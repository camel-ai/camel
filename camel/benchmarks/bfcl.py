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

import ast
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

import requests

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import (
    RoleType,
)

logger = get_logger(__name__)

# Version prefix for BFCL dataset files
VERSION_PREFIX = "BFCL_v3"

# Test categories mapping
TEST_CATEGORIES = {
    "simple": f"{VERSION_PREFIX}_simple.json",
    "multiple": f"{VERSION_PREFIX}_multiple.json",
    "parallel": f"{VERSION_PREFIX}_parallel.json",
    "parallel_multiple": f"{VERSION_PREFIX}_parallel_multiple.json",
    "irrelevance": f"{VERSION_PREFIX}_irrelevance.json",
    "java": f"{VERSION_PREFIX}_java.json",
    "javascript": f"{VERSION_PREFIX}_javascript.json",
    "rest": f"{VERSION_PREFIX}_rest.json",
}


class BFCLSample:
    r"""Sample for BFCL benchmark.

    Args:
        question (str): User question/prompt.
        functions (str): JSON string of function definitions.
        possible_answer (Optional[Union[List, Dict, str]]): Possible correct
            function call formats. (default: :obj:`None`)
        category (str): Category of the function call. (default: :obj:`""`)
        id (Optional[str]): Sample ID. (default: :obj:`None`)
    """

    def __init__(
        self,
        question: str,
        functions: str,
        possible_answer: Optional[Union[List, Dict, str]] = None,
        category: str = "",
        id: Optional[str] = None,
    ):
        self.question = question
        self.functions = functions
        self.possible_answer = possible_answer
        self.category = category
        self.id = id


