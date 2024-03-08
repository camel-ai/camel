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

from camel.functions.google_maps_function import get_address_description


@pytest.fixture(scope="module")
def api_key():
    key = os.environ.get('GOOGLEMAPS_API_KEY')
    if not key:
        pytest.fail("GOOGLEMAPS_API_KEY environment variable is not set.")
    return key


def test_weather(api_key):
    expected_output = (
        "Address completion status: Yes. Formatted address: 1600 Amphitheatre "
        "Parkway Pk, Mountain View, CA 94043-1351, USA. Location (latitude, "
        "longitude): (37.4224719, -122.0842778). Metadata indicating true "
        "types: business.")
    assert get_address_description('1600 Amphitheatre Pk', region_code='US',
                                   locality='Mountain View') == expected_output
    