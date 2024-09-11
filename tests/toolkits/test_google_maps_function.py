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
from functools import wraps
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import GoogleMapsToolkit


def mock_googlemaps(test_func):
    @wraps(test_func)
    @patch('googlemaps.Client')
    @patch('os.environ.get')
    def wrapper(*args, **kwargs):
        mock_get = args[0]
        mock_get.return_value = 'fake_api_key'
        return test_func(*args, **kwargs)

    return wrapper


@pytest.fixture
def google_maps_toolkit():
    return GoogleMapsToolkit()


@mock_googlemaps
def test_get_address_description(mock_get, mock_client, google_maps_toolkit):
    # Create a mock response for the addressvalidation method
    mock_response = {
        'result': {
            'verdict': {'addressComplete': True},
            'address': {
                'formattedAddress': (
                    '1600 Amphitheatre Parkway Pk, Mountain View, '
                    'CA 94043-1351, USA'
                )
            },
            'geocode': {
                'location': {'latitude': 37.4225028, 'longitude': -122.0843066}
            },
            'metadata': {
                'business': True,
                'poBox': False,
                'residential': False,
            },
        }
    }

    # Configure the mock client instance to return the mock response
    mock_instance = MagicMock()
    mock_instance.addressvalidation.return_value = mock_response
    mock_client.return_value = mock_instance

    # Call the function with a test address
    result = google_maps_toolkit.get_address_description(
        '1600 Amphitheatre Pk', region_code='US', locality='Mountain View'
    )

    # Verify the result
    expected_result = (
        "Address completion status: Yes. "
        "Formatted address: 1600 Amphitheatre Parkway Pk, Mountain View, CA "
        "94043-1351, USA. Location (latitude, longitude): (37.4225028, "
        "-122.0843066). Metadata indicating true types: business."
    )
    assert result == expected_result


@mock_googlemaps
def test_get_elevation(mock_get, mock_client, google_maps_toolkit):
    # Create a mock response for the elevation method
    mock_response = [
        {
            'elevation': 10.53015995025635,
            'location': {'lat': 40.71473, 'lng': -73.99867},
            'resolution': 76.35161590576172,
        }
    ]

    # Configure the mock client instance to return the mock response
    mock_instance = MagicMock()
    mock_instance.elevation.return_value = mock_response
    mock_client.return_value = mock_instance

    # Call the function with a test latitude and longitude
    result = google_maps_toolkit.get_elevation((40.71473, -73.99867))

    # Verify the result
    expected_result = (
        "The elevation at latitude 40.71473, longitude -73.99867 "
        "is approximately 10.53 meters above sea level, "
        "with a data resolution of 76.35 meters."
    )
    assert result == expected_result


@mock_googlemaps
def test_get_timezone(mock_get, mock_client, google_maps_toolkit):
    # Create a mock response for the timezone method
    mock_response = {
        'dstOffset': 3600,
        'rawOffset': -28800,
        'status': 'OK',
        'timeZoneId': 'America/Los_Angeles',
        'timeZoneName': 'Pacific Daylight Time',
    }

    # Configure the mock client instance to return the mock response
    mock_instance = MagicMock()
    mock_instance.timezone.return_value = mock_response
    mock_client.return_value = mock_instance

    # Call the function with a test latitude and longitude
    result = google_maps_toolkit.get_timezone(
        (39.603481, -119.682251)
    )  # Coordinates for Los Angeles

    # Verify the result
    expected_result = (
        "Timezone ID is America/Los_Angeles, named Pacific Daylight Time. "
        "The standard time offset is -8.00 hours. Daylight Saving Time offset "
        "is +1.00 hour. The total offset from Coordinated Universal Time "
        "(UTC) is -7.00 hours, including any Daylight Saving Time adjustment "
        "if applicable. "
    )
    assert result == expected_result


def test_wrong_api_key(monkeypatch, google_maps_toolkit):
    monkeypatch.setenv('GOOGLEMAPS_API_KEY', 'invalid_api_key')
    expected_output = "Error: Invalid API key provided."
    assert (
        google_maps_toolkit.get_address_description(
            '1600 Amphitheatre Pk', region_code='US', locality='Mountain View'
        )
        == expected_output
    )
    assert (
        google_maps_toolkit.get_elevation((40.714728, -73.998672))
        == expected_output
    )
    assert (
        google_maps_toolkit.get_timezone((40.714728, -73.998672))
        == expected_output
    )
