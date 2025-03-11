# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import OpenAPIToolkit


@pytest.fixture(scope="module")
def functions_dict():
    toolkit = OpenAPIToolkit()
    apinames_filepaths = toolkit.generate_apinames_filepaths()
    openapi_functions_list, _ = toolkit.apinames_filepaths_to_funs_schemas(
        apinames_filepaths
    )
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
                'price': r'$81.00',
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
                'price': r'$80.00',
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


@pytest.mark.parametrize(
    'get_function', ['speak_explainPhrase'], indirect=True
)
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
    confused about what happened, you can ask "你们这是怎么回事啊？" 
    (Nǐmen zhè shì zěnme huíshì a?) which translates to "What 
    happened here?" or "What's going on here?"

    </explanation>

    <alternatives context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    Here are a few alternative phrases that convey a similar meaning and can 
    be used in different situations:

    1. "发生了什么事？" (Fāshēngle shénme shì?) - This phrase is a bit more 
    formal and it means "What happened?" It can be used in various contexts, 
    such as asking about a news event or inquiring about a situation you're 
    not familiar with.

    2. "出什么事了？" (Chū shénme shì le?) - This phrase is more 
    casual and can be translated as "What's going on?" or "What's 
    happening?" It is often used when you want to express surprise 
    and inquire about a situation.

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
    Person A: 是的！你们这是怎么回事啊？(Shì de! Nǐmen zhè shì 
    zěnme huíshì a?) 
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
    confused about what happened, you can ask "你们这是怎么回事啊？" 
    (Nǐmen zhè shì zěnme huíshì a?) which translates to "What happened 
    here?" or "What's going on here?"

    </explanation>

    <alternatives context="Someone said this to me after a surprising event 
    occurred. Want to understand the tone and context it's used in.">
    Here are a few alternative phrases that convey a similar meaning and can 
    be used in different situations:

    1. "发生了什么事？" (Fāshēngle shénme shì?) - This phrase is a bit more 
    formal and it means "What happened?" It can be used in various contexts, 
    such as asking about a news event or inquiring about a situation you're 
    not familiar with.

    2. "出什么事了？" (Chū shénme shì le?) - This phrase is more casual and 
    can be translated as "What's going on?" or "What's happening?" It is 
    often used when you want to express surprise and inquire about a 
    situation.

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
    Person B: 什么？你确定吗？(Shénme? Nǐ quèdìng ma?) What? Are 
    you sure?
    Person A: 是的！你们这是怎么回事啊？(Shì de! Nǐmen zhè shì zěnme 
    huíshì a?) 
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


