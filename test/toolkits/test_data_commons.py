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
from unittest.mock import patch

from camel.toolkits.data_commons import DataCommonsToolkit


def test_query_data_commons():
    dc_toolkit = DataCommonsToolkit()
    query = '''
    SELECT ?name ?dcid 
    WHERE {
        ?a typeOf Place .
        ?a name ?name .
        ?a dcid ("geoId/06" "geoId/21" "geoId/24") .
        ?a dcid ?dcid
    }
    '''
    expected_result = [
        {'?name': 'Kentucky', '?dcid': 'geoId/21'},
        {'?name': 'California', '?dcid': 'geoId/06'},
        {'?name': 'Maryland', '?dcid': 'geoId/24'},
    ]

    with patch('datacommons.query') as mock_query:
        mock_query.return_value = expected_result
        result = dc_toolkit.query_data_commons(query)
        assert result == expected_result
    print("test_query_data_commons passed successfully")


def test_get_triples():
    dc_toolkit = DataCommonsToolkit()
    dcids = ['dc/c3j78rpyssdmf', 'dc/7hfhd2ek8ppd2']
    expected_result = {
        'dc/c3j78rpyssdmf': [
            ('dc/c3j78rpyssdmf', 'provenance', 'dc/h2lkz1'),
            ('dc/zn6l0flenf3m6', 'biosampleOntology', 'dc/c3j78rpyssdmf'),
            ('dc/tkcknpfwxfrhf', 'biosampleOntology', 'dc/c3j78rpyssdmf'),
            ('dc/jdzbbfhgzghv1', 'biosampleOntology', 'dc/c3j78rpyssdmf'),
            ('dc/4f9w8lhcwggxc', 'biosampleOntology', 'dc/c3j78rpyssdmf'),
        ],
        'dc/7hfhd2ek8ppd2': [
            ('dc/4mjs95b1meh1h', 'biosampleOntology', 'dc/7hfhd2ek8ppd2'),
            ('dc/13xcyzcr819cb', 'biosampleOntology', 'dc/7hfhd2ek8ppd2'),
            ('dc/7hfhd2ek8ppd2', 'provenance', 'dc/h2lkz1'),
        ],
    }

    with patch('datacommons.get_triples') as mock_get_triples:
        mock_get_triples.return_value = expected_result
        result = dc_toolkit.get_triples(dcids)
        assert result == expected_result
        mock_get_triples.assert_called()
        assert (
            mock_get_triples.call_args[0][0] == dcids
        )  # Check that dcids were passed correctly
    print("test_get_triples passed successfully")


def test_get_property_labels():
    dc_toolkit = DataCommonsToolkit()
    dcids = ['dc/c3j78rpyssdmf', 'dc/7hfhd2ek8ppd2']
    expected_result = {
        'dc/c3j78rpyssdmf': ['biosampleOntology'],
        'dc/7hfhd2ek8ppd2': ['biosampleOntology'],
    }

    with patch(
        'datacommons_pandas.get_property_labels'
    ) as mock_get_property_labels:
        mock_get_property_labels.return_value = expected_result
        result = dc_toolkit.get_property_labels(dcids, out=True)
        print("Expected result:", expected_result)
        print("Actual result:", result)
        assert result == expected_result
        mock_get_property_labels.assert_called_once_with(dcids, out=True)
    print("test_get_property_labels passed successfully")


def test_get_property_values():
    dc_toolkit = DataCommonsToolkit()
    dcids = ["nces/360007702877", "nces/062961004587"]
    prop = 'address'
    expected_result = {
        'nces/360007702877': ['345 Chambers St, New York, New York'],
        'nces/062961004587': ['780 Arastradero Rd., Palo Alto, California'],
    }

    with patch('datacommons.get_property_values') as mock_get_property_values:
        mock_get_property_values.return_value = expected_result
        result = dc_toolkit.get_property_values(dcids, prop)
        assert result == expected_result
        mock_get_property_values.assert_called_once_with(dcids, prop)
    print("test_get_property_values passed successfully")


def test_get_places_in():
    dc_toolkit = DataCommonsToolkit()
    dcids = ["geoId/15", "geoId/02"]
    place_type = "CongressionalDistrict"
    expected_result = {
        'geoId/15': ['geoId/1501', 'geoId/1502'],
        'geoId/02': ['geoId/0200'],
    }

    with patch('datacommons.get_places_in') as mock_get_places_in:
        mock_get_places_in.return_value = expected_result
        result = dc_toolkit.get_places_in(dcids, place_type)
        assert result == expected_result
        mock_get_places_in.assert_called_once_with(dcids, place_type)
    print("test_get_places_in passed successfully")


def test_get_stat_value():
    dc_toolkit = DataCommonsToolkit()
    place = "geoId/12086"  # Miami-Dade County
    stat_var = "RetailDrugDistribution_DrugDistribution_Naloxone"
    unit = "Grams"
    expected_result = 118.79

    with patch('datacommons.get_stat_value') as mock_get_stat_value:
        mock_get_stat_value.return_value = expected_result
        result = dc_toolkit.get_stat_value(place, stat_var, unit=unit)
        assert result == expected_result
        mock_get_stat_value.assert_called_once_with(place, stat_var, unit=unit)
    print("test_get_stat_value passed successfully")


def test_get_stat_all():
    dc_toolkit = DataCommonsToolkit()
    places = ["geoId/27", "geoId/55"]
    stat_vars = ["Count_Person_EducationalAttainmentDoctorateDegree"]
    expected_result = {
        'geoId/27': {
            'Count_Person_EducationalAttainmentDoctorateDegree': {
                'sourceSeries': [
                    {
                        'val': {
                            '2016': 50039,
                            '2017': 52737,
                            '2018': 54303,
                            '2012': 40961,
                            '2013': 42511,
                            '2014': 44713,
                            '2015': 47323,
                        },
                        'measurementMethod': 'CensusACS5yrSurvey',
                        'importName': 'CensusACS5YearSurvey',
                        'provenanceDomain': 'census.gov',
                        'provenanceUrl': 'https://www.census.gov/',
                    }
                ]
            }
        },
        'geoId/55': {
            'Count_Person_EducationalAttainmentDoctorateDegree': {
                'sourceSeries': [
                    {
                        'val': {
                            '2017': 43737,
                            '2018': 46071,
                            '2012': 38052,
                            '2013': 38711,
                            '2014': 40133,
                            '2015': 41387,
                            '2016': 42590,
                        },
                        'measurementMethod': 'CensusACS5yrSurvey',
                        'importName': 'CensusACS5YearSurvey',
                        'provenanceDomain': 'census.gov',
                        'provenanceUrl': 'https://www.census.gov/',
                    }
                ]
            }
        },
    }

    with patch('datacommons.get_stat_all') as mock_get_stat_all:
        mock_get_stat_all.return_value = expected_result
        result = dc_toolkit.get_stat_all(places, stat_vars)
        assert result == expected_result
        mock_get_stat_all.assert_called_once_with(places, stat_vars)
    print("test_get_stat_all passed successfully")


if __name__ == '__main__':
    test_query_data_commons()
    test_get_triples()
    test_get_property_labels()
    test_get_property_values()
    test_get_places_in()
    test_get_stat_value()
    test_get_stat_all()
    print("All tests completed successfully!")
