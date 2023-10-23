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
from typing import Any, Dict, List

import requests

from .openai_function import OpenAIFunction


def fetch_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    r"""Fetch the current weather data for the specified
    latitude and longitude. Temperature in Kelvin is used by default.

    Args:
        lat (number): The latitude of the location.
        lon (number): The longitude of the location.

    Returns:
        Dict[str, Any]: A dictionary containing various weather parameters,
        including:
            - 'coord': A dictionary containing 'lon' and 'lat'.
            - 'weather': A list of dictionaries containing 'id', 'main', \
                'description', and 'icon'.
            - 'base': Internal parameter.
            - 'main': A dictionary containing 'temp', 'feels_like', \
                'temp_min', 'temp_max', 'pressure', 'humidity', \
                    'sea_level', and 'grnd_level'.
            - 'visibility': Visibility, meter.
            - 'wind': A dictionary containing 'speed', 'deg', and 'gust'.
            - 'rain': A dictionary with '1h'.
            - 'clouds': A dictionary with 'all'.
            - 'dt': Time of data calculation, UTC.
            - 'sys': A dictionary containing 'type', 'id', \
                'country', 'sunrise', and 'sunset'.
            - 'timezone': Shift in seconds from UTC.
            - 'id': City ID.
            - 'name': City name.
            - 'cod': Internal parameter.

            Example:
            {
                "coord": {"lon": 10.99, "lat": 44.34},
                "weather": [
                    {"id": 501, "main": "Rain", "description": \
                        "moderate rain", "icon": "10d"}
                ],
                "base": "stations",
                "main": {
                    "temp": 298.48,
                    "feels_like": 298.74,
                    "temp_min": 297.56,
                    "temp_max": 300.05,
                    "pressure": 1015,
                    "humidity": 64,
                    "sea_level": 1015,
                    "grnd_level": 933
                },
                "visibility": 10000,
                "wind": {"speed": 0.62, "deg": 349, "gust": 1.18},
                "rain": {"1h": 3.16},
                "clouds": {"all": 100},
                "dt": 1661870592,
                "sys": {
                    "type": 2,
                    "id": 2075663,
                    "country": "IT",
                    "sunrise": 1661834187,
                    "sunset": 1661882248
                },
                "timezone": 7200,
                "id": 3163858,
                "name": "Zocca",
                "cod": 200
            }

    Raises:
        requests.RequestException: If the request to the OpenWeather API fails.

    """
    # Get the API key from environment variable
    # Obtain the OPENWEATHER_API_KEY from here: https://openweathermap.org"
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
    )

    try:
        response = requests.get(url)
        # Raises a requests.RequestException if the response status is not 200
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        return {"error": "Request failed: " + str(e)}


WEATHER_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [fetch_current_weather]
]
