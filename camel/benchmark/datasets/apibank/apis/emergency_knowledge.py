from apis.api import API

class EmergencyKnowledge(API):
    
    description = 'This API searches for a given symptom for emergency knowledge.'
    input_parameters = {
        "symptom": {'type': 'str', 'description': 'The symptom to search.'},
    }
    output_parameters = {
        "results": {'type': 'list', 'description': 'The list of results. Format be like [{"name":possible disease name, "aid": first-aid method},...]'},
    }
    database_name = 'Symptom'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, symptom: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - symptom (str): the symptom to search.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'symptom': symptom,
        }
        try:
            results = self.search(symptom)
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

    def format_check(self, symptom):
        """
        Checks the format of the symptom.

        Parameters:
        - symptom (str): the symptom to search.

        Returns:
        - None
        """
        symptom = symptom.strip()
        if symptom == '':
            symptom = Exception("The symptom cannot be empty.")
        return symptom.lower()

    def search(self, symptom: str) -> list:
        """
        Searches for a given symptom.

        Parameters:
        - symptom (str): the symptom to search.

        Returns:
        - results (list): the list of results.
        """
        symptom = self.format_check(symptom)
        if isinstance(symptom, Exception):
            raise symptom
        if symptom not in self.database:
            raise Exception("The symptom does not exist.")
        """
        database = {
          "Headache":[
              {
                  "name":"Migraine",
                  "description":"A neurological condition characterized by recurrent headaches, often accompanied by other symptoms such as nausea, vomiting, and sensitivity to light and sound.",
                  "aid":"Treatment may involve medications to manage symptoms and prevent attacks, lifestyle changes to avoid triggers, and in some cases, preventive medications."
              },
              {
                  "name":"Tension headache",
                  "description":"A type of headache characterized by a dull, aching pain that can be felt on both sides of the head.",
                  "aid":"Treatment may involve over-the-counter pain relievers, lifestyle changes, and stress management techniques."
              },
              {
                  "name":"Cluster headache",
                  "description":"A type of headache that occurs in cyclical patterns, with periods of frequent attacks followed by periods of remission.",
                  "aid":"Treatment may involve medications to manage symptoms and prevent attacks, as well as oxygen therapy and nerve blocks in some cases."
              }
          ],
        }
        """
        results = self.database[symptom]
        results = [{"name":item["name"],"aid":item["aid"]} for item in results]
        return results
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - correctness (bool): whether the API call is correct.
        """
        response_symptom = response['input']['symptom']
        groundtruth_symptom = groundtruth['input']['symptom']
        response_symptom = self.format_check(response_symptom)
        groundtruth_symptom = self.format_check(groundtruth_symptom)
        if response_symptom != groundtruth_symptom:
            return False
        
        response_results = response['output']
        groundtruth_results = groundtruth['output']
        if response_results != groundtruth_results:
            return False
        
        response_exception = response['exception']
        groundtruth_exception = groundtruth['exception']
        if response_exception != groundtruth_exception:
            return False
        
        return True
    
