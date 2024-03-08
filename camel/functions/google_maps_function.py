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
from typing import List, Literal
from functools import wraps

from camel.functions import OpenAIFunction


def get_googlemap_api_key() -> str:
    r"""Retrieve the Google Maps API key from environment variables.

    Returns:
        str: The Google Maps API key.

    Raises:
        ValueError: If the API key is not found in the environment variables.
    """
    # Get `GOOGLEMAPS_API_KEY` here:
    # https://console.cloud.google.com/apis/credentials
    GOOGLEMAPS_API_KEY = os.environ.get('GOOGLEMAPS_API_KEY')
    if not GOOGLEMAPS_API_KEY:
        raise ValueError("`GOOGLEMAPS_API_KEY` not found in environment "
                         "variables. `GOOGLEMAPS_API_KEY` API keys are "
                         "generated in the `Credentials` page of the "
                         "`APIs & Services` tab of "
                         "https://console.cloud.google.com/apis/credentials.")
    return GOOGLEMAPS_API_KEY


def check_googlemaps_installed(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            import googlemaps
            from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
        except ImportError:
            raise ImportError(
                "Please install `googlemaps` first. You can install it by "
                "running `pip install googlemaps`.")
        return f(*args, **kwargs, googlemaps=googlemaps)
    return wrapper


@check_googlemaps_installed
def get_address_description(address, region_code, locality, googlemaps):   
    GOOGLEMAPS_API_KEY = get_googlemap_api_key()
    gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

    try:
        # Call the Google Maps address validation service with enableUspsCass set to False
        addressvalidation_result = gmaps.addressvalidation([address], 
                                                            regionCode=region_code,
                                                            locality=locality, 
                                                            enableUspsCass=False)  # Always False as per requirements
        
        # Check if the result contains an error
        if 'error' in addressvalidation_result:
            error_info = addressvalidation_result['error']
            error_message = error_info.get('message', 'An unknown error occurred')
            error_status = error_info.get('status', 'UNKNOWN_STATUS')
            error_code = error_info.get('code', 'UNKNOWN_CODE')
            return (f"Address validation failed with error: {error_message} "
                    f"Status: {error_status}, Code: {error_code}")

        # Assuming the successful response structure includes a 'result' key
        result = addressvalidation_result['result']
        verdict = result.get('verdict', {})
        address_info = result.get('address', {})
        geocode = result.get('geocode', {})
        metadata = result.get('metadata', {})

        # Construct the descriptive string
        address_complete = "Yes" if verdict.get('addressComplete', False) else "No"
        formatted_address = address_info.get('formattedAddress', 'Not available')
        location = geocode.get('location', {})
        latitude = location.get('latitude', 'Not available')
        longitude = location.get('longitude', 'Not available')
        true_metadata_types = [key for key, value in metadata.items() if value]
        true_metadata_types_str = ', '.join(true_metadata_types) if true_metadata_types else 'None'

        description = (f"Address completion status: {address_complete}. "
                       f"Formatted address: {formatted_address}. "
                       f"Location (latitude, longitude): ({latitude}, {longitude}). "
                       f"Metadata indicating true types: {true_metadata_types_str}.")

        return description
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


MAP_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [get_address_description]
]