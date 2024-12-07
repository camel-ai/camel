# from api import API
from apis.api import API
import datetime

class QueryHistoryToday(API):
    description = 'This API queries the history of the given date.'
    input_parameters = {
        'date': {'type': 'str', 'description': 'The date of the history. Format: %m-%d'},
    }
    output_parameters = {
        'history': {'type': 'list', 'description': 'The history of the user today.'},
    }
    database_name = 'History'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
    
    def call(self, date) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - date (datetime): the date of the history. Format: %m-%d

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'date': date,
        }
        try:
            history = self.query_history_today(date)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': history,
                    'exception': None}
    
    def filter_date_format(self, date):
        """
        Filters the input parameters.

        Parameters:
        - date (datetime): the date of the history. Format: %m-%d / %Y-%m-%d

        Returns:
        - date (datetime): the date of the history. Format: %m-%d
        """
        date = date.strip()
        split_date = date.split('-')
        
        if len(split_date) != 3:
            pass
        else:
            if len(split_date[0]) == 4:
                pass
            else:
                split_date[0] = split_date[0].zfill(4)
            date = '-'.join(split_date)
        
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except Exception:
            try:
                datetime.datetime.strptime(date, '%m-%d')
            except Exception as e:
                date = e
            else:
                date = datetime.datetime.strptime(date, '%m-%d').strftime('%m-%d')
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d')
        
        return date

    def query_history_today(self, date) -> list:
        """
        Queries the history of a given user today.

        Parameters:
        - date (datetime): the date of the history. Format: %m-%d

        Returns:
        - history (list): the history of the user today.
        """
        # Check the format of the input parameters.
        date = self.filter_date_format(date)
        if isinstance(date, ValueError):
            raise date
        
        if date not in self.database:
            raise Exception('The date is not in the database.')
        
        history = self.database[date]
        history = ["Title: {}, Date: {}, Description: {}".format(history[i]['Title'].strip(), history[i]['Date'].strip(), history[i]['Description'].strip()) for i in range(len(history))]
        
        return history
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_date = self.filter_date_format(response['input']['date'])
        groundtruth_date = self.filter_date_format(groundtruth['input']['date'])

        response_history = response['output']
        groundtruth_history = groundtruth['output']

        if response_date == groundtruth_date and response_history == groundtruth_history and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        

