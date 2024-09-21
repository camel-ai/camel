import datacommons
import datacommons_pandas as dc
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import json
import re
from typing import Union, List, Dict, Optional, Any

#from camel.toolkits import OpenAIFunction
#from camel.toolkits.base import BaseToolkit,class TwitterToolkit(BaseToolkit):

class DataCommonsToolkit:
    """A class representing a toolkit for Data Commons.

    This class provides methods for get statistics series, get location info, get time series and visualize data.

    All the data are grabbed from the knowledge graph of Data Commons. Refer to https://datacommons.org/browser/ for more details.

    We could decide to output the raw data or the processed data.
    """

    @staticmethod
    def validate_sparql_query(query):
        """
        Perform basic validation on a SPARQL query string.
        """
        print("Validating the query:", query)
        if not re.match(r'^\s*SELECT', query, re.IGNORECASE):
            print("Query must start with SELECT")
            raise InvalidQueryError("Query must start with SELECT")
    
        if 'WHERE' not in query.upper():
            print("Query must contain a WHERE clause")
            raise InvalidQueryError("Query must contain a WHERE clause")
        
        if query.count('{') != query.count('}'):
            print("Unbalanced braces in query")
            raise InvalidQueryError("Unbalanced braces in query")

    @staticmethod
    def query_data_commons(query_string, select_function=None):
        """Query the Data Commons knowledge graph using SPARQL.

        Args:
        query_string (str): A SPARQL query string.
        select_function (callable, optional): A function to select rows to be returned.
            It should take a dict as input and return a boolean.

        Returns:
        list: A list of dictionaries, each representing a node matching the query conditions.

        Note:
        - Only supports a limited subset of SPARQL functionality (ORDER BY, DISTINCT, LIMIT).
        - Each variable in the query should have a 'typeOf' condition.
        - The Python SPARQL library currently only supports the V1 version of the API.

        Reference:
        https://docs.datacommons.org/api/python/query.html
        """

        try:
            DataCommonsToolkit.validate_sparql_query(query_string)
            print("Trying to execute the query:", query_string)
            results = datacommons.query(query_string)

            if not results:
                print("Query returned empty results")
                return []
            
            processed_results = [
                {key: value for key, value in row.items()}
                for row in results
            ]
            
            if select_function:
                processed_results = [row for row in processed_results if select_function(row)]
            
            return processed_results

        except Exception as e:
            print(f"An error occurred while querying Data Commons: {str(e)}")
            return []
        
    @staticmethod
    def get_triples(dcids: Union[str, List[str]], limit: int = 500) -> Dict[str, List[tuple]]:
        """
        Retrieve triples associated with nodes.

        Args:
        dcids (Union[str, List[str]]): A single DCID or a list of DCIDs to query.
        limit (int, optional): The maximum number of triples per combination of property and type. 
                               Default is 500.

        Returns:
        Dict[str, List[tuple]]: A dictionary where keys are DCIDs and values are lists of associated triples.

        Note:
        - The function will raise a ValueError if any of the required arguments are missing.
        - The function will raise a TypeError if the dcids are not a string or a list of strings.
        - The function will raise a ValueError if the limit is not between 1 and 500.
        - The function will raise a KeyError if one or more of the provided DCIDs do not exist in the Data Commons knowledge graph.
        - The function will raise an Exception if an unexpected error occurs.

        Reference:
        https://docs.datacommons.org/api/python/triple.html
        """
        try:
            # Check if dcids is of correct type
            if not isinstance(dcids, (str, list)):
                raise TypeError("dcids must be a string or a list of strings")
            
            # Check if limit is within valid range
            if not 1 <= limit <= 500:
                raise ValueError("limit must be between 1 and 500")

            # Should we throw an error if the output is empty?
            return datacommons.get_triples(dcids, limit)

        except TypeError as e:
            print(f"TypeError occurred: {str(e)}")
            print("Please ensure you're passing the correct type for dcids (string or list of strings).")
            return {}

        except ValueError as e:
            print(f"ValueError occurred: {str(e)}")
            print("Please ensure the limit is between 1 and 500.")
            return {}

        except KeyError as e:
            print(f"KeyError occurred: {str(e)}")
            print("One or more of the provided DCIDs do not exist in the Data Commons knowledge graph.")
            return {}

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return {}
        
    @staticmethod
    def get_stat_series(
        place: str,
        stat_var: str,
        measurement_method: Optional[str] = None,
        observation_period: Optional[str] = None,
        unit: Optional[str] = None,
        scaling_factor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve statistical time series for a place.

        Args:
        place: The dcid of the Place to query for.
        stat_var: The dcid of the StatisticalVariable.
        In addition to these required properties, this endpoint also allows for other, optional arguments.
        measurement_method: The technique used for measuring a statistical variable.
        observation_period: The time period over which an observation is made.
        scaling_factor: Property of statistical variables indicating factor by which a measurement is multiplied to fit a certain format.
        unit: The unit of measurement.

        Returns:
        Dict[str, Any]: A dictionary containing the statistical time series data.

        Note:
        - The function will raise a ValueError if any of the required arguments are missing.

        Reference:
        https://docs.datacommons.org/api/python/stat_series.html
        """
        try:
            
            result = dc.get_stat_series(
                place, stat_var, measurement_method, observation_period, unit, scaling_factor
            )
            
            if not result:
                print(f"No data found for place '{place}' and statistical variable '{stat_var}'.")
                return {}
            
            return result
        except Exception as e:
            print(f"An error occurred while querying Data Commons: {str(e)}")
            return {}
    
    @staticmethod
    def get_property_labels(dcids, out=True):
        """
        Retrieves and analyzes property labels for given DCIDs.
        
        Args:
        dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
        out (bool): Direction of properties to retrieve. Defaults to True.
        
        Returns:
        dict: Analysis results for each DCID.

        Reference:
        https://docs.datacommons.org/api/python/property_label.html
        """
        try:
            if not dcids:
                raise ValueError("Missing required argument: 'dcids'")
            
            result = dc.get_property_labels(dcids, out)
            if not result:
                print(f"No data found for dcids '{dcids}'.")
                return {}
            return result
        
        except Exception as e:
            print(f"An error occurred while analyzing property labels: {str(e)}")
            return {}
        
    @staticmethod
    def get_property_values(dcids, prop, out=True, value_type=None, limit=datacommons.utils._MAX_LIMIT):
        """
        Retrieves and analyzes property values for given DCIDs.
         
        Args:
        dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
        prop (str): The property to analyze.

        Optional arguments:
        value_type: The type of the property value to filter by. Defaults to NONE. Only applicable if the value refers to a node.
        out: The label’s direction. Defaults to True (only returning response nodes directed towards the requested node). If set to False, will only return response nodes directed away from the request node.
        limit: (≤ 500) Maximum number of values returned per node. Defaults to datacommons.utils._MAX_LIMIT.    

        Returns:
        dict: Analysis results for each DCID.

        Reference:
        https://docs.datacommons.org/api/python/property_value.html
        """
        try:
            result = dc.get_property_values(dcids, prop, out, value_type, limit)
            if not result:
                print(f"No data found for dcids '{dcids}'.")
                return {}
            return result
        
        except Exception as e:
            print(f"An error occurred while analyzing property values: {str(e)}")
            return {}
    
    @staticmethod
    def get_places_in(dcids, place_type):
        """
        Retrieves places within a given place type.
        
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
            if not result:
                print(f"No data found for dcids '{dcids}'.")
                return {}
            return result
        
        except Exception as e:
            print(f"An error occurred while retrieving places in a given place type: {str(e)}")
            return {}
        


    

# Example usage
if __name__ == "__main__":
    # Test get_places_in function
    print("Testing get_places_in function...")
    result = DataCommonsToolkit.get_places_in(
        ["geoId/1021"]
    )
    
    print(json.dumps(result, indent=2))