class FunctionCallParser:
    r"""Parser for function calls in model responses.

    This class provides methods to extract and evaluate function calls
    from model-generated text responses.
    """

    @staticmethod
    def _try_parse_json(json_str: str) -> Optional[Dict]:
        r"""Attempt to parse a JSON string.

        Args:
            json_str (str): The JSON string to parse.

        Returns:
            Optional[Dict]: Parsed JSON object or None if parsing fails.
        """
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    @staticmethod
    def _extract_from_markdown_codeblock(text: str) -> Optional[Dict]:
        r"""Extract JSON from markdown code blocks.

        Args:
            text (str): The text containing markdown code blocks.

        Returns:
            Optional[Dict]: Extracted JSON object or None if not found.
        """
        json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        match = re.search(json_pattern, text)
        if not match:
            return None

        # Try to parse the entire matched content
        result = FunctionCallParser._try_parse_json(match.group(1))
        if result:
            return result

        # If parsing fails, try to find a JSON object within
        curly_pattern = r'{[\s\S]*?}'
        curly_match = re.search(curly_pattern, match.group(1))
        if curly_match:
            return FunctionCallParser._try_parse_json(curly_match.group(0))

        return None

    @staticmethod
    def _extract_json_object_with_braces(text: str) -> Optional[Dict]:
        r"""Extract JSON object surrounded by curly braces.

        Args:
            text (str): The text to search for JSON objects.

        Returns:
            Optional[Dict]: Extracted JSON object or None if not found.
        """
        curly_pattern = r'{[\s\S]*?}'
        match = re.search(curly_pattern, text)
        if match:
            return FunctionCallParser._try_parse_json(match.group(0))
        return None

    @staticmethod
    def extract_json_from_string(text: str) -> Optional[Dict]:
        r"""Attempt to extract a JSON object from text string.

        Args:
            text (str): The text to parse for JSON objects.

        Returns:
            Optional[Dict]: Extracted JSON object or None if not found.
        """
        # Try to extract JSON from markdown code blocks
        result = FunctionCallParser._extract_from_markdown_codeblock(text)
        if result:
            return result

        # Try to parse the entire text as JSON
        result = FunctionCallParser._try_parse_json(text)
        if result:
            return result

        # Try to find JSON object surrounded by curly braces in the text
        result = FunctionCallParser._extract_json_object_with_braces(text)
        if result:
            return result

        logger.warning("Failed to parse JSON object from text: " f"{text}")
        return None

    @staticmethod
    def parse_function_call(
        response_text: str,
    ) -> Tuple[Optional[str], Optional[Dict]]:
        r"""Parse a function call from model response text.

        Args:
            response_text (str): The model's response text.

        Returns:
            Tuple[Optional[str], Optional[Dict]]: (function_name, parameters)
                or (None, None) if no function call is found.
        """
        # Try to extract JSON-formatted function call
        json_obj = FunctionCallParser.extract_json_from_string(response_text)

        if json_obj and isinstance(json_obj, dict):
            # Check for function_call format (OpenAI format)
            if 'function_call' in json_obj and isinstance(
                json_obj['function_call'], dict
            ):
                function_call = json_obj['function_call']
                if 'name' in function_call:
                    function_name = function_call['name']

                    # Process parameters, which may be a string or dict
                    parameters = function_call.get(
                        'parameters', function_call.get('arguments', {})
                    )
                    if isinstance(parameters, str):
                        try:
                            parameters = json.loads(parameters)
                        except Exception:
                            logger.warning(
                                "Failed to parse parameters from "
                                "function call: "
                                f"{parameters}"
                            )
                            parameters = {}
                    return function_name, parameters

            # Try to extract general format function call
            if 'name' in json_obj and 'parameters' in json_obj:
                function_name = json_obj['name']
                parameters = json_obj['parameters']
                return function_name, parameters

            # Try to extract single function call (not nested under parameters)
            if 'name' in json_obj and isinstance(json_obj.get('name'), str):
                function_name = json_obj['name']
                # Exclude name and other non-parameter fields
                parameters = {
                    k: v
                    for k, v in json_obj.items()
                    if k not in ['name', 'description', 'type']
                }
                return function_name, parameters

        # Try to parse JavaScript category special format
        if "createJsObject" in response_text or "JavaScript" in response_text:
            js_pattern = (
                r'createJsObject\s*\(\s*properties\s*[=:]\s*'
                r'["\'](.*?)["\']\s*\)'
            )
            js_match = re.search(js_pattern, response_text, re.DOTALL)
            if js_match:
                properties = js_match.group(1)
                return "createJsObject", {"properties": properties}

        # Try to parse Java category special format
        if "createHashMap" in response_text or "Java" in response_text:
            java_pattern = (
                r'createHashMap\s*\(\s*entries\s*[=:]\s*["\'](.*?)["\']\s*\)'
            )
            java_match = re.search(java_pattern, response_text, re.DOTALL)
            if java_match:
                entries = java_match.group(1)
                return "createHashMap", {"entries": entries}

        # Try to parse REST API call format
        if "requests.get" in response_text or "API" in response_text:
            rest_pattern = (
                r'requests\.get\s*\(\s*(?:url\s*[=:]\s*)?["\']([^"\']+)["\']'
                r'(?:\s*,\s*(?:params|data)\s*[=:]\s*(\{.*?\}))?\s*\)'
            )
            rest_match = re.search(rest_pattern, response_text, re.DOTALL)
            if rest_match:
                url = rest_match.group(1)
                parameters_str = (
                    rest_match.group(2) if rest_match.group(2) else "{}"
                )
                try:
                    # Try to parse parameter string as dictionary
                    parameters = ast.literal_eval(parameters_str)
                except Exception:
                    logger.warning(
                        "Failed to parse parameters from REST API call: "
                        f"{parameters_str}"
                    )
                    parameters = {}
                return "requests.get", {"url": url, "params": parameters}

        # Try to extract function name from text
        function_name_pattern = (
            r'[`"]([a-zA-Z0-9_.]+)[`"](?:\s+function|\s*\()'
        )
        function_match = re.search(function_name_pattern, response_text)

        if function_match:
            function_name = function_match.group(1)
            # Try to extract parameters
            parameters = {}
            param_pattern = r'[`"]?([a-zA-Z0-9_]+)[`"]?\s*[=:]\s*([^,\s]+)'
            param_matches = re.findall(param_pattern, response_text)

            for param_name, param_value in param_matches:
                # Try to convert parameter value to appropriate type
                try:
                    # Try as number
                    if param_value.isdigit():
                        parameters[param_name] = int(param_value)
                    elif re.match(r'^-?\d+\.\d+$', param_value):
                        parameters[param_name] = float(param_value)
                    # Try as quoted string
                    elif (
                        param_value.startswith('"')
                        and param_value.endswith('"')
                    ) or (
                        param_value.startswith("'")
                        and param_value.endswith("'")
                    ):
                        parameters[param_name] = param_value[1:-1]
                    else:
                        parameters[param_name] = param_value
                except Exception:
                    parameters[param_name] = param_value

            return function_name, parameters

        # Fall back to regex-based parsing for simple function calls
        try:
            # Clean up the input
            clean_call = response_text.strip()

            # Remove code blocks if present
            if clean_call.startswith("```") and clean_call.endswith("```"):
                lines = clean_call.split('\n')
                if len(lines) > 2:
                    clean_call = '\n'.join(lines[1:-1])

            # Try to extract function call format: func_name(args)
            function_call_pattern = r'([a-zA-Z0-9_.]+)\s*\((.*?)\)'
            function_call_match = re.search(
                function_call_pattern, clean_call, re.DOTALL
            )
            if function_call_match:
                function_name = function_call_match.group(1)
                args_str = function_call_match.group(2)

                # Parse parameters
                parameters = {}
                # Look for param=value pairs
                param_pattern = (
                    r'([a-zA-Z0-9_]+)\s*=\s*("[^"]*"|\'[^\']*\'|\d+|\d+\.\d+|'
                    r'True|False|None)'
                )
                param_matches = re.findall(param_pattern, args_str)

                for param_name, param_value in param_matches:
                    # Convert parameter values to appropriate types
                    if param_value.startswith('"') or param_value.startswith(
                        "'"
                    ):
                        # Strip quotes
                        parameters[param_name] = param_value[1:-1]
                    elif param_value == "True":
                        parameters[param_name] = True
                    elif param_value == "False":
                        parameters[param_name] = False
                    elif param_value == "None":
                        parameters[param_name] = None
                    elif "." in param_value:
                        parameters[param_name] = float(param_value)
                    else:
                        parameters[param_name] = int(param_value)

                return function_name, parameters
        except Exception:
            logger.warning(
                "Failed to parse function call from text: " f"{response_text}"
            )

        return None, None

    @staticmethod
    def evaluate_function_call(response_text: str, ground_truth: Dict) -> bool:
        r"""Evaluate if a function call matches the expected ground truth.

        Args:
            response_text (str): The model's response text.
            ground_truth (Dict): The expected answer in the format
                {func_name: {param1: [value1], param2: [value2], ...}}.

        Returns:
            bool: True if the function call matches, False otherwise.
        """
        # Verify ground_truth is valid
        if not ground_truth or not isinstance(ground_truth, dict):
            logger.warning(f"Invalid ground_truth format: {ground_truth}")
            return False

        function_name, parameters = FunctionCallParser.parse_function_call(
            response_text
        )

        if not function_name:
            logger.debug("No function call detected")
            return False

        # Debug parsed results
        logger.debug(
            f"Parsed function: {function_name}, parameters: {parameters}"
        )

        # Check if function name is in ground truth
        if function_name not in ground_truth:
            # Try removing namespace prefix (e.g., math.factorial -> factorial)
            if '.' in function_name:
                simple_name = function_name.split('.')[-1]
                if simple_name in ground_truth:
                    function_name = simple_name
                    logger.debug(
                        f"Using simplified function name: {function_name}"
                    )
                else:
                    # Check for namespace matching cases
                    for gt_func in ground_truth.keys():
                        if (
                            '.' in gt_func
                            and gt_func.split('.')[-1] == simple_name
                        ):
                            function_name = gt_func
                            logger.debug(
                                f"Using matched function name: {function_name}"
                            )
                            break

            if function_name not in ground_truth:
                logger.debug(
                    f"Function name mismatch: found {function_name}, "
                    f"expected {list(ground_truth.keys())}"
                )
                return False

        # Get expected parameters
        expected_parameters = ground_truth[function_name]

        # Check if expected_parameters is valid
        if not isinstance(expected_parameters, dict):
            logger.warning(
                f"Invalid expected_params format: {expected_parameters}"
            )
            return False

        # If no parameters are required, just check function name match
        if not expected_parameters:
            logger.debug(
                f"Reference answer for function {function_name} has no "
                f"parameter requirements, only checking function name match"
            )
            return True

        # If parameters aren't provided in the response, fail
        if not parameters:
            logger.debug("Function call has no parameters")
            return False

        # Check all required parameters exist
        for param_name, expected_values in expected_parameters.items():
            # For optional parameters (value list includes empty string or
            # default value), can skip if parameter doesn't exist
            is_optional = False
            if isinstance(expected_values, list):
                is_optional = "" in expected_values or None in expected_values

            # Check for parameter name variants (parameters vs arguments)
            alt_param_name = None
            if param_name == "parameters" and "arguments" in parameters:
                alt_param_name = "arguments"
            elif param_name == "arguments" and "parameters" in parameters:
                alt_param_name = "parameters"

            if param_name not in parameters and alt_param_name:
                logger.debug(
                    f"Using alternative parameter name: {alt_param_name} "
                    f"instead of {param_name}"
                )
                param_name = alt_param_name

            if param_name not in parameters:
                if is_optional:
                    logger.debug(
                        f"Parameter {param_name} is optional, skipping check"
                    )
                    continue
                logger.debug(f"Missing required parameter: {param_name}")
                return False

            # Convert single value to list for unified processing
            if not isinstance(expected_values, list):
                expected_values = [expected_values]

            # Expand nested lists from value list
            expanded_values = []
            for val in expected_values:
                if isinstance(val, list):
                    expanded_values.extend(val)
                else:
                    expanded_values.append(val)
            expected_values = expanded_values

            # Check if parameter value matches any expected value
            param_value = parameters[param_name]
            value_matched = False

            for expected_value in expected_values:
                if expected_value == "" or expected_value is None:
                    # Optional parameter, any value is acceptable
                    value_matched = True
                    break

                # Try different types of comparison
                try:
                    # Number comparison (ignore type)
                    if (
                        isinstance(param_value, (int, float))
                        or isinstance(expected_value, (int, float))
                        or (
                            isinstance(param_value, str)
                            and param_value.replace('.', '', 1).isdigit()
                        )
                        or (
                            isinstance(expected_value, str)
                            and expected_value.replace('.', '', 1).isdigit()
                        )
                    ):
                        try:
                            if float(param_value) == float(expected_value):
                                value_matched = True
                                break
                        except (ValueError, TypeError):
                            logger.warning(
                                "Failed to convert parameter value to float: "
                                f"{param_value} or {expected_value} "
                                f"for parameter {param_name}"
                            )

                    # String comparison (case insensitive)
                    if isinstance(param_value, str) and isinstance(
                        expected_value, str
                    ):
                        if param_value.lower() == expected_value.lower():
                            value_matched = True
                            break

                        # Try handling quote issues
                        cleaned_param = param_value.strip('"\'')
                        cleaned_expected = expected_value.strip('"\'')
                        if cleaned_param.lower() == cleaned_expected.lower():
                            value_matched = True
                            break

                    # Default comparison
                    if param_value == expected_value:
                        value_matched = True
                        break
                except (ValueError, TypeError):
                    # If conversion fails, use strict equality
                    if param_value == expected_value:
                        value_matched = True
                        break

            if not value_matched:
                logger.debug(
                    f"Parameter value mismatch: {param_name}={param_value}, "
                    f"expected one of: {expected_values}"
                )
                return False

        # All checks passed
        logger.debug(f"Function call {function_name} validation passed!")
        return True


