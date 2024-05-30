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
from unittest.mock import MagicMock, patch

import pytest

from camel.functions.open_api_function import combine_all_funcs_schemas


@pytest.fixture(scope="module")
def functions_dict():
    openapi_functions_list, _ = combine_all_funcs_schemas()
    functions_dict = {func.__name__: func for func in openapi_functions_list}
    return functions_dict


@pytest.fixture
def get_function(request, functions_dict):
    function_name = request.param
    func = functions_dict.get(function_name)
    if func is None:
        raise ValueError(f"Function {function_name} not found")
    return func


@pytest.mark.parametrize('get_function', ['coursera_search'], indirect=True)
def test_coursera_search(get_function):
    mock_response_data = {
        "hits": [
            {
                "name": "Machine Learning",
                "partners": ["DeepLearning.AI", "Stanford University"],
                "duration": "ONE_TO_THREE_MONTHS",
                "productDifficultyLevel": "BEGINNER",
                "entityType": "PRODUCTS",
                "skills": [
                    "Machine Learning",
                    "Machine Learning Algorithms",
                    "Applied Machine Learning",
                    "Algorithms",
                    "Deep Learning",
                    "Machine Learning Software",
                    "Artificial Neural Networks",
                    "Human Learning",
                ],
                "objectUrl": (
                    '''https://www.coursera.org/specializations/
                    machine-learning-introduction?utm_source=rest_api'''
                ),
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(requestBody={"query": "machine learning"})
        assert result == mock_response_data


@pytest.mark.parametrize(
    'get_function', ['klarna_productsUsingGET'], indirect=True
)
def test_klarna_productsUsingGET(get_function):
    mock_response_data = {
        'products': [
            {
                'name': 'Nike Dunk Low Retro M - Black/White',
                'url': '''https://www.klarna.com/us/shopping/pl/cl337/
                3200177969/Shoes/Nike-Dunk-Low-Retro-M-Black-White/?
                utm_source=openai&ref-site=openai_plugin''',
                'price': '\$81.00',
                'attributes': [
                    'Outsole:Rubber',
                    'Fastening:Laced',
                    'Midsole:Foam',
                    'Insole:Foam',
                    'Target Group:Man',
                    'Color:White',
                    'Upper Material:Leather',
                    '''Size (US):9.5,10,11,12,13,14,15,16,17,18,11.5,10.5,2,3,
                    4,5,6,7,8,9,2.5,3.5,4.5,16.5,5.5,15.5,6.5,14.5,13.5,7.5,8.
                    5,12.5''',
                    'Series:Nike Dunk',
                ],
            },
            {
                'name': "Nike Air Force 1 '07 M - White",
                'url': '''https://www.klarna.com/us/shopping/pl/cl337/3979297/
                Shoes/Nike-Air-Force-1-07-M-White/?utm_source=openai&
                ref-site=openai_plugin''',
                'price': '\$80.00',
                'attributes': [
                    'Outsole:Rubber',
                    'Fastening:Laced',
                    'Midsole:Foam',
                    'Target Group:Man',
                    'Color:White',
                    'Upper Material:Leather',
                    '''Size (US):9.5,10,11,12,13,14,15,16,17,11.5,10.5,2,3,4,5,
                    6,7,8,9,2.5,3.5,4.5,16.5,5.5,15.5,6.5,14.5,13.5,7.5,8.5,12.
                    5''',
                    'Lining Material:Textile',
                    'Series:Nike Air Force 1',
                ],
            },
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(
            q_in_query="nike shoes",
            size_in_query=2,
            min_price_in_query=50,
            max_price_in_query=100,
        )
        assert result == mock_response_data


@pytest.mark.parametrize('get_function', ['speak_translate'], indirect=True)
def test_speak_translate(get_function):
    # ruff: noqa: RUF001
    mock_response_data = {
        "explanation": '''
    <translation language="Chinese" context="Looking for the German word for 
    the fruit that is commonly red, green, or yellow.">
    苹果 (píngguǒ)
    </translation>

    <alternatives context="Looking for the German word for the fruit that is 
    commonly red, green, or yellow.">
    1. "苹果 (píngguǒ)" *(Neutral/Formal - the standard term for 'apple' in 
    Chinese)*
    2. "苹儿 (pín er)" *(Informal - a colloquial way to refer to an apple, 
    often used in Northern China)*
    3. "苹果儿 (píngguǒ er)" *(Informal - similar to "苹儿 (pín er)", used in 
    casual conversations)*
    </alternatives>

    <example-convo language="Chinese">
    <context>At a fruit market in China.</context>
    * Li: "嗨，这里有新鲜的苹果吗？" (Hi, do you have fresh apples here?)
    * Seller: "当然有！我们这里的苹果非常好吃，是从山上来的。" (Of course! 
    The apples here are delicious, they come from the mountains.)
    * Li: "好的，我要买几个红苹果。" (Great, I want to buy some red apples.)
    </example-convo>

    *[Report an issue or leave feedback](https://speak.com/chatgpt?
    rid=sjqtmni8qkvtwr6jlj3xl1lz)*
    ''',
        "extra_response_instructions": '''Use all information in the API 
        response and fully render all Markdown.\nAlways end your response with 
        a link to report an issue or leave feedback on the plugin.''',
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        translate_request = {
            "phrase_to_translate": "Wie sagt man 'apple' auf Deutsch?",
            "learning_language": "Chinese",
            "native_language": "English",
            "additional_context": '''Looking for the German word for the fruit 
            that is commonly red, green, or yellow.''',
            "full_query": "What is the German word for 'apple'?",
        }
        result = get_function(requestBody=translate_request)
        assert result == mock_response_data


@pytest.mark.parametrize('get_function', ['speak_explainPhrase'], indirect=True)
def test_speak_explainPhrase(get_function):
    mock_response_data = {
        "explanation": '''
    <markdown>
    <explanation context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    The phrase you entered is: "<input></input>"
    This phrase is commonly used in Chinese and it means "What happened?" or 
    "What's going on?" It is often used when you want to express surprise or 
    curiosity about a situation or event. Imagine someone just witnessed 
    something unexpected and they are genuinely interested in finding out more 
    details about it. 

    For example, if you witnessed a car accident on the street and you're 
    confused about what happened, you can ask "你们这是怎么回事啊？" (Nǐmen zhè 
    shì zěnme huíshì a?) which translates to "What happened here?" or "What's 
    going on here?"

    </explanation>

    <alternatives context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    Here are a few alternative phrases that convey a similar meaning and can 
    be used in different situations:

    1. "发生了什么事？" (Fāshēngle shénme shì?) - This phrase is a bit more 
    formal and it means "What happened?" It can be used in various contexts, 
    such as asking about a news event or inquiring about a situation you're 
    not familiar with.

    2. "出什么事了？" (Chū shénme shì le?) - This phrase is more casual and can 
    be translated as "What's going on?" or "What's happening?" It is often 
    used when you want to express surprise and inquire about a situation.

    3. "怎么回事？" (Zěnme huíshì?) - This phrase is similar to the first one 
    we mentioned, but it's a bit more informal. It can be used in both casual 
    and formal situations to ask "What's going on?" or "What happened?"

    </alternatives>

    <example-convo language="Chinese">
    <context>You and your friend are walking in the park when suddenly, a UFO 
    appears in the sky.</context>
    <dialogue>
    Person A: 哇，你看！天上有 个飞碟！(Wā, nǐ kàn! Tiānshàng yǒu gè 
    fēidié!) Wow, look! There's a UFO in the sky!
    Person B: 什么？你确定吗？(Shénme? Nǐ quèdìng ma?) What? Are you sure?
    Person A: 是的！你们这是怎么回事啊？(Shì de! Nǐmen zhè shì zěnme huíshì a?) 
    Yes! What happened here?
    </dialogue>
    </example-convo>
    </markdown>
    ''',
        "extra_response_instructions": '''Use all information in the API 
        response and fully render all Markdown.\nAlways end your response with 
        a link to report an issue or leave feedback on the plugin.''',
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        explain_phrase_request = {
            "foreign_phrase": "no mames",
            "learning_language": "Chinese",
            "native_language": "English",
            "additional_context": (
                "Someone said this to me after a surprising event occurred."
                "Want to understand the tone and context it's used in."
            ),
            "full_query": '''Somebody said 'no mames' to me, what does that 
            mean?''',
        }
        result = get_function(requestBody=explain_phrase_request)
        assert result == mock_response_data


@pytest.mark.parametrize('get_function', ['speak_explainTask'], indirect=True)
def test_speak_explainTask(get_function):
    mock_response_data = {
        "explanation": '''
    <markdown>
    <explanation context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    The phrase you entered is: "<input></input>"
    This phrase is commonly used in Chinese and it means "What happened?" or 
    "What's going on?" It is often used when you want to express surprise or 
    curiosity about a situation or event. Imagine someone just witnessed 
    something unexpected and they are genuinely interested in finding out more 
    details about it. 

    For example, if you witnessed a car accident on the street and you're 
    confused about what happened, you can ask "你们这是怎么回事啊？" (Nǐmen zhè 
    shì zěnme huíshì a?) which translates to "What happened here?" or "What's 
    going on here?"

    </explanation>

    <alternatives context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    Here are a few alternative phrases that convey a similar meaning and can 
    be used in different situations:

    1. "发生了什么事？" (Fāshēngle shénme shì?) - This phrase is a bit more 
    formal and it means "What happened?" It can be used in various contexts, 
    such as asking about a news event or inquiring about a situation you're 
    not familiar with.

    2. "出什么事了？" (Chū shénme shì le?) - This phrase is more casual and can 
    be translated as "What's going on?" or "What's happening?" It is often 
    used when you want to express surprise and inquire about a situation.

    3. "怎么回事？" (Zěnme huíshì?) - This phrase is similar to the first one 
    we mentioned, but it's a bit more informal. It can be used in both casual 
    and formal situations to ask "What's going on?" or "What happened?"

    </alternatives>

    <example-convo language="Chinese">
    <context>You and your friend are walking in the park when suddenly, a UFO 
    appears in the sky.</context>
    <dialogue>
    Person A: 哇，你看！天上有 个飞碟！(Wā, nǐ kàn! Tiānshàng yǒu gè 
    fēidié!) Wow, look! There's a UFO in the sky!
    Person B: 什么？你确定吗？(Shénme? Nǐ quèdìng ma?) What? Are you sure?
    Person A: 是的！你们这是怎么回事啊？(Shì de! Nǐmen zhè shì zěnme huíshì a?) 
    Yes! What happened here?
    </dialogue>
    </example-convo>
    </markdown>
    ''',
        "extra_response_instructions": '''Use all information in the API 
        response and fully render all Markdown.\nAlways end your response with 
        a link to report an issue or leave feedback on the plugin.''',
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        explain_task_request = {
            "task_description": "tell the waiter they messed up my order",
            "learning_language": "Chinese",
            "native_language": "English",
            "additional_context": (
                "I want to say it politely because it wasn't a big mistake."
            ),
            "full_query": (
                "How do I politely tell the waiter in Italian that they made "
                "a mistake with my order?"
            ),
        }
        result = get_function(requestBody=explain_task_request)
        assert result == mock_response_data
