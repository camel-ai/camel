from apis.api import API
# from api import API
import googletrans
from googletrans import Translator
import os

class Translate(API):
    
    description = 'Translate the text to the target language.'
    input_parameters = {
        "src": {"type": "str", "description": "The text to be translated."},
        "src_lang": {"type": "str", "description": "[Optional] The source language to translate from. Default is auto."},
        "tgt_lang": {"type": "str", "description": "[Optional] The target language to translate to. Default is english/en."},
    }
    output_parameters = {
        "translated_text": {"type": "str", "description": "The translated text."},
    }
    
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
        self.translator = Translator()
        self.LANGUAGES = googletrans.LANGUAGES

    def call(self, src:str, **kwargs) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - src (str): the text to be translated.
        - src_lang (str): the source language to translate from.
        - tgt_lang (str): the target language to translate to.

        Returns:
        - response (dict): the response from the API call.
        """
        # cancel proxy and backup proxy
        proxy = os.environ.get('ALL_PROXY')
        os.environ['ALL_PROXY'] = ''

        input_parameters = {
            'src': src,
            **kwargs
        }
        try:
            translated_text = self.translate(src, **kwargs)
        except Exception as e:
            exception = str(e)
            os.environ['ALL_PROXY'] = proxy
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        os.environ['ALL_PROXY'] = proxy
        return {
            'api_name': self.__class__.__name__,
            'input': input_parameters,
            'output': translated_text,
            'exception': None,
        }

       
    def translate(self, text: str, **kwargs) -> str:
        """
        Translates the text to the target language.

        Parameters:
        - text (str): the text to be translated.
        - target_language (str): the target language to translate to.

        Returns:
        - translated_text (str): the translated text.
        """
        
        if 'src_lang' in kwargs:
            src_lang = kwargs['src_lang']
            src_lang = src_lang.lower()
        else:
            src_lang = None
        if 'tgt_lang' in kwargs:
            tgt_lang = kwargs['tgt_lang']
            tgt_lang = tgt_lang.lower()
        else:
            tgt_lang = None
        
        def detect_language(lang):
            if lang == None:
                return "en"
            if "chinese" in lang:
                if "traditional" in lang:
                    return "zh-tw"
                else:
                    return "zh-cn"
            for key in self.LANGUAGES:
                if key == lang:
                    return key
                elif self.LANGUAGES[key] in lang:
                    return key
            
            raise Exception('Language not supported.')
                
        if src_lang != None:
            src_lang = detect_language(src_lang)
        tgt_lang = detect_language(tgt_lang)
        if src_lang == None:
            translated_text = self.translator.translate(text, dest=tgt_lang).text
        else:
            translated_text = self.translator.translate(text, src=src_lang, dest=tgt_lang).text
        
        return translated_text
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): whether the API call is correct.
        """
        if response['api_name'] != groundtruth['api_name']:
            return False
        if response['input']['src'] != groundtruth['input']['src']:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True
    
