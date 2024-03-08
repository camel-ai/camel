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


def import_googlemaps_or_raise():
    try:
        import googlemaps
        return googlemaps
    except ImportError:
        raise ImportError("Please install `googlemaps` first. You can install "
                          "it by running `pip install googlemaps`.")
    

# @check_googlemaps_installed
def get_address_description(address, region_code, locality):
    googlemaps = import_googlemaps_or_raise()
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


def handle_googlemaps_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApiError as e:
            return f"An exception returned by the remote API. Status: {e.status}, Message: {e.message}"
        except HTTPError as e:
            return f"An unexpected HTTP error occurred. Status Code: {e.status_code}"
        except Timeout as e:
            return "The request timed out. "
        except TransportError as e:
            return f"Something went wrong while trying to execute the request. Details: {e.base_exception}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
    return wrapper


@handle_googlemaps_exceptions
def get_elevation(lat_lng):
    googlemaps = import_googlemaps_or_raise()
    from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
    GOOGLEMAPS_API_KEY = get_googlemap_api_key()
    gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

    # Assuming gmaps is a configured Google Maps client instance
    elevation_result = gmaps.elevation(lat_lng)
    
    # Extract the elevation data from the first (and presumably only) result
    if elevation_result:
        elevation = elevation_result[0]['elevation']
        location = elevation_result[0]['location']
        resolution = elevation_result[0]['resolution']

        # Format the elevation data into a natural language description
        description = (f"The elevation at latitude {location['lat']}, longitude {location['lng']} "
                       f"is approximately {elevation:.2f} meters above sea level, "
                       f"with a data resolution of {resolution:.2f} meters.")
    else:
        description = "Elevation data is not available for the given location."

    return description


# Function to convert offsets to a more natural language description
def format_offset_to_natural_language(offset):
    hours = offset // 3600
    minutes = (offset % 3600) // 60
    seconds = offset % 60
    parts = []
    if hours or (hours == 0 and minutes == 0 and seconds == 0):
        parts.append(f"{abs(hours)} hour{'s' if abs(hours) != 1 else ''}")
    if minutes:
        parts.append(f"{abs(minutes)} minute{'s' if abs(minutes) != 1 else ''}")
    if seconds:
        parts.append(f"{abs(seconds)} second{'s' if abs(seconds) != 1 else ''}")
    return f"{'-' if offset < 0 else '+'}{' '.join(parts)}"


@handle_googlemaps_exceptions
def get_timezone(lat_lng):
    googlemaps = import_googlemaps_or_raise()
    from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
    GOOGLEMAPS_API_KEY = get_googlemap_api_key()
    gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

    # Get timezone information
    timezone_dict = gmaps.timezone(lat_lng)

    # Extract necessary information
    dst_offset = timezone_dict['dstOffset']  # Daylight Saving Time offset in seconds
    raw_offset = timezone_dict['rawOffset']  # Standard time offset in seconds
    timezone_id = timezone_dict['timeZoneId']
    timezone_name = timezone_dict['timeZoneName']

    raw_offset_str = format_offset_to_natural_language(raw_offset)
    dst_offset_str = format_offset_to_natural_language(dst_offset)
    total_offset_seconds = dst_offset + raw_offset
    total_offset_str = format_offset_to_natural_language(total_offset_seconds)
    
    # Create a natural language description
    description = (f"Timezone ID is {timezone_id}, named {timezone_name}. "
                   f"The standard time offset is {raw_offset_str}. "
                   f"Daylight Saving Time offset is {dst_offset_str}. "
                   f"The total offset from Coordinated Universal Time (UTC) is {total_offset_str}, "
                   f"including any Daylight Saving Time adjustment if applicable. ")

    return description


MAP_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [get_address_description, get_elevation, get_timezone]
]