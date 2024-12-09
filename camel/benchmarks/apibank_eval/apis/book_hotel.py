from .api import API
import json
import os
import datetime

class BookHotel(API):
    description = 'This API orders a hotel room. Two rooms are ordered if the number of adults is greater than 2. Only one order can be made at same time.'
    input_parameters = {
        'hotel_name': {'type': 'str', 'description': 'The name of the hotel.'},
        'check_in_time': {'type': 'str', 'description': 'The time to check in. Format: %Y-%m-%d'},
        'check_out_time': {'type': 'str', 'description': 'The time to check out. Format: %Y-%m-%d'},
        'room_count': {'type': 'int', 'description': 'The number of rooms to order.'},
        'adult_count': {'type': 'int', 'description': 'The number of adults.'},
        'child_count': {'type': 'int', 'description': 'The number of children.'},
    }
    output_parameters = {
        'order_id': {'type': 'str', 'description': 'The ID of the order.'},
    }
    database_name = 'Hotel'
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def dump_database(self, database_dir):
        json.dump(self.database, open(os.path.join(database_dir, 'Hotel.json'), 'w'), ensure_ascii=False)
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - target (dict): the target response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        if response['input'] == groundtruth['input'] and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        
    def call(self, hotel_name: str, check_in_time: str, check_out_time: str, room_count: int, adult_count: int, child_count: int) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - hotel_name (str): the name of the hotel.
        - check_in_time (datetime): the time to check in.
        - check_out_time (datetime): the time to check out.
        - room_count (int): the number of rooms to order.
        - adult_count (int): the number of adults.
        - child_count (int): the number of children.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'hotel_name': hotel_name,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'room_count': room_count,
            'adult_count': adult_count,
            'child_count': child_count,
        }
        try:
            order_id = self.order(hotel_name, check_in_time, check_out_time, room_count, adult_count, child_count)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': order_id, 'exception': None}

    def order(self, hotel_name: str, check_in_time: str, check_out_time: str, room_count: int, adult_count: int, child_count: int) -> str:
        """
        Orders a hotel room.

        Parameters:
        - hotel_name (str): the name of the hotel.
        - check_in_time (datetime): the time to check in.
        - check_out_time (datetime): the time to check out.
        - room_count (int): the number of rooms to order.
        - adult_count (int): the number of adults.
        - child_count (int): the number of children.

        Returns:
        - order_id (str): the ID of the order.
        """

        # Check the format of the input parameters.
        datetime.datetime.strptime(check_in_time, '%Y-%m-%d')
        datetime.datetime.strptime(check_out_time, '%Y-%m-%d')

        order_item = {
            'hotel_name': hotel_name,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'room_count': room_count,
            'adult_count': adult_count,
            'child_count': child_count,
        }

        if adult_count > 2 and room_count == 1:
            raise Exception('The number of adults is greater than 2. Two rooms are ordered.')
        
        self.check_room_availability(hotel_name, check_in_time, check_out_time, room_count)

        order_id = str(len(self.database) + 1)
        self.database[order_id] = order_item

        return order_id

    def check_room_availability(self, hotel_name: str, check_in_time: datetime, check_out_time: datetime, room_count: int) -> None:
        """
        Checks if the room is available.

        Parameters:
        - hotel_name (str): the name of the hotel.
        - check_in_time (datetime): the time to check in.
        - check_out_time (datetime): the time to check out.
        - room_count (int): the number of rooms to order.

        Returns:
        - None
        """
        check_in_time = datetime.datetime.strptime(check_in_time, '%Y-%m-%d')
        check_out_time = datetime.datetime.strptime(check_out_time, '%Y-%m-%d')

        for order_id, order_item in self.database.items():
            if order_item['hotel_name'] == hotel_name:
                order_check_in_time = datetime.datetime.strptime(order_item['check_in_time'], '%Y-%m-%d')
                order_check_out_time = datetime.datetime.strptime(order_item['check_out_time'], '%Y-%m-%d')
                if (check_in_time >= order_check_in_time and check_in_time < order_check_out_time) or (check_out_time > order_check_in_time and check_out_time <= order_check_out_time):
                    raise Exception('The room is not available.')
                