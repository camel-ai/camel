# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import sys
from unittest.mock import MagicMock, patch

# Create mock for datacommons_client module
mock_datacommons_client = MagicMock()
sys.modules['datacommons_client'] = mock_datacommons_client


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_triples_outgoing():
    # Reset mock for fresh test
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    dcids = ['geoId/06', 'geoId/21']
    expected_data = {
        'geoId/06': [('name', 'California'), ('typeOf', 'State')],
        'geoId/21': [('name', 'Kentucky'), ('typeOf', 'State')],
    }

    mock_response = MagicMock()
    mock_response.data = expected_data
    mock_client.node.fetch.return_value = mock_response

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_triples_outgoing(dcids)

    assert result == expected_data
    mock_client.node.fetch.assert_called_once_with(dcids, expression="->*")
    print("test_get_triples_outgoing passed successfully")


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_triples_incoming():
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    dcids = ['geoId/06', 'geoId/21']
    expected_data = {
        'geoId/06': [('containedInPlace', 'country/USA')],
        'geoId/21': [('containedInPlace', 'country/USA')],
    }

    mock_response = MagicMock()
    mock_response.data = expected_data
    mock_client.node.fetch.return_value = mock_response

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_triples_incoming(dcids)

    assert result == expected_data
    mock_client.node.fetch.assert_called_once_with(dcids, expression="<-*")
    print("test_get_triples_incoming passed successfully")


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_stat():
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    date = "2023"
    entity_dcids = "geoId/06"
    variable_dcids = "Count_Person"
    expected_by_variable = {
        'Count_Person': {'geoId/06': {'date': '2023', 'value': 39538223}}
    }

    mock_response = MagicMock()
    mock_response.byVariable = expected_by_variable
    mock_client.observation.fetch_observations_by_entity_dcid.return_value = (
        mock_response
    )

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_stat(date, entity_dcids, variable_dcids)

    assert result == expected_by_variable
    mock_client.observation.fetch_observations_by_entity_dcid.assert_called_once_with(
        date, entity_dcids, variable_dcids
    )
    print("test_get_stat passed successfully")


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_property_labels():
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    dcids = ['geoId/5508']
    expected_data = {
        'geoId/5508': [
            'containedInPlace',
            'geoId',
            'name',
            'typeOf',
        ]
    }

    mock_response = MagicMock()
    mock_response.data = expected_data
    mock_client.node.fetch_property_labels.return_value = mock_response

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_property_labels(dcids, out=True)

    assert result == expected_data
    mock_client.node.fetch_property_labels.assert_called_once_with(dcids, True)
    print("test_get_property_labels passed successfully")


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_property_values():
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    dcids = ["country/MDG"]
    properties = 'affectedPlace'
    constraints = None
    out = False
    expected_data = {
        'country/MDG': [
            'earthquake/us10007snb',
            'earthquake/us200040me',
        ]
    }

    mock_response = MagicMock()
    mock_response.data = expected_data
    mock_client.node.fetch_property_values.return_value = mock_response

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_property_values(
        dcids, properties, constraints, out
    )

    assert result == expected_data
    mock_client.node.fetch_property_values.assert_called_once_with(
        dcids, properties, constraints, out
    )
    print("test_get_property_values passed successfully")


@patch.dict(os.environ, {"DATACOMMONS_API_KEY": "test_api_key"})
def test_get_places_in():
    mock_client = MagicMock()
    mock_datacommons_client.DataCommonsClient.return_value = mock_client

    from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

    place_dcids = ["geoId/15", "geoId/02"]
    children_type = "CongressionalDistrict"
    expected_result = {
        'geoId/15': ['geoId/1501', 'geoId/1502'],
        'geoId/02': ['geoId/0200'],
    }

    mock_client.node.fetch_place_children.return_value = expected_result

    dc_toolkit = DataCommonsToolkit()
    result = dc_toolkit.get_places_in(place_dcids, children_type)

    assert result == expected_result
    mock_client.node.fetch_place_children.assert_called_once_with(
        place_dcids, children_type
    )
    print("test_get_places_in passed successfully")


if __name__ == '__main__':
    test_get_triples_outgoing()
    test_get_triples_incoming()
    test_get_stat()
    test_get_property_labels()
    test_get_property_values()
    test_get_places_in()
    print("All tests completed successfully!")
