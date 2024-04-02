from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.types import RoleType, ReasonType
from camel.functions.search_functions import *

import binascii
import pytest
import requests

