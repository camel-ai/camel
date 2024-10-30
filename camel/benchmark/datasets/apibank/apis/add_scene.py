from apis.api import API
import random

class AddScene(API):
    description = "This API adds a scene of smart home system, given the scene name and a list of smart devices"
    input_parameters = {
        "name": {'type': 'str', 'description': 'The name of the scene.'},
        "devices": {'type': 'list', 'description': 'The list of smart devices, containing the name and description. Format be like [{"name": "light", "description": "Smart light in the kitchen"}, {"name": "oven", "description": "Smart oven in the kitchen"}, {"name": "range hood", "description": "Smart range hood in the kitchen"}]'},
    }
    
    output_parameters = {
        "status": {'type': 'str', 'description': 'Whether succeed.'},
    }
    database_name = 'Scenes'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, name: str, devices: list) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - name (str): the name of the scene.
        - devices (list): the list of smart devices.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'name': name,
            'devices': devices,
        }
        try:
            scene_id = self.add_scene(name, devices)
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
                'output': scene_id,
                'exception': None,
            }
        
    def add_scene(self, name, devices):
        # format check
        name = name.strip().lower()
        if name == "":
            raise Exception("Scene name cannot be empty.")
        name_set = set([])
        for device in devices:
            if 'name' not in device or 'description' not in device:
                raise Exception('Invalid device format.')
            device['name'] = device['name'].strip().lower()
            device['description'] = device['description'].strip()
            if device['name'] not in name_set:
                name_set.add(device['name'])
            else:
                raise Exception("Device name cannot be duplicated.")
        
        devices.sort(key=lambda x: x['name'])
        
        if name in self.database:
            raise Exception("Scene name already exists.")
        else:
            self.database[name] = devices
        
        # database = {
        #    "scene_id": {
        #      "name": "scene_name",
        #      "devices": [
        #       {
        #           "device_id": "device_id",
        #           "description": "description",
        #       },
        #       {
        #           "device_id": "device_id",
        #           "description": "description",
        #       },
        #    ],
        #  },
        # }
        return "success"
    
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
        response_devices = response['input']['devices']
        groundtruth_name = groundtruth['input']['name']
        groundtruth_devices = groundtruth['input']['devices']

        response_name = response_name.strip().lower()
        groundtruth_name = groundtruth_name.strip().lower()
        for device in response_devices:
            device['name'] = device['name'].strip().lower()
            device['description'] = device['description'].strip()
        for device in groundtruth_devices:
            device['name'] = device['name'].strip().lower()
            device['description'] = device['description'].strip()
        response_devices.sort(key=lambda x: x['name'])
        groundtruth_devices.sort(key=lambda x: x['name'])

        if response_name != groundtruth_name:
            return False
        if response_devices != groundtruth_devices:
            return False
        # if response['output'] != groundtruth['output']:
        #     return False
        if groundtruth['output'] == None and response['output'] != None:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True