def get_model(
    model_platform: Optional[str] = None,
    model_type: Optional[str] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
):
    r"""Create a model instance based on configuration.

    Args:
        model_platform (Optional[str]): Model platform, e.g., openai,
            anthropic, etc. If None, will read from environment variable
            MODEL_PLATFORM. (default: :obj:`None`)
        model_type (Optional[str]): Model type, e.g., gpt-4, claude-3, etc.
            If None, will read from environment variable MODEL_TYPE.
            (default: :obj:`None`)
        api_key (Optional[str]): API key. If None, will read from environment
            variable API_KEY. (default: :obj:`None`)
        url (Optional[str]): API endpoint URL. If None, will read from
            environment variable BASE_URL. (default: :obj:`None`)

    Returns:
        BaseModelBackend: Model backend instance.
    """
    # Get configuration from environment variables or parameters
    model_platform = model_platform or os.environ.get(
        "MODEL_PLATFORM", "openai"
    )
    model_type = model_type or os.environ.get("MODEL_TYPE", "gpt-4o")
    api_key = api_key or os.environ.get("API_KEY", None)
    url = url or os.environ.get("BASE_URL", None)

    logger.info(f"Using model platform: {model_platform}")
    logger.info(f"Using model type: {model_type}")

    # Create model instance with ModelFactory
    assert model_platform is not None, "model_platform cannot be None"
    assert model_type is not None, "model_type cannot be None"
    model = ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
        api_key=api_key,
        url=url,
    )

    return model


