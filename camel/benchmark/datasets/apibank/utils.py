from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

import requests
import json
from tqdm import tqdm
from multiprocessing.dummy import Pool as ThreadPool
import logging
from requests.exceptions import ConnectionError

class RateLimitReached(Exception):
    pass

class OfficialError(Exception):
    pass

class RecoverableError(Exception):
    pass

class KeysBusyError(Exception):
    pass

class ChatGPTWrapper:
    def __init__(self, api_key='', proxies=None) -> None:
        # Set the request parameters
        self.url = 'https://api.openai.com/v1/chat/completions'
        # Set the header
        self.header = {
            "Content-Type": "application/json",
            "Authorization": 'Bearer {}'.format(api_key)
        }
        self.proxies = proxies

    @retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((RateLimitReached, RecoverableError, OfficialError, ConnectionError)))
    def call(self, messages, **kwargs):
        query = {
            "model": "gpt-3.5-turbo",
            "messages": messages
        }
        query.update(kwargs)

        # Make the request
        if self.proxies:
            response = requests.post(self.url, headers=self.header, data=json.dumps(query), proxies=self.proxies)
        else:
            response = requests.post(self.url, headers=self.header, data=json.dumps(query))
        response = response.json()
        if 'error' in response and 'Rate limit reached' in response['error']['message']:
            raise RateLimitReached()
        elif 'choices' in response:
            return response
        else:
            if 'error' in response:
                print(response['error']['message'])
                if response['error']['message'] == 'The server had an error while processing your request. Sorry about that!':
                    raise RecoverableError(response['error']['message'])
                else:
                    raise OfficialError(response['error']['message'])
            else:
                raise Exception('Unknown error occured. Json: {}'.format(response))
            

class GPT4Wrapper(ChatGPTWrapper):
    @retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((RateLimitReached, RecoverableError, OfficialError, ConnectionError)))
    def call(self, messages, **kwargs):
        query = {
            "model": "gpt-4o-mini",
            "messages": messages
        }
        query.update(kwargs)

        # Make the request
        if self.proxies:
            response = requests.post(self.url, headers=self.header, data=json.dumps(query), proxies=self.proxies)
        else:
            response = requests.post(self.url, headers=self.header, data=json.dumps(query))        
        response = response.json()
        if 'error' in response and 'Rate limit reached' in response['error']['message']:
            raise RateLimitReached()
        elif 'choices' in response:
            return response
        else:
            if 'error' in response:
                print(response['error']['message'])
                if response['error']['message'] == 'The server had an error while processing your request. Sorry about that!':
                    raise RecoverableError(response['error']['message'])
                else:
                    raise OfficialError(response['error']['message'])
            else:
                raise Exception('Unknown error occured. Json: {}'.format(response))

