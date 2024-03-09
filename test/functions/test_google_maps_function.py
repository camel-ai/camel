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
import re
from datetime import datetime, timezone

import pytest

from camel.functions.google_maps_function import get_address_description, get_elevation, get_timezone


def test_get_address_description():
    expected_output = (
        "Address completion status: Yes. Formatted address: 1600 Amphitheatre "
        "Parkway Pk, Mountain View, CA 94043-1351, USA. Location (latitude, "
        "longitude): (37.4224318, -122.0841787). Metadata indicating true "
        "types: business.")
    assert get_address_description('1600 Amphitheatre Pk', region_code='US',
                                   locality='Mountain View') == expected_output
    

def test_get_elevation():
    expected_output = (
        "The elevation at latitude 40.71473, longitude -73.99867 is "
        "approximately 10.53 meters above sea level, with a data resolution "
        "of 76.35 meters.")
    assert get_elevation((40.714728, -73.998672)) == expected_output


def test_get_timezone():
    expected_output = (
        "Timezone ID is America/New_York, named Eastern Standard Time. The "
        "standard time offset is -5 hours. Daylight Saving Time offset is +0 "
        "hours. The total offset from Coordinated Universal Time (UTC) is -5 "
        "hours, including any Daylight Saving Time adjustment if applicable. ")
    assert get_timezone((40.714728, -73.998672)) == expected_output


def test_with_wrong_api_key(monkeypatch):
    monkeypatch.setenv('GOOGLEMAPS_API_KEY', 'invalid_api_key')
    expected_output = ("Error: Invalid API key provided.")
    assert get_address_description('1600 Amphitheatre Pk', region_code='US',
                                   locality='Mountain View') == expected_output
    assert get_elevation((40.714728, -73.998672)) == expected_output
    assert get_timezone((40.714728, -73.998672)) == expected_output
