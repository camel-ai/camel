from apis.api import API

class DeleteScene(API):
    
    description = 'This API deletes a scene by its name.'
    input_parameters = {
        "name": {'type': 'str', 'description': 'The name of the scene.'},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'Whether the deletion is successful.'},
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
            success = self.delete_scene(name)
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
                'output': success,
                'exception': None,
            }
    
    def delete_scene(self, name: str) -> bool:
        """
        Deletes a scene.

        Parameters:
        - name (str): the name of the scene.

        Returns:
        - success (str): whether the deletion is successful.
        """
        name = name.strip().lower()
        if name == "":
            raise Exception("Scene name cannot be empty.")
        if name in self.database:
            del self.database[name]
        else:
            raise Exception('The scene does not exist.')
        
        return 'success'

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - correctness (bool): whether the API call is correct.
        """
        response_name = response['input']['name']
        groundtruth_name = groundtruth['input']['name']
        response_name = response_name.strip().lower()
        groundtruth_name = groundtruth_name.strip().lower()
        if response_name != groundtruth_name:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True
    