@pytest.mark.parametrize('get_function', ['nasa_apod_get_apod'], indirect=True)
def test_nasa_apod_get_apod(get_function, monkeypatch):
    monkeypatch.setenv('NASA_API_KEY', 'fake_api_key')
    mock_response_data = {
        "copyright": "Yann Sainty",
        "date": "2023-08-17",
        "explanation": (
            "Sprawling emission nebulae IC 1396 and Sh2-129 mix glowing "
            "interstellar gas and dark dust clouds in this nearly 12 degree "
            "wide field of view toward the northern constellation Cepheus the "
            "King. Energized by its central star IC 1396 (left), is hundreds "
            "of light-years across and some 3,000 light-years distant. The "
            "nebula's intriguing dark shapes include a winding dark cloud"
            "popularly known as the Elephant's Trunk below and right of "
            "center. Tens of light-years long, it holds the raw material for "
            "star formation and is known to hide protostars within. Located a "
            "similar distance from planet Earth, the bright knots and swept "
            "back ridges of emission of Sh2-129 on the right suggest its "
            "popular name, the Flying Bat Nebula. Within the Flying Bat, "
            "the most recently recognized addition to this royal cosmic zoo "
            "is the faint bluish emission from Ou4, the Giant Squid Nebula. "
            "Near the lower right edge of the frame, the suggestive dark "
            "marking on the sky cataloged as Barnard 150 is also known as the "
            "dark Seahorse Nebula. Notable submissions to APOD: Perseids "
            "Meteor Shower 2023"
        ),
        "hdurl": (
            "https://apod.nasa.gov/apod/image/2308/"
            "ElephantTrunkBatSquidSeahorse.jpg"
        ),
        "media_type": "image",
        "service_version": "v1",
        "title": "A Cosmic Zoo in Cepheus",
        "url": (
            "https://apod.nasa.gov/apod/image/2308/"
            "ElephantTrunkBatSquidSeahorse1024.jpg"
        ),
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(date_in_query='2023-08-17', hd_in_query=True)
        assert result == mock_response_data


@pytest.mark.parametrize('get_function', ['biztoc_getNews'], indirect=True)
def test_biztoc_getNews(get_function):
    mock_response_data = [
        {
            "title": "Republican on Fox Calls for the GOP to ‘Shut Down the"
            " Economy’ to Fix Immigration: ‘We Should, Really’",
            "source": "mediaite.com",
            "date": "Tue, 21 May 2024",
            "summary": "Republican Congresswoman Victoria Spartz joined Fox"
            " Business host Maria Bartiromo to discuss border security,"
            " calling for drastic measures.",
            "image": "https://c.biztoc.com/p/c7a5cea54ed2bdd5/s.webp",
            "tags": ["victoriaspartz", "borderpatrol", "immigration"],
            "url": "https://www.mediaite.com/tv/"
            "republican-on-fox-calls-for-the-gop-to-shut-down-the-economy-to-"
            "fix-immigration-we-should-really/?ref=biztoc.com",
        }
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(query_in_query='llm Agent')
        assert result == mock_response_data


@pytest.mark.parametrize(
    'get_function', ['create_qr_code_getQRCode'], indirect=True
)
def test_create_qr_code_getQRCode(get_function):
    mock_response_data = {
        'img_tag': """<img src="https://api.qrserver.com/v1/create-qr-code/?
        data=The data to encode in the QR code.&size=120x120"
        'alt="The alt text for the QR code image." title="The title for the QR 
        code image." />'"""
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(
            data_in_query="The data to encode in the QR code.",
            size_in_query="120x120",
            alt_in_query="The alt text for the QR code image.",
            title_in_query="The title for the QR code image.",
        )
        assert result == mock_response_data


@pytest.mark.parametrize(
    'get_function', ['outschool_searchClasses'], indirect=True
)
def test_out_school_searchClasses(get_function):
    mock_response_data = [
        {
            "uid": "f170ecbb-4ceb-41ad-af1a-3ac68f120833",
            "title": "1:1 Math Tutoring With a Math Major/Teacher",
            "summary": "Personalized 1:1 math tutoring by an experienced Math"
            " Major/Teacher for Grades 2 through 10.",
            "subject": "Math",
            "duration_minutes": 40,
            "price_cents": 4500,
            "age_min": 7,
            "age_max": 15,
            "url": "https://outschool.com/classes/"
            "11-math-tutoring-with-a-math-majorteacher-fYCdDueY?"
            "utm_medium=chatgpt&utm_source=chatgpt-plugin",
            "photo": "https://cdn.filestackcontent.com/vDVX6iIaQiKdguqAzI7e",
            "teacher": {
                "name": "Tess Monte, M.Ed.",
                "photo": "https://cdn.filestackcontent.com/"
                "enevVCpZSKqAR4u0Nolt",
                "averageActivityStarRating": 5,
                "reviewCount": 2,
                "url": "https://outschool.com/teachers/Ms-Tess?"
                "utm_medium=chatgpt&utm_source=chatgpt-plugin",
            },
        }
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(
            timeZone_in_query="America/Los_Angeles",
            age_in_query=12,
            q_in_query='math',
        )
        assert result == mock_response_data


@pytest.mark.parametrize(
    'get_function', ['outschool_searchTeachers'], indirect=True
)
def test_out_school_searchTeachers(get_function):
    mock_response_data = [
        {
            "uid": "9b4d48b8-80ee-474d-bdc9-73a2b76e3432",
            "name": "Alice Maundrell, B.Mus, M.Ed ",
        },
        {"uid": "ce93ca8f-34a3-463f-a1c6-fedfc5ebd983", "name": "Ms Alice "},
        {"uid": "7e09d0bb-ba47-4e1a-a024-d22063fe083c", "name": "Alice Wang"},
        {"uid": "5ffdce7f-6eed-4721-ba6a-05227fc86f3d", "name": "Alice"},
        {
            "uid": "64ab28c8-35ac-4c23-8869-bd798bec969a",
            "name": "Alice Campbell ",
        },
        {"uid": "af351235-624f-4a28-9835-ff5628bbc6ba", "name": "Alice H."},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(name_in_query="Alice", limit_in_query=2)
        assert result == mock_response_data


@pytest.mark.parametrize('get_function', ['web_scraper_scrape'], indirect=True)
def test_web_scraper_scrape(get_function):
    mock_response_data = {
        "text": """Skip to content\nNavigation Menu\nSign in\ncamel-ai\n/
        \ncamel\nPublic\nNotifications\nFork 558\n Star 4.5k""",
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    with patch('requests.request', return_value=mock_response):
        result = get_function(
            requestBody={
                "url": "https://github.com/camel-ai/camel/tree/master",
                "type": "text",
            }
        )
        assert result == mock_response_data
