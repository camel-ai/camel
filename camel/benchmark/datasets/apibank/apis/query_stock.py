from apis.api import API
import datetime

class QueryStock(API):
    
    description = 'This API queries the stock price of a given stock code and date.'
    input_parameters = {
        "stock_code": {'type': 'str', 'description': 'The stock code of the given stock.'},
        "date": {'type': 'str', 'description': 'The date of the stock price. Format: %Y-%m-%d'}
    }
    output_parameters = {
        'stock_price': {'type': 'float', 'description': 'The stock price of the given stock.'},
    }

    database_name = 'Stock'
    
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, stock_code, date) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - stock_code (str): the stock code of the given stock.
        - date (datetime): the date of the stock price. Format: %Y-%m-%d

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'stock_code': stock_code,
            'date': date,
        }
        try:
            stock_price = self.query_stock(stock_code, date)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': stock_price,
                    'exception': None}

    def format_check(self, stock_code, date) -> bool:
        """
        Checks the format of the input parameters.

        Parameters:
        - stock_code (str): the stock code of the given stock.
        - date (datetime): the date of the stock price. Format: %Y-%m-%d

        Returns:
        - res (tuple): the format check result. 
        """
        # Check the format of the input parameters.
        stock_code = stock_code.upper().strip()
        if stock_code == '':
            stock_code = None
        
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
        except Exception as e:
            date = e
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        return (stock_code, date)
        
    def query_stock(self, stock_code, date) -> float:
        """
        Queries the stock price of a given stock.

        Parameters:
        - stock_code (str): the stock code of the given stock.
        - date (datetime): the date of the stock price. Format: %Y-%m-%d

        Returns:
        - stock_price (float): the stock price of the given stock.
        """

        # Check the format of the input parameters.
        stock_code, date = self.format_check(stock_code, date)
        if stock_code == None:
            raise Exception('The stock code cannot be empty.')
        if isinstance(date, Exception):
            raise date
        
        # Check if the query is valid.
        if stock_code not in self.database:
            raise Exception('The stock code does not exist.')
        if date not in self.database[stock_code]:
            raise Exception('The stock price of this date is not maintained.')
        
        # Return the stock price.
        """
        database = {
           'AAPL': {
              '2020-01-01': 100.0,
              '2020-01-02': 101.0,
              '2020-01-03': 102.0,
           },
           'MSFT': {
              '2020-01-01': 200.0,
              '2020-01-02': 201.0,
              '2020-01-03': 202.0,
           },
        }
        """
        return self.database[stock_code][date]
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_stock_code = response['input']['stock_code']
        response_date = response['input']['date']
        groundtruth_stock_code = groundtruth['input']['stock_code']
        groundtruth_date = groundtruth['input']['date']

        response_stock_code, response_date = self.format_check(response_stock_code, response_date)
        groundtruth_stock_code, groundtruth_date = self.format_check(groundtruth_stock_code, groundtruth_date)

        if response_stock_code == groundtruth_stock_code and response_date == groundtruth_date and response['output'] == \
            groundtruth['output'] and response['exception'] == groundtruth['exception']:
                return True
        else:
            return False