from apis.api import API
import datetime

class QueryHealthData(API):
    description = 'This API queries the recorded health data in database of a given user and time span.'
    input_parameters = {
        "user_id": {'type': 'str', 'description': 'The user id of the given user. Cases are ignored.'},
        "start_time": {'type': 'str', 'description': 'The start time of the time span. Format: %Y-%m-%d %H:%M:%S'},
        "end_time": {'type': 'str', 'description': 'The end time of the time span. Format: %Y-%m-%d %H:%M:%S'},
    }
    output_parameters = {
        'health_data': {'type': 'list', 'description': 'The health data of the given user and time span.'},
    }

    database_name = 'HealthData'
    
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, user_id, start_time, end_time) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - user_id (str): the user id of the given user. Cases are ignored.
        - start_time (datetime): the start time of the time span. Format: %Y-%m-%d %H:%M:%S
        - end_time (datetime): the end time of the time span. Format: %Y-%m-%d %H:%M:%S

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'user_id': user_id,
            'start_time': start_time,
            'end_time': end_time,
        }
        try:
            health_data = self.query_health_data(user_id, start_time, end_time)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': health_data,
                    'exception': None}
        
    def format_check(self, user_id, start_time, end_time) -> bool:
        """
        Checks the format of the input parameters.

        Parameters:
        - user_id (str): the user id of the given user.
        - start_time (datetime): the start time of the time span. Format: %Y-%m-%d %H:%M:%S
        - end_time (datetime): the end time of the time span. Format: %Y-%m-%d %H:%M:%S

        Returns:
        - res (tuple): the format check result. 
        """
        # Check the format of the input parameters.
        user_id = user_id.upper().strip()
        if user_id == '':
            user_id = None

        start_time = start_time.strip()
        split_start_time = start_time.split('-')
        if len(split_start_time) != 3:
            pass
        else:
            if len(split_start_time[0]) == 4:
                pass
            else:
                split_start_time[0] = split_start_time[0].zfill(4)
            start_time = '-'.join(split_start_time)
        try:
            start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            start_time = e
       
        end_time = end_time.strip()
        split_end_time = end_time.split('-')
        if len(split_end_time) != 3:
            pass
        else:
            if len(split_end_time[0]) == 4:
                pass
            else:
                split_end_time[0] = split_end_time[0].zfill(4)
            end_time = '-'.join(split_end_time)
        try:
            end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            end_time = e
        return user_id, start_time, end_time
        #end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

    def query_health_data(self, user_id, start_time, end_time) -> list:
        """
        Queries the health data of a given user and time span.

        Parameters:
        - user_id (str): the user id of the given user.
        - start_time (datetime): the start time of the time span. Format: %Y-%m-%d %H:%M:%S
        - end_time (datetime): the end time of the time span. Format: %Y-%m-%d %H:%M:%S

        Returns:
        - health_data (list): the health data of the given user and time span.
        """
        # Check the format of the input parameters.
        user_id, start_time, end_time = self.format_check(user_id, start_time, end_time)

        if user_id == None:
            raise Exception('The user id cannot be empty.')
        if isinstance(start_time, Exception) and isinstance(end_time, Exception):
            raise Exception(str(start_time) + '; ' + str(end_time))
        if isinstance(start_time, Exception):
            raise start_time
        if isinstance(end_time, Exception):
            raise end_time
        if start_time > end_time:
            raise Exception('The start time cannot be later than the end time.')
        # Query the health data of the given user and time span.
        """
        database = {
            "USER1": [
                {
                    "time": "2020-01-01 00:00:00",
                    "heart_rate": 60,
                    "blood_pressure": 120,
                    ...
                },
                {
                    "time": "2020-01-02 00:00:00",
                    "heart_rate": 60,
                    "blood_pressure": 120,
                    ...
                },
            ],
            "USER2": [
                {
                    "time": "2020-01-01 00:00:00",
                    "heart_rate": 60,
                    "blood_pressure": 120,
                    ...
                },
                {
                    "time": "2020-01-02 00:00:00",
                    "heart_rate": 60,
                    "blood_pressure": 120,
                    ...
                },
            ],
        }
        """
        health_data = []
        if user_id not in self.database:
            raise Exception('The user id does not exist.')
        for health_data_item in self.database[user_id]:
            health_data_item_time = datetime.datetime.strptime(health_data_item['time'], '%Y-%m-%d %H:%M:%S')
            if health_data_item_time >= start_time and health_data_item_time <= end_time:
                health_data.append(health_data_item)

        if len(health_data) == 0:
            raise Exception('There is no health data in the given time span.')
        return health_data
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.

        Returns:
        - res (bool): the correctness check result.
        """
        response_user_id = response['input']['user_id']
        response_start_time = response['input']['start_time']
        response_end_time = response['input']['end_time']
        groundtruth_user_id = groundtruth['input']['user_id']
        groundtruth_start_time = groundtruth['input']['start_time']
        groundtruth_end_time = groundtruth['input']['end_time']

        response_user_id, response_start_time, response_end_time = self.format_check(response_user_id, response_start_time, response_end_time)
        groundtruth_user_id, groundtruth_start_time, groundtruth_end_time = self.format_check(groundtruth_user_id, groundtruth_start_time, groundtruth_end_time)

        if response_user_id != groundtruth_user_id:
            return False
        if response_start_time != groundtruth_start_time:
            return False
        if response_end_time != groundtruth_end_time:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True