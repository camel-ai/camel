from apis.api import API

class QueryScene(API):
    description = 'This API queries a scene of smart home system, given the scene name'
    input_parameters = {
        "name": {'type': 'str', 'description': 'The name of the scene.'},
    }

    output_parameters = {
        'devices': {'type': 'list', 'description': 'The list of smart devices, containing the name and description.'},
    }

    database_name = 'Scenes'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, name: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - name (str): the name of the scene.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'name': name,
        }
        try:
            devices = self.query_scene(name)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        else:
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': devices,
                'exception': None,
            }
        
    def query_scene(self, name: str) -> list:
        """
        Queries a scene.

        Parameters:
        - name (str): the name of the scene.

        Returns:
        - devices (list): the list of smart devices.
        """
        name = name.strip().lower()
        if name == "":
            raise Exception("Scene name cannot be empty.")
        target = None
        if name in self.database:
            target = self.database[name]
            return target
        else:
            raise Exception('Scene not found.')
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks whether the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the ground truth.

        Returns:
        - is_correct (bool): whether the API call is correct.
        """
        response_name = response['input']['name'].strip().lower()
        groundtruth_name = groundtruth['input']['name'].strip().lower()
        if response_name != groundtruth_name:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True