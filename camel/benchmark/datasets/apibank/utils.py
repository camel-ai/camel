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
