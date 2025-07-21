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
import os
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import WeatherToolkit


@pytest.fixture(scope="module")
def api_key():
    return "mock_api_key"


@pytest.fixture
def weather_toolkit():
    return WeatherToolkit()


@patch.dict(os.environ, {'OPENWEATHERMAP_API_KEY': 'mock_api_key'})
@patch('pyowm.OWM')
def test_weather(mock_owm_class, api_key, weather_toolkit):
    # Mock OWM and weather manager
    mock_owm_instance = MagicMock()
    mock_owm_class.return_value = mock_owm_instance
    mock_mgr = MagicMock()
    mock_owm_instance.weather_manager.return_value = mock_mgr

    # Mock observation and weather
    mock_observation = MagicMock()
    mock_weather = MagicMock()
    mock_observation.weather = mock_weather

    # Configure weather methods to return appropriate data
    def temperature_side_effect(unit):
        temps = {
            'celsius': {
                'temp': 15.0,
                'feels_like': 13.0,
                'temp_max': 17.0,
                'temp_min': 12.0,
            },
            'kelvin': {
                'temp': 288.0,
                'feels_like': 286.0,
                'temp_max': 290.0,
                'temp_min': 285.0,
            },
            'fahrenheit': {
                'temp': 59.0,
                'feels_like': 55.0,
                'temp_max': 63.0,
                'temp_min': 54.0,
            },
        }
        return temps.get(unit, temps['kelvin'])

    def wind_side_effect(unit):
        winds = {
            'meters_sec': {'speed': 5.0, 'deg': 270},
            'miles_hour': {'speed': 11.0, 'deg': 270},
            'knots': {'speed': 10.0, 'deg': 270},
            'beaufort': {'speed': 3.0, 'deg': 270},
        }
        return winds.get(unit, winds['meters_sec'])

    mock_weather.temperature = MagicMock(side_effect=temperature_side_effect)
    mock_weather.wind = MagicMock(side_effect=wind_side_effect)
    mock_weather.visibility_distance = 10000
    mock_weather.visibility = MagicMock(return_value=6.2)
    mock_weather.sunrise_time = MagicMock(
        side_effect=lambda timeformat: {
            'unix': '1700000000',
            'iso': '2023-11-14 05:46:05',
            'date': '2023-11-14 05:46:05+00:00',
        }.get(timeformat, '1700000000')
    )
    mock_weather.sunset_time = MagicMock(
        side_effect=lambda timeformat: {
            'unix': '1700040000',
            'iso': '2023-11-14 18:42:20',
            'date': '2023-11-14 18:42:20+00:00',
        }.get(timeformat, '1700040000')
    )

    # Set manager to return mock observation
    mock_mgr.weather_at_place.return_value = mock_observation

    # Test temperature in Paris, FR.
    city = "Paris, FR"
    temp_units_options = {
        'celsius': (-100, 60),
        'kelvin': (173, 333),
        'fahrenheit': (-148, 140),
    }
    for temp_units, (temp_min, temp_max) in temp_units_options.items():
        report = weather_toolkit.get_weather_data(
            city, temp_units, 'meters_sec', 'meters', 'iso'
        )
        # Parse temperature
        pattern = re.compile(
            rf"Weather in .+: (-?\d+\.?\d*)°{temp_units.title()},"
        )
        match = pattern.search(report)
        temp = float(match.group(1)) if match else None
        # Test temperature
        assert (
            temp is not None
        ), "Temperature information is missing from the report"
        assert (
            temp_min <= temp <= temp_max
        ), f"Temperature {temp} not in range for {temp_units}"

    # Test wind speed in Jeddah, Saudi Arabia.
    city = "Jeddah"
    wind_units_options = {
        'meters_sec': (0, 200),
        'miles_hour': (0, 447),
        'knots': (0, 390),
        'beaufort': (0, 12),
    }
    for wind_units, (wind_min, wind_max) in wind_units_options.items():
        report = weather_toolkit.get_weather_data(
            city, 'celsius', wind_units, 'meters', 'iso'
        )
        # Parse wind speed
        pattern = re.compile(rf"Wind: (-?\d+\.?\d*) {wind_units} at")
        match = pattern.search(report)
        wind_speed = float(match.group(1)) if match else None
        # Test wind speed
        assert (
            wind_speed is not None
        ), "Wind speed information is missing from the report"
        assert (
            wind_min <= wind_speed <= wind_max
        ), f"Wind speed {wind_speed} not in range for {wind_units}"

    # Test visibility distance in Harbin, China.
    city = "Harbin, China"
    visibility_units_options = {'meters': (0, 400000), 'miles': (0, 250)}
    for visibility_units, visibility_range in visibility_units_options.items():
        visibility_min, visibility_max = visibility_range
        report = weather_toolkit.get_weather_data(
            city, 'celsius', 'meters_sec', visibility_units, 'iso'
        )
        # Parse visibility
        pattern = re.compile(
            rf"Visibility: (-?\d+\.?\d*) {visibility_units}\."
        )
        match = pattern.search(report)
        visibility = float(match.group(1)) if match else None
        # Test visibility
        assert (
            visibility is not None
        ), "Visibility information is missing from the report"
        assert (
            visibility_min <= visibility <= visibility_max
        ), f"Visibility {visibility} not in range for {visibility_units}"

    # Test sunrise and sunset time in London,GB.
    city = "London,GB"
    # Test each time_units option
    time_units_options = ['unix', 'iso', 'date']
    for time_units in time_units_options:
        report = weather_toolkit.get_weather_data(
            city, 'celsius', 'meters_sec', 'meters', time_units
        )
        # Regex to extract sunrise and sunset times based on time_units
        pattern_map = {
            'unix': (r"Sunrise at (\d+), Sunset at (\d+)."),
            'iso': (
                r"Sunrise at ([\d-]+\s[\d:]+), " r"Sunset at ([\d-]+\s[\d:]+)."
            ),
            'date': (
                r"Sunrise at ([\d-]+\s[\d:]+\+00:00), "
                r"Sunset at ([\d-]+\s[\d:]+\+00:00)."
            ),
        }
        pattern = re.compile(pattern_map[time_units])
        match = pattern.search(report)
        # Ensure sunrise and sunset times are found in the report
        assert match, (
            "Sunrise and sunset information in {} "
            "format is missing from the report.".format(time_units)
        )
        sunrise_str, sunset_str = match.groups()
        # Parse times according to format
        time_format_map = {
            'unix': '%s',
            'iso': '%Y-%m-%d %H:%M:%S',
            # The 'date' format includes timezone information for parsing
            'date': '%Y-%m-%d %H:%M:%S%z',
        }
        if time_units == 'unix':
            sunrise_time = datetime.fromtimestamp(
                int(sunrise_str), tz=timezone.utc
            )
            sunset_time = datetime.fromtimestamp(
                int(sunset_str), tz=timezone.utc
            )
        else:
            sunrise_format = time_format_map[time_units]
            sunrise_time = datetime.strptime(sunrise_str, sunrise_format)
            sunset_time = datetime.strptime(sunset_str, sunrise_format)
        # Check that sunrise occurs before sunset
        assert (
            sunrise_time < sunset_time
        ), "Sunrise time is not before sunset time in the report."
