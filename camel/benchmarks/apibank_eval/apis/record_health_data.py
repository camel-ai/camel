from apis.api import API
import datetime

class RecordHealthData(API):
    
    description = 'This API records the health data of a user.'
    input_parameters = {
        "user_id": {'type': 'str', 'description': 'The ID of user.'},
        "time": {'type': 'str', 'description': 'The time of health data. Format: %Y-%m-%d %H:%M:%S'},
        "health_data": {'type': 'list', 'description': "The health data, with the format like [{'name': 'blood_pressure', 'value': '120/80'}, {'name': 'heart_rate', 'value': '80'}]"},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'The status of recording.'},
    }
    database_name = 'HealthData'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, user_id: str, time: str, health_data: list = None) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - user_id (str): the ID of user.
        - time (str): the time of health data.
        - health_data (list): the health data.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'user_id': user_id,
            'time': time,
            'health_data': health_data,
        }
        try:
            status = self.record_health_data(user_id, time, health_data)
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
    
    def record_health_data(self, user_id, time, health_data=None):
        user_id = user_id.upper().strip()
        if user_id == '':
            user_id = None
        if user_id == None:
            raise Exception('The user id cannot be empty.')
        
        time = self.format_check(time)
        if isinstance(time, Exception):
            raise time

        if health_data == None:
            raise Exception('The health data cannot be empty.')
        if len(health_data) == 0:
            raise Exception('The health data cannot be empty.')
        health_data_set = set([])
        for data in health_data:
            if 'name' not in data:
                raise Exception('The health data has invalid format.')
            
            if data['name'] not in health_data_set:
                health_data_set.add(data['name'])
            else:
                raise Exception('The health data cannot contain duplicate items.')

        if user_id not in self.database:
            self.database[user_id] = []
        
        to_be_updated = None
        for record in self.database[user_id]:
            if record['time'] == time:
                to_be_updated = record
        
        if to_be_updated != None:
            for data in health_data:
                to_be_updated[data['name']] = data['value']
        else:
            new_record = {
                'time': time,
            }
            for data in health_data:
                new_record[data['name']] = data['value']
            self.database[user_id].append(new_record)

        return 'success'

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): the correctness of the API call.
        """
        response_user_id = str(response['input']['user_id'])
        groundtruth_user_id = groundtruth['input']['user_id']
        response_time = response['input']['time']
        groundtruth_time = groundtruth['input']['time']
        response_health_data = response['input']['health_data']
        groundtruth_health_data = groundtruth['input']['health_data']

        response_user_id = response_user_id.upper().strip()
        groundtruth_user_id = groundtruth_user_id.upper().strip()
        response_time = self.format_check(response_time)
        groundtruth_time = self.format_check(groundtruth_time)
        # response_health_data = [{"name":str(i["name"]),"value":str(i["value"])} for i in response_health_data]
        # groundtruth_health_data = [{"name":str(i["name"]),"value":str(i["value"])} for i in groundtruth_health_data]
        # response_health_data.sort(key=lambda x: str(x))
        # groundtruth_health_data.sort(key=lambda x: str(x))
        

        if response_user_id != groundtruth_user_id:
            return False
        if response_time != groundtruth_time:
            return False
        # if response_health_data != groundtruth_health_data:
        #     return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True