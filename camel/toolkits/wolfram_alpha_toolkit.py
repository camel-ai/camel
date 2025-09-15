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
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required, dependencies_required


@MCPServer()
class WolframAlphaToolkit(BaseToolkit):
    r"""A class representing a toolkit for WolframAlpha.

    Wolfram|Alpha is an answer engine developed by Wolfram Research.
    It is offered as an online service that answers factual queries
    by computing answers from externally sourced data.
    """

    @api_keys_required(
        [
            (None, "WOLFRAMALPHA_APP_ID"),
        ]
    )
    @dependencies_required("wolframalpha")
    def query_wolfram_alpha(self, query: str) -> str:
        r"""Queries Wolfram|Alpha and returns the result as a simple answer.

        Args:
            query (str): The query to send to Wolfram Alpha.

        Returns:
            str: The result from Wolfram Alpha as a simple answer.
        """
        import wolframalpha

        WOLFRAMALPHA_APP_ID = os.environ.get("WOLFRAMALPHA_APP_ID", "")

        try:
            client = wolframalpha.Client(WOLFRAMALPHA_APP_ID)
            res = client.query(query)

        except Exception as e:
            return f"Wolfram Alpha wasn't able to answer it. Error: {e}"

        parsed_result = self._parse_wolfram_result(res)
        return parsed_result["final_answer"]

    @api_keys_required(
        [
            (None, "WOLFRAMALPHA_APP_ID"),
        ]
    )
    @dependencies_required("wolframalpha")
    def query_wolfram_alpha_step_by_step(self, query: str) -> Dict[str, Any]:
        r"""Queries Wolfram|Alpha and returns detailed results with
        step-by-step solution.

        Args:
            query (str): The query to send to Wolfram Alpha.

        Returns:
            Dict[str, Any]: A dictionary with detailed information including
                step-by-step solution.
        """
        import wolframalpha

        WOLFRAMALPHA_APP_ID = os.environ.get("WOLFRAMALPHA_APP_ID", "")

        try:
            client = wolframalpha.Client(WOLFRAMALPHA_APP_ID)
            res = client.query(query)

        except Exception as e:
            return {
                "error": f"Wolfram Alpha wasn't able to answer it. Error: {e}"
            }

        parsed_result = self._parse_wolfram_result(res)
        step_info = self._get_wolframalpha_step_by_step_solution(
            WOLFRAMALPHA_APP_ID, query
        )
        parsed_result["steps"] = step_info
        return parsed_result

    @api_keys_required(
        [
            (None, "WOLFRAMALPHA_APP_ID"),
        ]
    )
    def query_wolfram_alpha_llm(self, query: str) -> str:
        r"""Sends a query to the Wolfram|Alpha API optimized for language
        model usage.

        Args:
            query (str): The query to send to Wolfram Alpha LLM.

        Returns:
            str: The result from Wolfram Alpha as a string.
        """

        WOLFRAMALPHA_APP_ID = os.environ.get("WOLFRAMALPHA_APP_ID", "")

        try:
            url = "https://www.wolframalpha.com/api/v1/llm-api"
            params = {
                "input": query,
                "appid": WOLFRAMALPHA_APP_ID,
                "format": "plaintext",
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.text

        except Exception as e:
            return f"Wolfram Alpha wasn't able to answer it. Error: {e}"

    def _parse_wolfram_result(self, result) -> Dict[str, Any]:
        r"""Parses a Wolfram Alpha API result into a structured dictionary
        format.

        Args:
            result: The API result returned from a Wolfram Alpha
                query, structured with multiple pods, each containing specific
                information related to the query.

        Returns:
            Dict[str, Any]: A structured dictionary with the original query
                and the final answer.
        """

        # Extract the original query
        query = result.get("@inputstring", "")

        # Initialize a dictionary to hold structured output
        output = {"query": query, "pod_info": [], "final_answer": None}

        # Loop through each pod to extract the details
        for pod in result.get("pod", []):
            # Handle the case where subpod might be a list
            subpod_data = pod.get("subpod", {})
            if isinstance(subpod_data, list):
                # If it's a list, get the first item for 'plaintext' and 'img'
                description, image_url = next(
                    (
                        (data["plaintext"], data["img"])
                        for data in subpod_data
                        if "plaintext" in data and "img" in data
                    ),
                    ("", ""),
                )
            else:
                # Otherwise, handle it as a dictionary
                description = subpod_data.get("plaintext", "")
                image_url = subpod_data.get("img", {}).get("@src", "")

            pod_info = {
                "title": pod.get("@title", ""),
                "description": description,
                "image_url": image_url,
            }

            # For Results pod, collect all plaintext values from subpods
            if pod.get("@title") == "Results":
                results_text = []
                if isinstance(subpod_data, list):
                    for subpod in subpod_data:
                        if subpod.get("plaintext"):
                            results_text.append(subpod["plaintext"])
                else:
                    if description:
                        results_text.append(description)
                pod_info["description"] = "\n".join(results_text)

            # Add to steps list
            output["pod_info"].append(pod_info)

            # Get final answer
            if pod.get("@primary", False):
                output["final_answer"] = description

        return output

    def _get_wolframalpha_step_by_step_solution(
        self, app_id: str, query: str
    ) -> dict:
        r"""Retrieve a step-by-step solution from the Wolfram Alpha API for a
        given query.

        Args:
            app_id (str): Your Wolfram Alpha API application ID.
            query (str): The mathematical or computational query to solve.

        Returns:
            dict: The step-by-step solution response text from the Wolfram
                Alpha API.
        """
        # Define the base URL
        url = "https://api.wolframalpha.com/v2/query"

        # Set up the query parameters
        params = {
            "appid": app_id,
            "input": query,
            "podstate": ["Result__Step-by-step solution", "Show all steps"],
            "format": "plaintext",
        }

        # Send the request
        response = requests.get(url, params=params)
        root = ET.fromstring(response.text)

        # Extracting step-by-step steps, including 'SBSStep' and 'SBSHintStep'
        steps = []
        # Find all subpods within the 'Results' pod
        for subpod in root.findall(".//pod[@title='Results']//subpod"):
            # Check if the subpod has the desired stepbystepcontenttype
            content_type = subpod.find("stepbystepcontenttype")
            if content_type is not None and content_type.text in [
                "SBSStep",
                "SBSHintStep",
            ]:
                plaintext = subpod.find("plaintext")
                if plaintext is not None and plaintext.text:
                    step_text = plaintext.text.strip()
                    cleaned_step = step_text.replace(
                        "Hint: |", ""
                    ).strip()  # Remove 'Hint: |' if present
                    steps.append(cleaned_step)

        # Structuring the steps into a dictionary
        structured_steps = {}
        for i, step in enumerate(steps, start=1):
            structured_steps[f"step{i}"] = step

        return structured_steps

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.query_wolfram_alpha),
            FunctionTool(self.query_wolfram_alpha_step_by_step),
            FunctionTool(self.query_wolfram_alpha_llm),
        ]
