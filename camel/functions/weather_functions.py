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
from typing import Dict, List

from pyowm import OWM

from camel.functions import OpenAIFunction


def get_openweathermap_api_key() -> str:
    """
    Retrieve the OpenWeatherMap API key from environment variables.

    Returns:
        str: The OpenWeatherMap API key.

    Raises:
        ValueError: If the API key is not found in the environment variables.
    """
    # Get OPENWEATHERMAP_API_KEY here: https://openweathermap.org/
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
    if not OPENWEATHERMAP_API_KEY:
        raise ValueError("OPENWEATHERMAP_API_KEY not found in environment \
                          variables. Get OPENWEATHERMAP_API_KEY here: \
                         https://openweathermap.org/")
    return OPENWEATHERMAP_API_KEY


def get_current_weather(city: str, units: str = 'kelvin') -> dict:
    r"""
    Fetch current weather for a given city using the OpenWeatherMap API.
    Including details such as the current temperature, maximum temperature,
    minimum temperature, perceived temperature, and weather status for
    the specified city on the current day.

    Args:
        city (string): The city for which weather information is to be fetched.
                    Queries work best by specifying toponyms and country
                    2-letter names separated by comma. Eg: instead of using
                    "seattle", try using "seattle,WA".
        units (string): The unit system to be used. Possible values are
                        'kelvin' (default), 'celsius', and 'fahrenheit'.

    Returns:
        dict: A dictionary containing weather information including:
            - 'temp': Current temperature.
            - 'temp_max': Maximum temperature.
            - 'temp_min': Minimum temperature.
            - 'feels_like': Perceived temperature.
            - 'temp_kf': Internal parameter.
            - 'status': Brief weather status (e.g., "Rain").
            - 'detailed_status': Detailed weather status (e.g., "light rain").
            Example:
            {
                'temp': 291.14,
                'temp_max': 293.9,
                'temp_min': 288.44,
                'feels_like': 290.86,
                'temp_kf': None,
                'status': 'Rain',
                'detailed_status': 'light rain'
            }
    """

    # Retrieve the OpenWeatherMap API key
    OPENWEATHERMAP_API_KEY = get_openweathermap_api_key()
    # Create OWM manager
    owm = OWM(OPENWEATHERMAP_API_KEY)
    mgr = owm.weather_manager()

    try:
        weather = mgr.weather_at_place(city).weather
        temperature = weather.temperature(units)

        # Extract required information
        return {
            'temp': temperature['temp'],
            'temp_max': temperature['temp_max'],
            'temp_min': temperature['temp_min'],
            'feels_like': temperature['feels_like'],
            # temp_kf might not always be present
            'temp_kf': temperature.get('temp_kf', None),
            'status': weather.status,
            'detailed_status': weather.detailed_status
        }

    except Exception as e:
        # Catch any unexpected exceptions
        return {
            "error":
            f"Unexpected error occurred while fetching weather \
                for {city}. Reason: {str(e)}"
        }


def get_current_wind(city: str, units: str = 'meters_sec') -> dict:
    r"""
    Fetch wind information (speed and direction) for a given city using the \
    OpenWeatherMap API.

    Args:
        city (string): The city for which wind information is to be fetched.
                       Queries work best by specifying toponyms and country \
                        2-letter names separated by comma.
                       Eg: instead of using "seattle", try using "seattle,WA".
        units (string): The unit system to be used for wind speed. Possible \
                        values are 'meters_sec' (default),
                        'miles_hour', 'knots', and 'beaufort'.

    Returns:
        dict: A dictionary containing wind information including:
            - 'speed': Current wind speed.
            - 'deg': Wind direction in degrees (meteorological).

            Example:
            {
                'speed': 5.66,
                'deg': 180
            }
    """

    # Retrieve the OpenWeatherMap API key
    OPENWEATHERMAP_API_KEY = get_openweathermap_api_key()

    # Create OWM manager
    owm = OWM(OPENWEATHERMAP_API_KEY)
    mgr = owm.weather_manager()

    try:
        observation = mgr.weather_at_place(city)
        wind_data = observation.weather.wind(unit=units)

        # Return required wind information
        return {'speed': wind_data['speed'], 'deg': wind_data['deg']}

    except Exception as e:
        # Catch any unexpected exceptions
        return {
            "error":
            f"Unexpected error occurred while fetching wind data \
                 for {city}. Reason: {str(e)}"
        }


def get_current_visibility_distance(city: str, units: str = 'meters') -> dict:
    r"""
    Fetch visibility distance information for a given city using the \
    OpenWeatherMap API.

    Args:
        city (string): The city for which visibility distance information is \
                    to be fetched. Queries work best by specifying toponyms \
                        and country 2-letter names separated by comma.
                    Eg: instead of using "seattle", try using "seattle,WA".
        units (string): The unit system to be used. Possible values are \
                    'meters' (default), and 'miles'.

    Returns:
        dict: A dictionary containing visibility distance for the given city \
            in the specified unit.
            Example:
            {"visibility_distance": 10000.0}
    """

    # Retrieve the OpenWeatherMap API key
    OPENWEATHERMAP_API_KEY = get_openweathermap_api_key()

    # Create OWM manager
    owm = OWM(OPENWEATHERMAP_API_KEY)
    mgr = owm.weather_manager()

    try:
        observation = mgr.weather_at_place(city)

        # Fetch visibility based on specified units
        if units == 'meters':
            visibility_distance = observation.weather.visibility_distance
        elif units == 'miles':
            visibility_distance = observation.weather.visibility(unit='miles')
        else:
            return {"error": f"Unsupported unit: {units}"}

        return {"visibility_distance": visibility_distance}

    except Exception as e:
        # Catch any unexpected exceptions
        return {
            "error":
            f"Unexpected error occurred while fetching \
                visibility distance for {city}. Reason: {str(e)}"
        }


def get_sunrise_sunset(city: str, units: str = 'unix') -> Dict[str, str]:
    r"""
    Get sunrise and sunset times for a given city using the OpenWeatherMap API.

    Args:
        city (string): The city for which sunrise and sunset times are to be \
                    fetched.
        units (string): The unit system for time format. Supported values: \
                    'unix' (default), 'iso', 'date'.

    Returns:
        Dict[str, str]: A dictionary containing sunrise and sunset times in \
                    the specified format.

    Example:
    {
        'sunrise_time': '2023-10-28 06:46:05+00:00',
        'sunset_time': '2023-10-28 16:42:20+00:00'
    }
    """

    # Retrieve the OpenWeatherMap API key
    OPENWEATHERMAP_API_KEY = get_openweathermap_api_key()

    # Create OWM manager
    owm = OWM(OPENWEATHERMAP_API_KEY)
    mgr = owm.weather_manager()

    try:
        observation = mgr.weather_at_place(city)
        weather = observation.weather
        sunrise_time = weather.sunrise_time(timeformat=units)
        sunset_time = weather.sunset_time(timeformat=units)

        # Extract and format sunrise and sunset times
        return {'sunrise_time': sunrise_time, 'sunset_time': sunset_time}

    except Exception as e:
        # Handle any exceptions that may occur during the request
        return {
            "error":
            f"Failed to fetch sunrise and sunset times for \
                {city}. Reason: {str(e)}"
        }


WEATHER_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [
        get_current_weather, get_current_wind, get_current_visibility_distance,
        get_sunrise_sunset
    ]
]
