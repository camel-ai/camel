# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Dict, List, Protocol, Any

class RetrieverProtocol(Protocol):
    r"""Protocol for the retriever class.
    Any retriever class implementing this protocol
    can be used in the benchmark class.
    """
    def retrieve(
        self,
        query: str,
        contents: List[str],
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Retrieve the relevant content for the query.
        
        Args:
            query (str): The query to retrieve the content for.
            contents (List[str]): The list of contents to search in.
            **kwargs (Dict[str, Any]): Additional keyword arguments.
            
        Returns:
            Dict[str, Any]: The relevant content for the query.
        """
        ...
        
    def reset(self, **kwargs) -> bool:
        r"""Reset the retriever.
        Some benchmarks may require resetting the retriever
        after each query.
        
        Args:
            **kwargs: Additional keyword arguments.
            
        Returns:
            bool: True if the reset was successful, False otherwise.
        """
        ...
