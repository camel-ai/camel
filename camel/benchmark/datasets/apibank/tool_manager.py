from apis.tool_search import ToolSearcher
from apis import API
import os
import json
from api_call_extraction import parse_api_call
class ToolManager:
    def __init__(self, apis_dir='./apis') -> None:
        import importlib.util

        all_apis = []
        # import all the file in the apis folder, and load all the classes
        except_files = ['__init__.py', 'api.py']
        for file in os.listdir(apis_dir):
            if file.endswith('.py') and file not in except_files:
                api_file = file.split('.')[0]
                basename = os.path.basename(apis_dir)
                module = importlib.import_module(f'{basename}.{api_file}')
                classes = [getattr(module, x) for x in dir(module) if isinstance(getattr(module, x), type)]
                for cls in classes:
                    if issubclass(cls, API) and cls is not API:
                        all_apis.append(cls)

        classes = all_apis

        self.init_databases = {}
        init_database_dir = './init_database'
        for file in os.listdir(init_database_dir):
            if file.endswith('.json'):
                database_name = file.split('.')[0]
                with open(os.path.join(init_database_dir, file), 'r') as f:
                    self.init_databases[database_name] = json.load(f)

        # Get the description parameter for each class
        apis = []
        for cls in classes:
            if issubclass(cls, object) and cls is not object:
                name = cls.__name__
                cls_info = {
                    'name': name,
                    'class': cls,
                    'description': cls.description,
                    'input_parameters': cls.input_parameters,
                    'output_parameters': cls.output_parameters,
                }

                if hasattr(cls, 'database_name') and cls.database_name in self.init_databases:
                    cls_info['init_database'] = self.init_databases[cls.database_name]
                apis.append(cls_info)
        
        self.apis = apis
        self.inited_tools = {}
        if 'CheckToken' in self.list_all_apis():
            self.token_checker = self.init_tool('CheckToken')

    def get_api_by_name(self, name: str):
        """
        Gets the API with the given name.

        Parameters:
        - name (str): the name of the API to get.

        Returns:
        - api (dict): the API with the given name.
        """
        for api in self.apis:
            if api['name'] == name:
                return api
        raise Exception('invalid tool name.')
    
    def get_api_description(self, name: str):
        """
        Gets the description of the API with the given name.

        Parameters:
        - name (str): the name of the API to get the description of.

        Returns:
        - desc (str): the description of the API with the given name.
        """
        api_info = self.get_api_by_name(name).copy()
        api_info.pop('class')
        if 'init_database' in api_info:
            api_info.pop('init_database')
        return json.dumps(api_info)

    def init_tool(self, tool_name: str, *args, **kwargs):
        """
        Initializes a tool with the given name and parameters.

        Parameters:
        - tool_name (str): the name of the tool to initialize.
        - args (list): the positional arguments to initialize the tool with.
        - kwargs (dict): the parameters to initialize the tool with.

        Returns:
        - tool (object): the initialized tool.
        """
        if tool_name in self.inited_tools:
            return self.inited_tools[tool_name]
        # Get the class for the tool
        api_class = self.get_api_by_name(tool_name)['class']
        temp_args = []

        if 'init_database' in self.get_api_by_name(tool_name):
            # Initialize the tool with the init database
            temp_args.append(self.get_api_by_name(tool_name)['init_database'])
        
        if tool_name != 'CheckToken' and 'token' in self.get_api_by_name(tool_name)['input_parameters']:
            temp_args.append(self.token_checker)

        args = temp_args + list(args)
        tool = api_class(*args, **kwargs)

        self.inited_tools[tool_name] = tool
        return tool
    
    def process_parameters(self, tool_name: str, parameters: list):
        input_parameters = self.get_api_by_name(tool_name)['input_parameters'].values()
        assert len(parameters) == len(input_parameters), 'invalid number of parameters.'

        processed_parameters = []
        for this_para, input_para in zip(parameters, input_parameters):
            para_type = input_para['type']
            if para_type == 'int':
                assert this_para.isdigit(), 'invalid parameter type. parameter: {}'.format(this_para)
                processed_parameters.append(int(this_para))
            elif para_type == 'float':
                assert this_para.replace('.', '', 1).isdigit(), 'invalid parameter type.'
                processed_parameters.append(float(this_para))
            elif para_type == 'str':
                processed_parameters.append(this_para)
            else:
                raise Exception('invalid parameter type.')
        return processed_parameters
    
    def api_call(self, tool_name: str, **kwargs): 
        """
        Calls the API with the given name and parameters.
        """
        input_parameters = self.get_api_by_name(tool_name)['input_parameters'] # {'username': {'type': 'str', 'description': 'The username of the user.'}, 'password': {'type': 'str', 'description': 'The password of the user.'}}
        # assert len(kwargs) == len(input_parameters), 'invalid number of parameters. expected: {}, got: {}'.format(len(input_parameters), len(kwargs))

        processed_parameters = {}
        for input_key in kwargs:
            input_value = kwargs[input_key]
            assert input_key in input_parameters, 'invalid parameter name. parameter: {}'.format(input_key)
            required_para = input_parameters[input_key]

            required_type = required_para['type']
            if required_type == 'int':
                if isinstance(input_value, str):
                    assert input_value.isdigit(), 'invalid parameter type. parameter: {}'.format(input_value)
                processed_parameters[input_key] = int(input_value)
            elif required_type == 'float':
                if isinstance(input_value, str):
                    assert input_value.replace('.', '', 1).isdigit(), 'invalid parameter type.'
                processed_parameters[input_key] = float(input_value)
            elif required_type == 'str':
                processed_parameters[input_key] = input_value
            elif required_type == 'list(str)':
                # input_value = input_value.replace('\'', '"')
                processed_parameters[input_key] = input_value
            elif required_type == 'list':
                # input_value = input_value.replace('\'', '"')
                processed_parameters[input_key] = input_value
            elif required_type == 'bool':
                processed_parameters[input_key] = input_value == 'True'
            else:
                raise Exception('invalid parameter type.')
        
        tool = self.init_tool(tool_name)
        result = tool.call(**processed_parameters)
        return result
    
    def command_line(self):
        """
        Starts the command line interface for the tool manager.
        """
        mode = 'function_call' # 'function_call' or 'qa'
        if mode == 'qa':
            while True:
                tool_keywords = input('Please enter the keywords for the tool you want to use (\'exit\' to exit):\n')
                tool_searcher = self.init_tool('ToolSearcher')
                response = tool_searcher.call(tool_keywords)
                tool = self.init_tool(response['output']['name'])
                print('The tool you want to use is: \n' + self.get_api_description(response['output']['name']))
                while True:
                    command = input('Please enter the parameters for the tool you want to use (\'exit\' to exit): \n')
                    if command == 'exit':
                        break
                    else:
                        command = command.replace(' ', '')
                        processed_parameters = self.process_parameters(response['output']['name'], command.split(','))
                        print(tool.call(*processed_parameters))
        elif mode == 'function_call':
            while True:
                command = input('Please enter the command for the tool you want to use: \n')
                if command == 'exit':
                    break
                api_name, param_dict = parse_api_call(command)
                print(self.api_call(api_name, **param_dict))

    def list_all_apis(self):
        """
        Lists all the APIs.

        Returns:
        - apis (list): a list of all the APIs.
        """
        return [api['name'] for api in self.apis]
    
if __name__ == '__main__':
    tool_manager = ToolManager()
    tool_manager.command_line()