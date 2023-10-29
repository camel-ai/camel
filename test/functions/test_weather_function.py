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
import datetime
import os

import pytest

from camel.functions.weather_functions import (
    get_current_visibility_distance,
    get_current_weather,
    get_current_wind,
    get_sunrise_sunset,
)


# Ensure the OPENWEATHERMAP_API_KEY environment variable is set
@pytest.fixture(scope="module")
def api_key():
    key = os.environ.get('OPENWEATHERMAP_API_KEY')
    if not key:
        pytest.fail("OPENWEATHERMAP_API_KEY environment variable is not set.")
    return key


def test_get_current_weather(api_key):
    city = "London,GB"

    # Test with celsius
    units_celsius = "celsius"
    result_celsius = get_current_weather(city, units_celsius)

    # Ensure all required keys are in the result for celsius
    assert all(key in result_celsius for key in [
        'temp', 'temp_max', 'temp_min', 'feels_like', 'temp_kf', 'status',
        'detailed_status'
    ])
    assert -100 <= result_celsius["temp"] <= 60
    assert -100 <= result_celsius["temp_max"] <= 60
    assert -100 <= result_celsius["temp_min"] <= 60
    assert -100 <= result_celsius["feels_like"] <= 60

    # Test with kelvin
    units_kelvin = "kelvin"
    result_kelvin = get_current_weather(city, units_kelvin)

    # Ensure all required keys are in the result for kelvin
    assert all(key in result_kelvin for key in [
        'temp', 'temp_max', 'temp_min', 'feels_like', 'temp_kf', 'status',
        'detailed_status'
    ])
    # Kelvin values for extreme cold and hot conditions on Earth
    assert 173 <= result_kelvin["temp"] <= 333
    assert 173 <= result_kelvin["temp_max"] <= 333
    assert 173 <= result_kelvin["temp_min"] <= 333
    assert 173 <= result_kelvin["feels_like"] <= 333

    # Test with fahrenheit
    units_fahrenheit = "fahrenheit"
    result_fahrenheit = get_current_weather(city, units_fahrenheit)

    # Ensure all required keys are in the result for fahrenheit
    assert all(key in result_fahrenheit for key in [
        'temp', 'temp_max', 'temp_min', 'feels_like', 'temp_kf', 'status',
        'detailed_status'
    ])
    # Fahrenheit values for extreme cold and hot conditions on Earth
    assert -148 <= result_fahrenheit["temp"] <= 140
    assert -148 <= result_fahrenheit["temp_max"] <= 140
    assert -148 <= result_fahrenheit["temp_min"] <= 140
    assert -148 <= result_fahrenheit["feels_like"] <= 140

    # Ensure the status fields are strings
    assert isinstance(result_celsius["status"], str)
    assert isinstance(result_celsius["detailed_status"], str)
    assert isinstance(result_kelvin["status"], str)
    assert isinstance(result_kelvin["detailed_status"], str)
    assert isinstance(result_fahrenheit["status"], str)
    assert isinstance(result_fahrenheit["detailed_status"], str)


def test_get_current_wind(api_key):
    city = "London,GB"

    # Test with meters per second
    units_mps = "meters_sec"
    result_mps = get_current_wind(city, units_mps)
    assert all(key in result_mps for key in ['speed', 'deg'])
    assert 0 <= result_mps["speed"] <= 200
    assert 0 <= result_mps["deg"] <= 360

    # Test with miles per hour
    units_mph = "miles_hour"
    result_mph = get_current_wind(city, units_mph)
    assert all(key in result_mph for key in ['speed', 'deg'])
    assert 0 <= result_mph["speed"] <= 447  # Speed in mph

    # Test with knots
    units_knots = "knots"
    result_knots = get_current_wind(city, units_knots)
    assert all(key in result_knots for key in ['speed', 'deg'])
    assert 0 <= result_knots["speed"] <= 390  # Speed in knots

    # Test with beaufort scale
    units_beaufort = "beaufort"
    result_beaufort = get_current_wind(city, units_beaufort)
    assert all(key in result_beaufort for key in ['speed', 'deg'])
    # Beaufort scale is ordinal and goes from 0 to 12
    assert 0 <= result_beaufort["speed"] <= 12
    assert 0 <= result_beaufort["deg"] <= 360


def test_get_current_visibility_distance(api_key):
    city = "London,GB"

    # Test with default units (meters)
    result_meters = get_current_visibility_distance(city)
    assert isinstance(result_meters, dict)
    assert "visibility_distance" in result_meters
    assert isinstance(result_meters["visibility_distance"], (int, float))
    # Assuming max visibility in meters
    assert 0 <= result_meters["visibility_distance"] <= 400000
    # Test with miles
    units_miles = "miles"
    result_miles = get_current_visibility_distance(city, units_miles)
    assert isinstance(result_miles, dict)
    assert "visibility_distance" in result_miles
    assert isinstance(result_miles["visibility_distance"], (int, float))
    # Assuming max visibility in miles
    assert 0 <= result_miles["visibility_distance"] <= 250


def test_get_sunrise_sunset(api_key):
    city = "London,GB"
    units = "unix"
    result_unix = get_sunrise_sunset(city, units)
    assert 'sunrise_time' in result_unix
    assert 'sunset_time' in result_unix

    # Test with ISO format
    units_iso = "iso"
    result_iso = get_sunrise_sunset(city, units_iso)
    assert 'sunrise_time' in result_iso
    assert 'sunset_time' in result_iso

    # Test with datetime format
    units_datetime = "date"
    result_datetime = get_sunrise_sunset(city, units_datetime)
    assert 'sunrise_time' in result_datetime
    assert 'sunset_time' in result_datetime

    # Ensure sunrise time is earlier than sunset time
    sunrise_time = result_unix['sunrise_time']
    sunset_time = result_unix['sunset_time']
    assert sunrise_time < sunset_time

    # Ensure sunrise time is earlier than sunset time in ISO format
    sunrise_iso = datetime.datetime.fromisoformat(result_iso['sunrise_time'])
    sunset_iso = datetime.datetime.fromisoformat(result_iso['sunset_time'])
    assert sunrise_iso < sunset_iso

    # Ensure sunrise time is earlier than sunset time in datetime format
    sunrise_datetime = result_datetime['sunrise_time']
    sunset_datetime = result_datetime['sunset_time']
    assert sunrise_datetime < sunset_datetime
