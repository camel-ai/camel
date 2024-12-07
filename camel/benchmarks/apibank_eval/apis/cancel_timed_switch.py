from apis.api import API
import datetime

class CancelTimedSwitch(API):
    description = 'Cancels a timed switch for a smart device.'
    input_parameters = {
        "name": {'type': 'str', 'description': 'The name of the smart device.'},
        "time": {'type': 'str', 'description': 'The time to switch the device on or off. Format: %Y-%m-%d %H:%M:%S'},
    }

    output_parameters = {
        'status': {'type': 'str', 'description': 'Whether the time switch is successful.'},
    }

    database_name = 'TimeSwitch'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, name: str, time: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - name (str): the name of the smart device.
        - time (str): the time to switch the device on or off.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'name': name,
            'time': time,
        }
        try:
            status = self.cancel_timed_switch(name, time)
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
        
    def format_check(self, time):
        time = time.strip()
        split_time = time.split('-')
        if len(split_time) == 3:
            if len(split_time[0]) == 4:
                pass
            else:
                split_time[0] = split_time[0].zfill(4)
            time = '-'.join(split_time)
        try:
            time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            time = e
        return time
    
    def cancel_timed_switch(self, name, time):
        name = name.strip().lower()
        if name == '':
            raise Exception('name cannot be empty.')
        time = self.format_check(time)
        if isinstance(time, Exception):
            raise time
        
        if name not in self.database:
            raise Exception('device name does not exist.')
        time_index = -1
        for i in range(len(self.database[name])):
            if self.database[name][i]['time'] == time:
                time_index = i
                break
        if time_index == -1:
            raise Exception('time does not exist.')
        self.database[name].pop(time_index)
        return 'success'
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_device_id = response['input']['name']
        groundtruth_device_id = groundtruth['input']['name']
        response_time = response['input']['time']
        groundtruth_time = groundtruth['input']['time']

        response_device_id = response_device_id.strip().lower()
        groundtruth_device_id = groundtruth_device_id.strip().lower()
        response_time = self.format_check(response_time)
        groundtruth_time = self.format_check(groundtruth_time)

        if response_device_id != groundtruth_device_id:
            return False
        if response_time != groundtruth_time:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True