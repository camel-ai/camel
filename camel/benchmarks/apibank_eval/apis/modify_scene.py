from apis import API

class ModifyScene(API):
    description = 'This API modifies a scene of smart home system, given the scene name and a list of smart devices'
    input_parameters = {
        "name": {'type': 'str', 'description': 'The name of the scene.'},
        "devices": {'type': 'list', 'description': 'The list of smart devices, containing the name and description.'},
    }

    output_parameters = {
        'status': {'type': 'str', 'description': 'Whether the modification is successful.'},
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
            status = self.modify_scene(name, devices)
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
                'output': status,
                'exception': None,
            }
        
    def modify_scene(self, name: str, devices: list) -> bool:
        """
        Modifies a scene.

        Parameters:
        - name (str): the name of the scene.
        - devices (list): the list of smart devices.

        Returns:
        - status (str): whether the modification is successful.
        """
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

        scene = None
        if name in self.database:
            self.database[name] = devices
        else:
            raise Exception('The scene does not exist.')
        
        return "success"
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.
        
        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - correctness (bool): whether the response is correct.
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
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True