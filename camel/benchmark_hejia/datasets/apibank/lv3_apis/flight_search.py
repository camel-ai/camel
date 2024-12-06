import datetime
from apis.api import API

class FlightSearch(API):
    description = "API to retrieve flight options based on the destination and travel dates."
    input_parameters = {
        'source': {'type': 'str', 'description': "Source for the flight."},
        'destination': {'type': 'str', 'description': "Destination for the flight."},
        'travel_dates': {'type': 'str', 'description': 'Travel dates. Format: %Y-%m-%d'}
    }
    output_parameters = {
        'flights': {'type': 'list', 'description': 'List of available flight options.'}
    }

    def __init__(self):
        self.flight_data = [{
            'source': 'New York',
            'destination': 'San Francisco',
            'departure_date': datetime.datetime(2022, 1, 1, 12, 0, 0),
            'arrival_date': datetime.datetime(2022, 1, 1, 15, 0, 0),
        },
        {
            'source': 'Los Angeles',
            'destination': 'San Francisco',
            'departure_date': datetime.datetime(2022, 1, 2, 12, 0, 0),
            'arrival_date': datetime.datetime(2022, 1, 2, 15, 0, 0),
        },
        {
            'source': 'London',
            'destination': 'San Francisco',
            'departure_date': datetime.datetime(2022, 1, 3, 12, 0, 0),
            'arrival_date': datetime.datetime(2022, 1, 3, 15, 0, 0),
        },
        {
            'source': 'New York',
            'destination': 'London',
            'departure_date': datetime.datetime(2022, 1, 4, 12, 0, 0),
            'arrival_date': datetime.datetime(2022, 1, 4, 15, 0, 0),
        },
        {
            'source': 'New York',
            'destination': 'Los Angeles',
            'departure_date': datetime.datetime(2022, 1, 5, 12, 0, 0),
            'arrival_date': datetime.datetime(2022, 1, 5, 15, 0, 0),
        }]

    def get_flights(self, source, destination, travel_dates):
        travel_dates = datetime.datetime.strptime(travel_dates, '%Y-%m-%d')
        flights = []
        for flight in self.flight_data:
            if flight['source'] == source and flight['destination'] == destination and flight['departure_date'].date() == travel_dates.date():
                flight['departure_date'] = flight['departure_date'].strftime('%Y-%m-%d %H:%M:%S')
                flight['arrival_date'] = flight['arrival_date'].strftime('%Y-%m-%d %H:%M:%S')
                flights.append(flight)
        return flights
    
    def call(self, source, destination, travel_dates):
        input_parameters = {
            'source': source,
            'destination': destination,
            'travel_dates': travel_dates
        }
        try:
            flights = self.get_flights(source, destination, travel_dates)
            output_parameters = {'flights': flights}
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters,
                    'exception': None}
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']

