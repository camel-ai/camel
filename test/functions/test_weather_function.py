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
import os

import requests

from camel.functions.weather_functions import fetch_current_weather


def test_openweather_api():
    # Check the OpenWeatherMap API
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    url = f"https://api.openweathermap.org/data/2.5/weather?" \
        f"lat=35&lon=139&appid={OPENWEATHER_API_KEY}"
    result = requests.get(url)
    assert result.status_code == 200


def test_fetch_current_weather():
    response = fetch_current_weather(
        35.682839, 139.759455)  # Tokyo coordinates
    assert response is not None
    assert "coord" in response
    assert "weather" in response
    assert "main" in response
    assert "visibility" in response
    assert "wind" in response
    assert "clouds" in response
    assert "dt" in response
    assert "sys" in response
    assert "timezone" in response
    assert "id" in response
    assert "name" in response
    assert "cod" in response


def test_invalid_api_key():
    invalid_key = "invalid_key"
    url = f"https://api.openweathermap.org/data/2.5/weather?" \
        f"lat=35&lon=139&appid={invalid_key}"
    result = requests.get(url)
    data = result.json()

    assert "cod" in data
    assert data["cod"] == 401
    assert "message" in data
    assert data["message"] == "Invalid API key. Please see " \
        "https://openweathermap.org/faq#error401 for more info."