def create_bfcl_agent(
    model_platform: Optional[str] = None,
    model_type: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    system_message: Optional[str] = None,
) -> Optional["ChatAgent"]:
    r"""Create an agent for BFCL benchmark.

    Args:
        model_platform (Optional[str]): Model platform, e.g., openai,
            anthropic, etc. If None, will read from environment variable
            MODEL_PLATFORM. (default: :obj:`None`)
        model_type (Optional[str]): Model type, e.g., gpt-4, claude-3, etc.
            If None, will read from environment variable MODEL_TYPE.
            (default: :obj:`None`)
        api_key (Optional[str]): API key. If None, will read from environment
            variable API_KEY. (default: :obj:`None`)
        base_url (Optional[str]): API endpoint URL. If None, will read from
            environment variable BASE_URL. (default: :obj:`None`)
        system_message (Optional[str]): System message for the agent.
            If None, a default system message for function calling is used.
            (default: :obj:`None`)

    Returns:
        Optional[ChatAgent]: Agent instance for BFCL benchmark,
            or None if creation fails.
    """
    # Create a default system message if not provided
    if system_message is None:
        system_message = (
            "You are an expert in function calling. "
            "If the user request is not related to any function, "
            "you should directly return a single string 'None' in "
            "natural language instead of JSON format."
            "You analyze user requests and call the appropriate "
            "functions with the correct parameters. "
            "Return the function call in JSON format with "
            "function_call property."
        )

    # Create system message
    system_message_obj = BaseMessage(
        role_name="System",
        role_type=RoleType.USER,
        meta_dict=None,
        content=system_message,
    )

    # Initialize the model
    try:
        model = get_model(
            model_platform=model_platform,
            model_type=model_type,
            api_key=api_key,
            url=base_url,
        )

        agent = ChatAgent(model=model, system_message=system_message_obj)
        logger.info(
            f"Created agent with model {model_type} on platform "
            f"{model_platform}"
        )
        return agent
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return None


