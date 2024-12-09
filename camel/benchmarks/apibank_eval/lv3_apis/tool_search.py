from sentence_transformers import SentenceTransformer, util
import logging
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

import json
from apis.api import API
import os

class ToolSearcher(API):
    description = 'Searches for relevant tools in library based on the keyword.'
    input_parameters = {
        'keywords': {'type': 'str', 'description': 'The keyword to search for.'}
    }
    output_parameters = {
        'best_matchs': {'type': 'Union[List[dict], dict]', 'description': 'The best match tool(s).'},
    }

    def __init__(self, apis_dir = './lv3_apis'):
        import importlib.util


        all_apis = []
        # import all the file in the apis folder, and load all the classes
        except_files = ['__init__.py', 'api.py', 'tool_search.py']
        for file in os.listdir(apis_dir):
            if file.endswith('.py') and file not in except_files:
                api_file = file.split('.')[0]
                basename = os.path.basename(apis_dir)
                module = importlib.import_module(basename + "." + api_file)
                classes = [getattr(module, x) for x in dir(module) if isinstance(getattr(module, x), type)]
                for cls in classes:
                    if issubclass(cls, API) and cls is not API:
                        all_apis.append(cls)

        classes = all_apis

        # # Import the module containing the API classes
        # spec = importlib.util.spec_from_file_location('apis', './apis.py')
        # module = importlib.util.module_from_spec(spec)
        # spec.loader.exec_module(module)

        # # Get a list of all classes in the module
        # classes = inspect.getmembers(module, inspect.isclass)

        def api_summery(cls):
            cls_name = cls.__name__
            # split cls_name by capital letters
            cls_name = ''.join([' ' + i.lower() if i.isupper() else i for i in cls_name]).strip()
            return cls_name + cls.description 

        # Get the description parameter for each class
        apis = []
        for cls in classes:
            if issubclass(cls, object) and cls is not object:
                desc_for_search = api_summery(cls)
                apis.append({
                    'name': cls.__name__,
                    'description': cls.description,
                    'input_parameters': cls.input_parameters,
                    'output_parameters': cls.output_parameters,
                    'desc_for_search': desc_for_search
                })
        
        self.apis = apis

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        
        if response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

    def call(self, keywords):
        """
        Searches for relevant tools in various libraries based on the keyword.

        Parameters:
        - keywords (str): the keywords to search for.

        Returns:
        - best_match (dict): the best match for the keywords.
        """
        input_parameters = {
            'keywords': keywords
        }
        try:
            best_match = self.best_match_api(keywords)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': best_match, 'exception': None}
        
    
    def best_match_api(self, keywords):

        model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2')
        kw_emb = model.encode(keywords)
        best_match = None
        best_match_score = 0
        for api in self.apis:
            re_emb = model.encode(api['desc_for_search'])
            cos_sim = util.cos_sim(kw_emb, re_emb).item()
            if cos_sim > best_match_score:
                best_match = api.copy()
                best_match_score = cos_sim
        best_match.pop('desc_for_search')
        if 'token' in best_match['input_parameters']:
            return [self.get_user_token_api, best_match]
        else:
            return best_match
        # best_match = None
        # for api in self.apis:
        #     if api['name'] == keywords:
        #         best_match = api
        #         break
        # best_match = best_match.copy()
        # best_match.pop('desc_for_search')
        # return best_match

        # model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2')
        # kw_emb = model.encode(keywords)

        # scores = []
        # for api in self.apis:
        #     re_emb = model.encode(api['desc_for_search'])
        #     cos_sim = util.cos_sim(kw_emb, re_emb).item()
        #     scores.append((api, cos_sim))

        # scores.sort(key=lambda x: x[1], reverse=True)
        # api_id = input('Please select the best match from {}:\n'.format([x[0]['name'] for x in scores[:3]]))
        # try:
        #     api_id = int(api_id) - 1
        # except:
        #     best_match = scores[0][0]
        #     for api in self.apis:
        #         if api['name'] == api_id:
        #             best_match = api
        #             break
        # else:
        #     best_match = scores[int(api_id)][0]

        # best_match = best_match.copy()
        # best_match.pop('desc_for_search')
        # return best_match

if __name__ == '__main__':
    tool_searcher = ToolSearcher(apis_dir='./lv3_apis')
    print(tool_searcher.call('add alarm'))