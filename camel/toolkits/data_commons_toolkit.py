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
import logging
import os
from typing import Any, Dict, List, Optional, Union

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = logging.getLogger(__name__)


@MCPServer()
class DataCommonsToolkit(BaseToolkit):
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

    @api_keys_required(
        [
            (None, "DATACOMMONS_API_KEY"),
        ]
    )
    def __init__(self, timeout: Optional[float] = None):
        r"""Initialize the DataCommonsToolkit.

        Args:
            timeout (Optional[float], optional): Maximum time in seconds to
            wait for API calls to complete. If None, will wait indefinitely.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        from datacommons_client import DataCommonsClient

        datacommons_api_key = os.environ.get("DATACOMMONS_API_KEY")

        self.client = DataCommonsClient(datacommons_api_key)

    def get_triples_outgoing(
        self, dcids: Union[str, List[str]]
    ) -> Optional[Dict[str, List[tuple]]]:
        r"""Retrieve triples associated with nodes for outgoing relationships.

        Args:
            dcids (Union[str, List[str]]): A single DCID or a list of DCIDs
                to query.

        Returns:
            Optional[Dict[str, List[tuple]]]: A dictionary where keys are
                DCIDs and values are lists of associated triples if success,
                (default: :obj:`None`) otherwise.
        """

        try:
            result = self.client.node.fetch(dcids, expression="->*")
            return result.data

        except Exception as e:
            logger.error(f"An error occurred: {e!s}")
            return None

    def get_triples_incoming(
        self, dcids: Union[str, List[str]]
    ) -> Optional[Dict[str, List[tuple]]]:
        r"""Retrieve triples associated with nodes for incoming relationships.

        Args:
            dcids (Union[str, List[str]]): A single DCID or a list of DCIDs
                to query.

        Returns:
            Optional[Dict[str, List[tuple]]]: A dictionary where keys are
                DCIDs and values are lists of associated triples if success,
                (default: :obj:`None`) otherwise.
        """

        try:
            result = self.client.node.fetch(dcids, expression="<-*")
            return result.data

        except Exception as e:
            logger.error(f"An error occurred: {e!s}")
            return None

    def get_stat(
        self,
        date: str,
        entity_dcids: Union[str, List[str]],
        variable_dcids: Union[str, List[str]],
    ) -> Optional[Dict[str, Any]]:
        r"""Retrieve statistical time series for a place.

        Args:
            date (str): The date option for the observations.
            Use 'all' for all dates, 'latest' for the most recent data,
            or provide a date as a string (e.g., "2026")
            entity_dcids (Union[str, List[str]]): entity IDs to filter the data
            variable_dcids (Union[str, List[str]]):
            The variable(s) to fetch observations for.
            This can be a single variable ID or a list of IDs.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the statistical
                time series data if success, (default: :obj:`None`) otherwise.
        """

        try:
            result = self.client.observation.fetch_observations_by_entity_dcid(
                date, entity_dcids, variable_dcids
            )
            return result.byVariable
        except Exception as e:
            logger.error(
                f"An error occurred while querying Data Commons: {e!s}"
            )
            return None

    def get_property_labels(
        self, dcids: Union[str, List[str]], out: bool = True
    ) -> Optional[Dict[str, List[str]]]:
        r"""Retrieves and analyzes property labels for given DCIDs.

        Args:
            dcids (Union[str, List[str]]): A single DCID or a list of DCIDs
                to query.
            out (bool): Whether to fetch outgoing properties (default:
                :obj:`True`)

        Returns:
            Optional[Dict[str, List[str]]]: Analysis results for each DCID if
                success, (default: :obj:`None`) otherwise.
        """

        try:
            result = self.client.node.fetch_property_labels(dcids, out)
            return result.data
        except Exception as e:
            logger.error(
                f"An error occurred while analyzing property labels: {e!s}"
            )
            return None

    def get_property_values(
        self,
        dcids: Union[str, List[str]],
        properties: Union[str, List[str]],
        constraints: Optional[str] = None,
        out: Optional[bool] = True,
    ) -> Optional[Dict[str, Any]]:
        r"""Retrieves and analyzes property values for given DCIDs.

        Args:
            dcids (Union[str, List[str]]): A single DCID or a list of DCIDs
                to query.
            properties (str): The property to analyze.
            constraints (Optional[str]): Additional constraints for the query.
            Defaults to None.
            out (bool, optional): Whether to fetch outgoing properties.
            Defaults to True

        Returns:
            Optional[Dict[str, Any]]: Analysis results for each DCID if
                success, (default: :obj:`None`) otherwise.
        """

        try:
            result = self.client.node.fetch_property_values(
                dcids, properties, constraints, out
            )
            return result.data

        except Exception as e:
            logger.error(
                f"An error occurred while analyzing property values: {e!s}"
            )
            return None

    def get_places_in(
        self,
        place_dcids: Union[str, List[str]],
        children_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        r"""Retrieves places within a given place type.

        Args:
            dcids (list): A list of Data Commons IDs (DCIDs) to analyze.
            children_type : (Optional[str]):
            The type of the child entities to fetch.
            If None, fetches all child types.

        Returns:
            Optional[Dict[str, Any]]: Analysis results for each DCID if
                success, (default: :obj:`None`) otherwise.

        """

        try:
            result = self.client.node.fetch_place_children(
                place_dcids, children_type
            )
            return result

        except Exception as e:
            logger.error(
                "An error occurred while retrieving places in a given place "
                f"type: {e!s}"
            )
            return None

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.get_triples_incoming),
            FunctionTool(self.get_triples_outgoing),
            FunctionTool(self.get_stat),
            FunctionTool(self.get_property_labels),
            FunctionTool(self.get_property_values),
            FunctionTool(self.get_places_in),
        ]
