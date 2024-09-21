# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any, Dict, List, Optional, Union
import datacommons
import datacommons_pandas as dc
from typing import Union, List, Dict, Optional, Any
import datacommons
import datacommons_pandas as dc


class DataCommonsToolkit:
    r"""A class representing a toolkit for Data Commons.

    This class provides methods for querying and retrieving data from the
    Data Commons knowledge graph. It includes functionality for:
    - Executing SPARQL queries
    - Retrieving triples associated with nodes
    - Fetching statistical time series data
    - Analyzing property labels and values
    - Retrieving places within a given place type
    - Obtaining statistical values for specific variables and locations

    All the data are grabbed from the knowledge graph of Data Commons.
    Refer to https://datacommons.org/browser/ for more details.
    """

    @staticmethod
    def query_data_commons(query_string, select_function=None):
        r"""Query the Data Commons knowledge graph using SPARQL.

        Args:
        query_string (str): A SPARQL query string.
        select_function (callable, optional): A function to select rows to be
            returned. It should take a dict as input and return a boolean.

        Returns:
        list: A list of dictionaries, each representing a node matching the
        query conditions.

        Note:
        - Only supports a limited subset of SPARQL functionality (ORDER BY,
          DISTINCT, LIMIT).
        - Each variable in the query should have a 'typeOf' condition.
        - The Python SPARQL library currently only supports the V1 version
          of the API.

        Reference:
        https://docs.datacommons.org/api/python/query.html
        """

        try:
            results = datacommons.query(query_string)

            if not results:
                print("Query returned empty results")
                return []

            processed_results = [
                {key: value for key, value in row.items()} for row in results
            ]

            if select_function:
                processed_results = [
                    row for row in processed_results if select_function(row)
                ]

            return processed_results

        except Exception as e:
            print(f"An error occurred while querying Data Commons: {e!s}")
            return []

    @staticmethod
    def get_triples(
        dcids: Union[str, List[str]], limit: int = 500
    ) -> Dict[str, List[tuple]]:
        r"""Retrieve triples associated with nodes.

        Args:
        dcids (Union[str, List[str]]): A single DCID or a list of DCIDs to
                                       query.
        limit (int, optional): The maximum number of triples per combination
                               of property and type. Default is 500.

        Returns:
        Dict[str, List[tuple]]: A dictionary where keys are DCIDs and values
                                are lists of associated triples.

        Note:
        - The function will raise a ValueError if any of the required
          arguments are missing.
        - The function will raise a TypeError if the dcids are not a string
          or a list of strings.
        - The function will raise a ValueError if the limit is not between
          1 and 500.
        - The function will raise a KeyError if one or more of the provided
          DCIDs do not exist in the Data Commons knowledge graph.
        - The function will raise an Exception if an unexpected error occurs.

        Reference:
        https://docs.datacommons.org/api/python/triple.html
        """
        try:
            result = datacommons.get_triples(dcids, limit)
            if len(result) == 0:
                print(
                    f"No data found for dcids '{dcids}'. "
                    "(The result is an empty dictionary.)"
                )
                return {}
            return result

        except TypeError as e:
            print(f"TypeError occurred: {e!s}")
            print(
                "Please ensure you're passing the correct type for dcids "
                "(string or list of strings)."
            )
            return {}

        except ValueError as e:
            print(f"ValueError occurred: {e!s}")
            print("Please ensure the limit is between 1 and 500.")
            return {}

        except KeyError as e:
            print(f"KeyError occurred: {e!s}")
            print(
                "One or more of the provided DCIDs do not exist in the "
                "Data Commons knowledge graph."
            )
            return {}

        except Exception as e:
            print(f"An unexpected error occurred: {e!s}")
            return {}

    @staticmethod
    def get_stat_series(
        place: str,
        stat_var: str,
        measurement_method: Optional[str] = None,
        observation_period: Optional[str] = None,
        unit: Optional[str] = None,
        scaling_factor: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Retrieve statistical time series for a place.

        Args:
        place: The dcid of the Place to query for.
        stat_var: The dcid of the StatisticalVariable.
        In addition to these required properties, this endpoint also allows
        for other, optional arguments.
        measurement_method: The technique used for measuring a statistical
                            variable.
        observation_period: The time period over which an observation is made.
        scaling_factor: Property of statistical variables indicating factor by
                        which a measurement is multiplied to fit a certain
                        format.
        unit: The unit of measurement.

        Returns:
        Dict[str, Any]: A dictionary containing the statistical time series
                        data.

        Note:
        - The function will raise a ValueError if any of the required
          arguments are missing.

        Reference:
        https://docs.datacommons.org/api/python/stat_series.html
        """
        try:
            result = dc.get_stat_series(
                place,
                stat_var,
                measurement_method,
                observation_period,
                unit,
                scaling_factor,
            )

            if len(result) == 0:
                print(
                    f"No data found for place '{place}' and statistical "
                    f"variable '{stat_var}'."
                )
                return {}
            return result
        except Exception as e:
            print(f"An error occurred while querying Data Commons: {e!s}")
            return {}

    @staticmethod
    def get_property_labels(dcids, out=True):
        r"""Retrieves and analyzes property labels for given DCIDs.

        Args:
        dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
        out (bool): Direction of properties to retrieve. Defaults to True.

        Returns:
        dict: Analysis results for each DCID.

        Reference:
        https://docs.datacommons.org/api/python/property_label.html
        """
        try:
            result = dc.get_property_labels(dcids, out)
            if len(result) == 0:
                print(f"No data found for dcids '{dcids}'.")
                return {}
            return result

        except Exception as e:
            print(f"An error occurred while analyzing property labels: {e!s}")
            return {}

    @staticmethod
    def get_property_values(
        dcids,
        prop,
        out=True,
        value_type=None,
        limit=datacommons.utils._MAX_LIMIT,
    ):
        r"""Retrieves and analyzes property values for given DCIDs.

        Args:
        dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
        prop (str): The property to analyze.

        Optional arguments:
        value_type: The type of the property value to filter by. Defaults to
                    NONE. Only applicable if the value refers to a node.
        out: The label's direction. Defaults to True (only returning response
             nodes directed towards the requested node). If set to False,
             will only return response nodes directed away from the request
             node.
        limit: (≤ 500) Maximum number of values returned per node. Defaults
               to datacommons.utils._MAX_LIMIT.

        Returns:
        dict: Analysis results for each DCID.

        Reference:
        https://docs.datacommons.org/api/python/property_value.html
        """
        try:
            result = dc.get_property_values(
                dcids, prop, out, value_type, limit
            )
            if len(result) == 0:
                print(
                    f"No data found for dcids '{dcids}' and property '{prop}'."
                )
                return {}
            return result

        except Exception as e:
            print(f"An error occurred while analyzing property values: {e!s}")
            return {}

    @staticmethod
    def get_places_in(dcids, place_type):
        r"""Retrieves places within a given place type.

        Args:
        dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
        place_type (str): The type of the place to filter by.

        Returns:
        dict: Analysis results for each DCID.

        Reference:
        https://docs.datacommons.org/api/python/place_in.html
        """
        try:
            result = dc.get_places_in(dcids, place_type)
            if len(result) == 0:
                print(
                    f"No data found for dcids '{dcids}' and place type "
                    f"'{place_type}'."
                )
                return {}
            return result

        except Exception as e:
            print(
                "An error occurred while retrieving places in a given place "
                f"type: {e!s}"
            )
            return {}

    @staticmethod
    def get_stat_value(
        place,
        stat_var,
        date=None,
        measurement_method=None,
        observation_period=None,
        unit=None,
        scaling_factor=None,
    ):
        r"""Retrieves the value of a statistical variable for a given place
        and date.

        Args:
        place: The DCID of the Place to query for.
        stat_var: The DCID of the StatisticalVariable.
        You can find a list of StatisticalVariables with human-readable names
        here.

        Optional arguments:
        date: The preferred date of observation in ISO 8601 format. If not
              specified, returns the latest observation.
        measurement_method: The DCID of the preferred measurementMethod value.
        observation_period: The preferred observationPeriod value.
        unit: The DCID of the preferred unit value.
        scaling_factor: The preferred scalingFactor value.

        Returns:
        float: The value of the statistical variable for the given place and
               date.

        Reference:
        https://docs.datacommons.org/api/python/stat_value.html
        """
        try:
            result = dc.get_stat_value(
                place,
                stat_var,
                date,
                measurement_method,
                observation_period,
                unit,
                scaling_factor,
            )
            if not result:
                print(
                    f"No data found for place '{place}' and statistical "
                    f"variable '{stat_var}'."
                )
                return None
            return result

        except Exception as e:
            print(
                "An error occurred while retrieving the value of a "
                f"statistical variable: {e!s}"
            )
            return None

    @staticmethod
    def get_stat_all(places, stat_vars):
        r"""Retrieves the value of a statistical variable for a given place
        and date.

        Args:
        places: The DCID IDs of the Place objects to query for. (Here DCID
                stands for Data Commons ID, the unique identifier assigned to
                all entities in Data Commons.)
        stat_vars: The dcids of the StatisticalVariables at
                   https://datacommons.org/browser/StatisticalVariable

        Returns:
        A dictionary with the DCID of the place as the key and a list of
        tuples as the value. Each tuple contains the DCID of the statistical
        variable, the date, the measurement method, the observation period,
        the unit, and the scaling factor.

        Reference:
        https://docs.datacommons.org/api/python/stat_all.html
        """
        try:
            result = dc.get_stat_all(places, stat_vars)
            if len(result) == 0:
                print(
                    f"No data found for places '{places}' and statistical "
                    f"variables '{stat_vars}'."
                )
                return {}
            return result

        except Exception as e:
            print(
                "An error occurred while retrieving the value of a "
                f"statistical variable: {e!s}"
            )
            return {}