def run_bfcl_benchmark(
    model_name: str,
    category: str = "simple",
    data_dir: str = "data/bfcl",
    save_to: str = "results/bfcl",
    subset: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_platform: str = "openai",
    force_download: bool = False,
):
    r"""Run the BFCL benchmark with specified model and category.

    Args:
        model_name (str): Name of the model to use.
        category (str): Category of function calls to evaluate.
            Options: "simple", "multiple", "parallel", "parallel_multiple",
            "irrelevance", "java", "javascript", "rest".
            (default: :obj:`"simple"`)
        data_dir (str): Directory to store dataset.
            (default: :obj:`"data/bfcl"`)
        save_to (str): Directory to save results.
            (default: :obj:`"results/bfcl"`)
        subset (Optional[int]): Number of samples to evaluate.
            (default: :obj:`None`)
        api_key (Optional[str]): API key for the model.
            (default: :obj:`None`)
        base_url (Optional[str]): Base URL for API requests.
            (default: :obj:`None`)
        model_platform (str): Platform of the model.
            (default: :obj:`"openai"`)
        force_download (bool): Whether to force download the dataset.
            (default: :obj:`False`)
    """
    # Create data and results directories if they don't exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(save_to, exist_ok=True)

    # Create timestamp for results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(
        save_to, f"bfcl_{model_name}_{category}_{timestamp}.json"
    )

    # Initialize and run the benchmark directly
    benchmark = BFCLBenchmark(data_dir=data_dir, save_to=results_file)

    # Create a default system message in case needed
    system_message = (
        "You are an expert in function calling. "
        "If the user request is not related to any function, you should "
        "directly return a single string 'None' in natural language instead "
        "of JSON format."
        "You analyze user requests and call the appropriate functions "
        "with the correct parameters. "
        "Return the function call in JSON format with function_call property."
    )

    # Set up the agent to be benchmarked
    agent = create_bfcl_agent(
        model_platform=model_platform,
        model_type=model_name,
        api_key=api_key,
        base_url=base_url,
        system_message=system_message,
    )

    if agent is None:
        logger.error(f"Failed to create agent for model {model_name}")
        return None

    benchmark.run(
        agent=agent,
        category=category,
        randomize=False,
        subset=subset,
        force_download=force_download,
    )

    # Log results
    results = benchmark.results
    total = len(results)
    correct = sum(1 for result in results if result["result"])
    accuracy = correct / total if total > 0 else 0
    logger.info(f"Model: {model_name}")
    logger.info(f"Category: {category}")
    logger.info(f"Accuracy: {accuracy:.4f} ({correct}/{total})")
    logger.info(f"Results saved to: {results_file}")

    return benchmark


