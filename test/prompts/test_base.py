# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
#
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
# ===========================================================================
from camel.prompts import TextPrompt, TextPromptDict


def test_text_prompt_key_words():
    prompt = TextPrompt('Please enter your name and age: {name}, {age}')
    assert prompt.key_words == {'name', 'age'}

    prompt = TextPrompt('Please enter your email address')
    assert prompt.key_words == set()


def test_text_prompt_format():
    prompt = TextPrompt('Your name and age are: {name}, {age}')

    name, age = 'John', 30
    assert prompt.format(name=name,
                         age=age) == 'Your name and age are: John, 30'

    assert prompt.format(name=name) == 'Your name and age are: John, {age}'


def test_text_prompt_dict():
    prompt_dict = TextPromptDict()
    prompt_dict['test'] = TextPrompt('test')
    assert prompt_dict['test'] == TextPrompt('test')
