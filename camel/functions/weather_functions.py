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
from typing import List

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


def get_weather_data(city: str, temp_units: str = 'kelvin',
                     wind_units: str = 'meters_sec',
                     visibility_units: str = 'meters',
                     time_units: str = 'unix') -> str:
    """
    Fetch and return a comprehensive weather report for a given city as a\
    string. The report includes current weather conditions, temperature, \
    wind details, visibility, and sunrise/sunset times, all formatted as \
    a readable string.

    The function interacts with the OpenWeatherMap API to retrieve the data.

    Args:
        city (string): The name of the city for which the weather information
                    is desired. Format "City, CountryCode" (e.g., "Paris, FR"
                    for Paris, France). If the country code is not provided,
                    the API will search for the city in all countries, which
                    may yield incorrect results if multiple cities with the
                    same name exist.
        temp_units (string): Units for temperature. Options: 'kelvin',
                          'celsius', 'fahrenheit'. Default is 'kelvin'.
        wind_units (string): Units for wind speed. Options: 'meters_sec',
                          'miles_hour', 'knots', 'beaufort'.
                          Default is 'meters_sec'.
        visibility_units (string): Units for visibility distance. Options:
                          'meters', 'miles'. Default is 'meters'.
        time_units (string): Format for sunrise and sunset times. Options:
                          'unix', 'iso', 'date'. Default is 'unix'.

    Returns:
        str: A string containing the fetched weather data, formatted in a
             readable manner. If an error occurs, a message indicating the
             error will be returned instead.

    Example of return string:
        "Weather in Paris, FR: 15°C, feels like 13°C. Max temp: 17°C, Min temp\
            : 12°C.
        Wind: 5 m/s at 270 degrees. Visibility: 10 kilometers.
        Sunrise at 05:46:05 (UTC), Sunset at 18:42:20 (UTC)."

    Note:
        Please ensure that the API key is valid and has permissions to access \
            the weather data.
    """

    OPENWEATHERMAP_API_KEY = get_openweathermap_api_key()
    owm = OWM(OPENWEATHERMAP_API_KEY)
    mgr = owm.weather_manager()

    try:
        observation = mgr.weather_at_place(city)
        weather = observation.weather

        # Temperature
        temperature = weather.temperature(temp_units)

        # Wind
        wind_data = observation.weather.wind(unit=wind_units)
        wind_speed = wind_data.get('speed')
        # 'N/A' if the degree is not available
        wind_deg = wind_data.get('deg', 'N/A')

        # Visibility
        visibility_distance = observation.weather.visibility_distance
        visibility = str(visibility_distance) if visibility_units == 'meters' \
            else str(observation.weather.visibility(unit='miles'))

        # Sunrise and Sunset
        sunrise_time = str(weather.sunrise_time(timeformat=time_units))
        sunset_time = str(weather.sunset_time(timeformat=time_units))

        # Compile all the weather details into a report string
        weather_report = (
            f"Weather in {city}: {temperature['temp']}°{temp_units.title()}, \
                feels like {temperature['feels_like']}°{temp_units.title()}. "
            f"Max temp: {temperature['temp_max']}°{temp_units.title()}, \
                Min temp: {temperature['temp_min']}°{temp_units.title()}. "
            f"Wind: {wind_speed} {wind_units} at {wind_deg} degrees. "
            f"Visibility: {visibility} {visibility_units}. "
            f"Sunrise at {sunrise_time}, Sunset at {sunset_time}.")

        return weather_report

    except Exception as e:
        error_message = f"An error occurred while fetching weather data for \
            {city}: {str(e)}"

        return error_message


WEATHER_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [get_weather_data]
]