class BFCLBenchmark(BaseBenchmark):
    r"""Berkeley Function Call Leaderboard (BFCL) benchmark adapted from
    Gorilla-LLM's BFCL.

    Args:
        data_dir (str): Path to data directory.
        save_to (str): Path to save results.
        processes (int): Number of processes to use. (default: :obj:`1`)
    """

    REPO_ID = "gorilla-llm/Berkeley-Function-Calling-Leaderboard"

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
    ):
        r"""Initialize the BFCL benchmark.

        Args:
            data_dir (str): The directory to save the data.
            save_to (str): The file to save the results.
            processes (int): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        super().__init__("bfcl", data_dir, save_to, processes)
        # Use cast to make _data typed as dict[str, list[dict[str, Any]]]
        # but store as List[BFCLSample] for internal use
        self._data: Any = []

    def download(self) -> "BFCLBenchmark":
        r"""Download the BFCL dataset from HuggingFace.

        Returns:
            BFCLBenchmark: The benchmark instance.
        """
        try:
            # First try using Hugging Face Hub
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=self.REPO_ID,
                repo_type="dataset",
                local_dir=self.data_dir,
                local_dir_use_symlinks=True,
            )
            logger.info(f"Downloaded dataset from {self.REPO_ID}")
        except ImportError:
            logger.warning(
                "huggingface_hub is not installed, falling back to "
                "GitHub download. You can install it using "
                "'pip install huggingface_hub'."
            )
            # Fallback to GitHub if huggingface_hub is not available
            for category in TEST_CATEGORIES.keys():
                self._download_category(category)
        except Exception as e:
            logger.warning(f"Failed to download from Hugging Face: {e}")
            logger.info("Trying to download from GitHub...")

            # Fallback to GitHub if Hugging Face fails
            for category in TEST_CATEGORIES.keys():
                self._download_category(category)

        return self

    def _download_category(self, category: str) -> bool:
        r"""Download a specific category dataset from GitHub.

        Args:
            category (str): Category to download.

        Returns:
            bool: Whether download was successful.
        """
        data_file = self.data_dir / f"{VERSION_PREFIX}_{category}.json"

        # Skip if file already exists
        if data_file.exists():
            logger.info(
                f"Dataset file {data_file} already exists, skipping download"
            )
            return True

        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

        # Download URL from GitHub
        url = f"https://raw.githubusercontent.com/gorilla-llm/berkeley-function-call-leaderboard/main/data/{category}.json"

        logger.info(f"Downloading {category} dataset from {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()

            # Write response to file
            with open(data_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            logger.info(
                f"Successfully downloaded {category} dataset to {data_file}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to download {category} dataset: {e}")
            return False

    def load(
        self,
        force_download: bool = False,
        **kwargs: Any,
    ) -> BaseBenchmark:
        r"""Load the BFCL dataset.

        Args:
            force_download (bool): Whether to force download the data.
                (default: :obj:`False`)
            **kwargs (Any): Additional keyword arguments.

        Returns:
            BaseBenchmark: The benchmark instance.
        """
        # get category parameter from kwargs
        category = kwargs.get("category", "simple")
        if isinstance(category, str):
            if category not in TEST_CATEGORIES:
                logger.warning(
                    f"Invalid category: {category}. "
                    f"Using default category: simple"
                )
                category = "simple"
        else:
            category = "simple"

        if force_download:
            logger.info("Force downloading data.")
            self.download()

        # Get the dataset file
        dataset_file = self.data_dir / f"{VERSION_PREFIX}_{category}.json"
        possible_answers_file = (
            self.data_dir
            / "possible_answer"
            / f"{VERSION_PREFIX}_{category}.json"
        )

        # If file doesn't exist, automatically download
        if not dataset_file.exists():
            logger.info(
                f"Dataset file {dataset_file} not found. Downloading..."
            )
            self.download()

            # Check again after download
            if not dataset_file.exists():
                raise FileNotFoundError(
                    f"The dataset file {dataset_file} does not exist even "
                    "after download. Please check your network connection or "
                    "download manually."
                )

        # Load possible answers if they exist in the separate file
        possible_answers_dict = {}
        if possible_answers_file.exists():
            logger.info(
                f"Loading reference answers from: {possible_answers_file}"
            )
            try:
                with open(possible_answers_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            answer_obj = json.loads(line)
                            if (
                                "id" in answer_obj
                                and "ground_truth" in answer_obj
                            ):
                                possible_answers_dict[answer_obj["id"]] = (
                                    answer_obj["ground_truth"]
                                )
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"Failed to parse reference answer line: {e}"
                            )
            except Exception as e:
                logger.warning(f"Error loading reference answers: {e}")

        # Load the dataset - read line by line to handle JSONL format
        self._data = []
        try:
            with open(dataset_file, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        item = json.loads(line)

                        # Extract question
                        question = item.get("question", "")

                        # Extract function definitions
                        functions = item.get(
                            "function", item.get("functions", [])
                        )

                        # Get sample ID
                        sample_id = item.get("id", f"{category}_{i}")

                        # Get reference answer for this sample - try different
                        # sources
                        ground_truth = None
                        if sample_id in possible_answers_dict:
                            # First check if we have the answer in the separate
                            # file
                            ground_truth = possible_answers_dict[sample_id]
                            logger.debug(
                                f"Found reference answer for {sample_id} "
                                "in separate file"
                            )
                        elif "ground_truth" in item:
                            ground_truth = item["ground_truth"]
                        elif "possible_answer" in item:
                            ground_truth = item["possible_answer"]

                        # If ground_truth is still None, use an empty dict to
                        # avoid errors
                        if ground_truth is None:
                            logger.warning(
                                f"No reference answer found for sample "
                                f"{sample_id}, using empty dict"
                            )
                            ground_truth = {}

                        # Create sample - we store ground_truth as is, not as
                        # JSON string
                        sample = BFCLSample(
                            question=question,
                            functions=json.dumps(functions),
                            possible_answer=ground_truth,
                            category=category,
                            id=sample_id,
                        )
                        self._data.append(sample)

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Skipping invalid JSON line {i+1}: {e}"
                        )
                    except Exception as e:
                        logger.warning(f"Error processing line {i+1}: {e}")
        except Exception as e:
            logger.error(f"Error loading data: {e}")

        # If no data was loaded, add a default example
        if not self._data:
            logger.info(
                "No data loaded. Creating a default sample for testing"
            )
            default_func = [
                {
                    "name": "calculate_triangle_area",
                    "description": "Calculate the area of a triangle",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base": {
                                "type": "number",
                                "description": "Length of the base",
                            },
                            "height": {
                                "type": "number",
                                "description": "Height of the triangle",
                            },
                            "unit": {
                                "type": "string",
                                "description": "Unit of measurement",
                            },
                        },
                        "required": ["base", "height"],
                    },
                }
            ]

            ground_truth = [
                {
                    "calculate_triangle_area": {
                        "base": [10],
                        "height": [5],
                        "unit": ["units", ""],
                    }
                }
            ]

            sample = BFCLSample(
                question=(
                    "Calculate the area of a triangle with a base of 10 "
                    "units and a height of 5 units."
                ),
                functions=json.dumps(default_func),
                possible_answer=ground_truth,  # Store as Python object
                category=category,
                id=f"{category}_default",
            )
            self._data.append(sample)
            logger.info("Added a default sample")

        logger.info(
            f"Loaded {len(self._data)} samples from {category} category."
        )
        return self

    def run(
        self,
        agent: "ChatAgent",
        on: Literal[
            "train", "valid", "test"
        ] = "test",  # add on parameter to match parent class
        randomize: bool = False,
        subset: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> BaseBenchmark:
        r"""Run the BFCL benchmark.

        Args:
            agent (ChatAgent): The chat agent to use.
            on (Literal["train", "valid", "test"]): The dataset split to use.
                (default: :obj:`"test"`)
            randomize (bool): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int]): Number of samples to evaluate.
                (default: :obj:`None`)
            *args (Any): Additional positional arguments.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            BaseBenchmark: The benchmark instance.
        """
        # process parameters from kwargs
        category = kwargs.get("category", "simple")
        force_download = kwargs.get("force_download", False)

        logger.info(f"Running BFCL benchmark on {category} category.")
        self.load(force_download=force_download, category=category)
        samples = self._data

        # Shuffle and subset if necessary
        if randomize:
            random.shuffle(samples)
        if subset:
            samples = samples[:subset]

        logger.info(f"Number of samples: {len(samples)}")

        # Initialize results storage
        self._results = []

        # Import tqdm for progress display
        try:
            from tqdm.auto import tqdm as tqdm_func

            samples_list = list(enumerate(samples))
            samples_iter: Any = tqdm_func(
                samples_list,
                total=len(samples),
                desc=f"Testing {category}",
                position=0,
                leave=True,
            )
        except ImportError:
            logger.warning(
                "tqdm not found, progress bar will not be displayed"
            )
            samples_iter = enumerate(samples)

        # Process samples
        for i, sample in samples_iter:
            logger.info(f"Processing sample {i+1}/{len(samples)}")

            # Prepare the user prompt
            user_prompt = (
                f"Question: {sample.question}\n\n"
                f"Here is a list of functions in JSON format that "
                f"you can invoke:\n{sample.functions}"
            )

            # Get agent response
            try:
                start_time = time.time()
                agent_response = agent.step(input_message=user_prompt)
                response_time = time.time() - start_time

                if not agent_response.msg:
                    logger.warning("Agent returned empty response")
                    agent_response_text = ""
                else:
                    agent_response_text = agent_response.msg.content

                # Add some debugging output
                logger.debug(f"Agent response: {agent_response_text[:200]}...")
            except Exception as e:
                logger.error(f"Error getting agent response: {e}")
                agent_response_text = ""
                response_time = 0

            # Evaluate the response
            try:
                is_result_correct = self._evaluate_response(
                    agent_response_text, sample, category
                )
            except Exception as e:
                logger.error(f"Error in evaluation: {e}")
                is_result_correct = False

            # Create a sample ID if not available
            sample_id = getattr(sample, 'id', f"{category}_{i}")

            # Store the result
            self._results.append(
                {
                    "id": sample_id,
                    "question": sample.question,
                    "functions": sample.functions,
                    "possible_answer": sample.possible_answer,
                    "category": category,
                    "agent_response": agent_response_text,
                    "result": is_result_correct,
                    "latency": response_time,
                }
            )

        # Calculate accuracy
        if self._results:
            accuracy = sum(r["result"] for r in self._results) / len(
                self._results
            )
            logger.info(f"BFCL {category} accuracy: {accuracy:.4f}")

            # Save results to file
            if self.save_to:
                try:
                    # Create directory if it doesn't exist
                    save_path = Path(self.save_to)
                    save_dir = save_path.parent
                    os.makedirs(save_dir, exist_ok=True)

                    # ensure the results are serializable
                    serializable_results = []
                    for result in self._results:
                        result_copy = result.copy()
                        # handle possible non-serializable objects
                        for key, value in list(result_copy.items()):
                            try:
                                # test if it can be serialized
                                json.dumps(value)
                            except (TypeError, OverflowError):
                                # for non-serializable objects, convert to
                                # string
                                if key == "possible_answer" and not isinstance(
                                    value, (str, type(None))
                                ):
                                    result_copy[key] = json.dumps(value)
                                else:
                                    result_copy[key] = str(value)
                        serializable_results.append(result_copy)

                    # Write results to file
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(
                            serializable_results,
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )
                    logger.info(f"Results saved to: {self.save_to}")

                    # We only log the results but don't print them here
                    # to avoid duplicate printing with the run_bfcl_benchmark
                    # function
                    correct = sum(1 for r in self._results if r["result"])
                    total = len(self._results)
                    model_name = "unknown"
                    try:
                        # Try to get model information from agent if possible
                        if agent and hasattr(agent, "model_name"):
                            model_name = agent.model_name
                        elif (
                            agent
                            and hasattr(agent, "model")
                            and hasattr(agent.model, "model_type")
                        ):
                            model_name = agent.model.model_type
                    except Exception as e:
                        logger.debug(f"Could not get model name: {e}")
                    logger.info(f"Model: {model_name}")
                    logger.info(f"Category: {category}")
                    logger.info(
                        f"Accuracy: {accuracy:.4f} ({correct}/{total})"
                    )
                except Exception as e:
                    logger.error(
                        f"Error saving results to {self.save_to}: {e}"
                    )
        else:
            logger.warning("No results to calculate accuracy")

        return self

    def _evaluate_response(
        self, response: str, sample: BFCLSample, category: str
    ) -> bool:
        r"""Evaluate the agent's response against ground truth.

        Args:
            response (str): Agent's response.
            sample (BFCLSample): BFCL sample.
            category (str): Category of function call.

        Returns:
            bool: Whether the response is correct.
        """
        if category == "irrelevance":
            # For irrelevance category, the correct answer is no function call
            # We consider any non-function-call response as correct
            function_name, _ = FunctionCallParser.parse_function_call(response)
            # If no function call was parsed, it's correct for irrelevance
            # category
            return function_name is None
        else:
            # For other categories, evaluate using ground truth
            try:
                # Get the possible answers
                possible_answers = sample.possible_answer

                # Handle empty possible_answer
                if not possible_answers:
                    logger.warning("Sample has no possible_answer defined")
                    return False

                # Debug the possible answers
                logger.debug(f"Reference answer: {possible_answers}")

                # If possible_answers is a list, need to check if any of
                # them match
                if isinstance(possible_answers, list):
                    for possible_answer in possible_answers:
                        if FunctionCallParser.evaluate_function_call(
                            response, possible_answer
                        ):
                            return True
                    return False
                # If possible_answers is a dict, just need to check if it
                # matches
                elif isinstance(possible_answers, dict):
                    return FunctionCallParser.evaluate_function_call(
                        response, possible_answers
                    )
                else:
                    logger.warning(
                        f"Unexpected format for possible_answers: "
                        f"{type(possible_answers)}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error evaluating response: {e}")
                import traceback

                logger.error(traceback.format_exc())
                return False
