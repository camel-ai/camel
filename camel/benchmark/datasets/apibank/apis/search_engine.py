from apis.api import API
from rank_bm25 import BM25Okapi
import numpy as np
import nltk
try:
    from nltk.tokenize import word_tokenize
except:
    nltk.download('punkt')
    from nltk.tokenize import word_tokenize

class SearchEngine(API):
    description = 'This API searches for a given keyword for search engine.'
    input_parameters = {
        "keyword": {'type': 'str', 'description': 'The keyword to search.'},
    }
    output_parameters = {
        "results": {'type': 'list', 'description': 'The list of results.'},
    }
    database_name = 'SearchEngine'
    """
    database = {
        "item1": {
            "title": "title1",
            "url": "url1",
            "abstract": "abstract1",
        },
        "item2": {
            "title": "title2",
            "url": "url2",
            "abstract": "abstract2",
        },
        "item3": {
            "title": "title3",
            "url": "url3",
            "abstract": "abstract3",
        },
        "item4": {
            "title": "title4",
            "url": "url4",
            "abstract": "abstract4",
        },
    }
    """

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
        self.bm25 = BM25Okapi(self.database['tokenized_documents'])

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
        else:
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': results,
                'exception': None,
            }

    def search(self, keyword: str) -> list:
        """
        Searches for a given keyword.

        Parameters:
        - keyword (str): the keyword to search.

        Returns:
        - results (list): the list of results.
        """
        keyword = keyword.lower().strip()
        query = word_tokenize(keyword) # keyword.split()
        rankings = np.argsort(-np.array(self.bm25.get_scores(query)))
        if len(rankings) > 2:
            rankings = rankings[:2]
        results = [self.database["raw_documents"][i] for i in rankings]
        return results
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth from the API call.

        Returns:
        - correctness (bool): whether the response is correct.
        """
        if response['api_name'] != groundtruth['api_name']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        if response['output'] != None:
            response_output = sorted(response['output'], key=lambda x: x['title']+x['abstract'], reverse=True)
        if groundtruth['output'] != None:
            groundtruth_output = sorted(groundtruth['output'], key=lambda x: x['title']+x['abstract'], reverse=True)
        if response_output != groundtruth_output:
            return False
        return True

