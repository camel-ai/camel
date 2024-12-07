from apis.api import API
# from api import API
import requests

class Dictionary(API):
    description = 'This API searches the dictionary for a given keyword.'
    input_parameters = {
        "keyword": {'type': 'str', 'description': 'The keyword to search.'},
    }
    output_parameters = {
        "results": {'type': 'list', 'description': 'The list of results. Format be like [{"partOfSpeech": "xxx", "definitions": [{"definition": "xxx", "example": "xxx", "synonyms": ["xxx", "xxx"]}, ...]'},
    }
    
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, keyword: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - keyword (str): the keyword to search.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'keyword': keyword,
        }
        try:
            results = self.search(keyword)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        return {
            'api_name': self.__class__.__name__,
            'input': input_parameters,
            'output': results,
            'exception': None,
        }

    def search(self, keyword: str) -> list:
        """
        Search for a given keyword.

        Parameters:
        - keyword (str): the keyword to search.

        Returns:
        - results (dict): the results from the search.
        """
        keyword = keyword.replace('_', ' ').strip().lower()
        url = 'https://api.dictionaryapi.dev/api/v2/entries/en_US/' + keyword
        response = requests.get(url)
        if response.status_code == 200:
            res = response.json()[0]
        else:
            raise Exception("Failed.")
        
        return res["meanings"]
        
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        if response['api_name'] != self.__class__.__name__:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True
