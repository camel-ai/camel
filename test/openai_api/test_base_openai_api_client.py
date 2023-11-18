# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from typing import Union
from camel.openai_api.base_openai_api_client import BaseOpenAIAPIClient

def test_get_api_key():
    client = BaseOpenAIAPIClient()
    api_key = client._get_api_key()
    assert isinstance(api_key, str)

def test_set_api_key():
    client = BaseOpenAIAPIClient()
    api_key = 'my-api-key'
    client._set_api_key(api_key)
    assert client._get_api_key() == api_key

def test_get_set_api_base():
    client = BaseOpenAIAPIClient()
    api_base = 'my-api-base'
    client.set_api_base(api_base)
    assert client.get_api_base() == api_base

def test_get_set_organization():
    client = BaseOpenAIAPIClient()
    organization = 'my-organization'
    client.set_organization(organization)
    organization = client.get_organization()
    assert isinstance(organization, str)