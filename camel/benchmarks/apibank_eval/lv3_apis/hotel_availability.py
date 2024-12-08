import datetime
from apis.api import API

class HotelAvailability(API):
    description = "API for checking hotel availability based on the destination and travel dates."
    input_parameters = {
        'destination': {'type': 'str', 'description': "Destination for hotel search."},
        'check_in_date': {'type': 'str', 'description': 'Check-in date. Format: %Y-%m-%d'},
        'check_out_date': {'type': 'str', 'description': 'Check-out date. Format: %Y-%m-%d'},
    }
    output_parameters = {
        'hotels': {'type': 'list', 'description': 'List of available hotels.'},
    }

    def __init__(self):
        self.hotel_database = {
            'hotel_1': {
                'destination': 'San Francisco',
                'check_in_date': datetime.datetime(2022, 1, 1),
                'check_out_date': datetime.datetime(2022, 1, 2),
            },
            'hotel_2': {
                'destination': 'San Francisco',
                'check_in_date': datetime.datetime(2022, 1, 2),
                'check_out_date': datetime.datetime(2022, 1, 3),
            },
            'hotel_3': {
                'destination': 'San Francisco',
                'check_in_date': datetime.datetime(2022, 1, 3),
                'check_out_date': datetime.datetime(2022, 1, 4),
            },
            'hotel_4': {
                'destination': 'San Francisco',
                'check_in_date': datetime.datetime(2022, 1, 4),
                'check_out_date': datetime.datetime(2022, 1, 5),
            },
            'hotel_5': {
                'destination': 'San Francisco',
                'check_in_date': datetime.datetime(2022, 1, 5),
                'check_out_date': datetime.datetime(2022, 1, 6),
            },
        }

    def check_api_call_correctness(self, response, groundtruth):
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        if response['input']['destination'] == groundtruth['input']['destination'] \
                and response['input']['check_in_date'] == groundtruth['input']['check_in_date'] \
                and response['input']['check_out_date'] == groundtruth['input']['check_out_date'] \
                and response['output']['hotels'] == groundtruth['output']['hotels']:
            return True
        else:
            return False

    def call(self, destination: str, check_in_date: str, check_out_date: str) -> dict:
        input_parameters = {
            'destination': destination,
            'check_in_date': check_in_date,
            'check_out_date': check_out_date
        }
        try:
            hotels = self.get_available_hotels(destination, check_in_date, check_out_date)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': {'hotels': hotels},
                    'exception': None}

    def get_available_hotels(self, destination: str, check_in_date: str, check_out_date: str) -> list:
        # Check the format of the input parameters.
        datetime.datetime.strptime(check_in_date, '%Y-%m-%d')
        datetime.datetime.strptime(check_out_date, '%Y-%m-%d')

        available_hotels = []
        for hotel_id, hotel in self.hotel_database.items():
            if hotel['destination'] == destination and self.is_hotel_available(hotel, check_in_date, check_out_date):
                hotel['check_in_date'] = hotel['check_in_date'].strftime('%Y-%m-%d')
                hotel['check_out_date'] = hotel['check_out_date'].strftime('%Y-%m-%d')
                available_hotels.append(hotel)
        
        return available_hotels

    def is_hotel_available(self, hotel, check_in_date, check_out_date) -> bool:
        hotel_check_in_date = hotel['check_in_date'] if isinstance(hotel['check_in_date'], datetime.datetime) \
            else datetime.datetime.strptime(hotel['check_in_date'], '%Y-%m-%d')
        hotel_check_out_date = hotel['check_out_date'] if isinstance(hotel['check_out_date'], datetime.datetime) \
            else datetime.datetime.strptime(hotel['check_out_date'], '%Y-%m-%d')
        user_check_in_date = datetime.datetime.strptime(check_in_date, '%Y-%m-%d')
        user_check_out_date = datetime.datetime.strptime(check_out_date, '%Y-%m-%d')

        if user_check_in_date >= hotel_check_in_date and user_check_out_date <= hotel_check_out_date:
            return True
