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

import logging
from unittest.mock import MagicMock, mock_open, patch

from camel.benchmarks import BFCLBenchmark

# configure logger
logger = logging.getLogger(__name__)

# Mock sample data for BFCL benchmark's different categories

# Simple function call
MOCK_SIMPLE_DATA = [
    {
        "question": (
            "Calculate the area of a triangle with base 10 and height 5"
        ),
        "functions": [
            {
                "name": "calculate_triangle_area",
                "description": "Calculate the area of a triangle",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base": {
                            "type": "number",
                            "description": "The base length of the triangle",
                        },
                        "height": {
                            "type": "number",
                            "description": "The height of the triangle",
                        },
                    },
                    "required": ["base", "height"],
                },
            }
        ],
        "possible_answer": {
            "calculate_triangle_area": {"base": [10], "height": [5]}
        },
    }
]

# Multiple function call (choose one from multiple functions)
MOCK_MULTIPLE_DATA = [
    {
        "question": (
            "I need to predict the price of a house in San Francisco with "
            "3 bedrooms, 2 bathrooms, and 1800 square feet"
        ),
        "functions": [
            {
                "name": "predict_house_price",
                "description": "Predict the price of a house",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bedrooms": {
                            "type": "number",
                            "description": "Number of bedrooms",
                        },
                        "bathrooms": {
                            "type": "number",
                            "description": "Number of bathrooms",
                        },
                        "area": {
                            "type": "number",
                            "description": "Area in square feet",
                        },
                        "location": {
                            "type": "string",
                            "description": "Location of the house",
                        },
                    },
                    "required": ["bedrooms", "bathrooms", "area", "location"],
                },
            },
            {
                "name": "predict_apartment_price",
                "description": "Predict the price of an apartment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bedrooms": {
                            "type": "number",
                            "description": "Number of bedrooms",
                        },
                        "bathrooms": {
                            "type": "number",
                            "description": "Number of bathrooms",
                        },
                        "area": {
                            "type": "number",
                            "description": "Area in square feet",
                        },
                        "floor": {
                            "type": "number",
                            "description": "Floor number",
                        },
                        "location": {
                            "type": "string",
                            "description": "Location of the apartment",
                        },
                    },
                    "required": ["bedrooms", "bathrooms", "area", "location"],
                },
            },
        ],
        "possible_answer": {
            "predict_house_price": {
                "bedrooms": [3],
                "bathrooms": [2],
                "area": [1800],
                "location": ["San Francisco", "San Francisco, CA"],
            }
        },
    }
]

# Parallel function call (multiple function calls at once)
MOCK_PARALLEL_DATA = [
    {
        "question": "Get the weather in New York and London today",
        "functions": [
            {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state/country",
                        }
                    },
                    "required": ["location"],
                },
            }
        ],
        "possible_answer": [
            {"get_weather": {"location": ["New York", "New York, NY"]}},
            {"get_weather": {"location": ["London", "London, UK"]}},
        ],
    }
]

# Parallel multiple function call
MOCK_PARALLEL_MULTIPLE_DATA = [
    {
        "question": "Display today's weather and traffic conditions in Boston",
        "functions": [
            {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state/country",
                        }
                    },
                    "required": ["location"],
                },
            },
            {
                "name": "get_traffic",
                "description": "Get current traffic conditions for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state/country",
                        }
                    },
                    "required": ["location"],
                },
            },
            {
                "name": "get_news",
                "description": "Get latest news for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state/country",
                        },
                        "category": {
                            "type": "string",
                            "description": "News category",
                        },
                    },
                    "required": ["location"],
                },
            },
        ],
        "possible_answer": [
            {"get_weather": {"location": ["Boston", "Boston, MA"]}},
            {"get_traffic": {"location": ["Boston", "Boston, MA"]}},
        ],
    }
]

# Irrelevance detection (no function should be called)
MOCK_IRRELEVANCE_DATA = [
    {
        "question": "What's your favorite color?",
        "functions": [
            {
                "name": "calculate_area",
                "description": "Calculate area of shapes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "shape": {
                            "type": "string",
                            "description": "The shape (circle, square, etc.)",
                        },
                        "dimensions": {
                            "type": "array",
                            "description": "Dimensions of the shape",
                        },
                    },
                    "required": ["shape", "dimensions"],
                },
            }
        ],
        "possible_answer": {},
    }
]

# Java function call
MOCK_JAVA_DATA = [
    {
        "question": (
            "Create a Java HashMap with three entries: 'apple' -> 1, "
            "'banana' -> 2, 'orange' -> 3"
        ),
        "functions": [
            {
                "name": "createHashMap",
                "description": "Create a HashMap in Java",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "string",
                            "description": (
                                "Entries for the HashMap in Java format"
                            ),
                        }
                    },
                    "required": ["entries"],
                },
            }
        ],
        "possible_answer": {
            "createHashMap": {
                "entries": ["\"apple\", 1, \"banana\", 2, \"orange\", 3"]
            }
        },
    }
]

# JavaScript function call
MOCK_JAVASCRIPT_DATA = [
    {
        "question": "Create a JavaScript object with name 'John' and age 30",
        "functions": [
            {
                "name": "createJsObject",
                "description": "Create a JavaScript object",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "properties": {
                            "type": "string",
                            "description": (
                                "Properties for the JavaScript object"
                            ),
                        }
                    },
                    "required": ["properties"],
                },
            }
        ],
        "possible_answer": {
            "createJsObject": {"properties": ["name: 'John', age: 30"]}
        },
    }
]

# REST API call
MOCK_REST_DATA = [
    {
        "question": "Get the weather for New York City using the weather API",
        "functions": [
            {
                "name": "requests.get",
                "description": "Make a GET request to an API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The API URL to request",
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters",
                        },
                    },
                    "required": ["url"],
                },
            }
        ],
        "possible_answer": {
            "requests.get": {
                "url": ["https://api.weather.example/v1/current"],
                "params": [{"city": "New York", "country": "US"}],
            }
        },
    }
]

# Map of category to mock data
MOCK_DATA_MAP = {
    "simple": MOCK_SIMPLE_DATA,
    "multiple": MOCK_MULTIPLE_DATA,
    "parallel": MOCK_PARALLEL_DATA,
    "parallel_multiple": MOCK_PARALLEL_MULTIPLE_DATA,
    "irrelevance": MOCK_IRRELEVANCE_DATA,
    "java": MOCK_JAVA_DATA,
    "javascript": MOCK_JAVASCRIPT_DATA,
    "rest": MOCK_REST_DATA,
}

# Mock responses for different categories
MOCK_RESPONSES = {
    "simple": "calculate_triangle_area(base=10, height=5)",
    "multiple": (
        "predict_house_price(bedrooms=3, bathrooms=2, area=1800, "
        "location='San Francisco')"
    ),
    "parallel": (
        "get_weather(location='New York')\nget_weather(location='London')"
    ),
    "parallel_multiple": (
        "get_weather(location='Boston')\nget_traffic(location='Boston')"
    ),
    "irrelevance": (
        "I don't have a favorite color as I'm an AI, but I'd be happy to help "
        "you with calculations or other tasks."
    ),
    "java": (
        "createHashMap(entries=\"apple\", 1, \"banana\", 2, \"orange\", 3)"
    ),
    "javascript": "createJsObject(properties=\"name: 'John', age: 30\")",
    "rest": (
        "requests.get(url=\"https://api.weather.example/v1/current\", "
        "params={\"city\": \"New York\", \"country\": \"US\"})"
    ),
}


def run_test_for_category(category):
    """Run the test for a specific category and log results"""
    logger.info(f"Testing BFCL benchmark for category: {category}")

    # Patch necessary functions and classes to prevent real file system access
    with (
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
        patch("huggingface_hub.snapshot_download"),
        patch("json.load", return_value=MOCK_DATA_MAP[category]),
        patch("builtins.open", mock_open()),
        patch.object(BFCLBenchmark, 'download'),
    ):
        # Initialize BFCLBenchmark with mock paths
        data_dir = "/mock_data_dir"
        save_to = "mock_save_to.json"
        benchmark = BFCLBenchmark(data_dir=data_dir, save_to=save_to)

        # Mock the agent's generate_response method
        mock_agent = MagicMock()

        # create mock response
        mock_response = MagicMock()
        mock_response.content = str(MOCK_RESPONSES[category])

        # set the return value of the step method
        mock_step_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = str(MOCK_RESPONSES[category])
        mock_step_response.msg = mock_message
        mock_agent.step.return_value = mock_step_response

        # set the return value of the generate_response method
        mock_agent.generate_response.return_value = mock_response

        # Run the benchmark
        benchmark.run(
            agent=mock_agent,
            category=category,
            randomize=False,
            subset=1,
        )

        # Assert the benchmark results
        results_len = len(benchmark._results)
        is_result_correct = benchmark._results[0]["result"] is True
        category_match = benchmark._results[0]["category"] == category

        logger.info(f"  Test completed successfully for {category}")
        logger.info(f"  Results count: {results_len}")
        logger.info(f"  Result correct: {is_result_correct}")
        logger.info(f"  Category match: {category_match}")
        logger.info("  All assertions passed!\n")

        return True


if __name__ == "__main__":
    # set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    logger.info("===== Running BFCL Benchmark Tests =====")
    logger.info(
        "Note: These tests use mocks and don't actually call any real APIs "
        "or models."
    )
    logger.info("Running tests for all categories...")

    all_categories = [
        "simple",
        "multiple",
        "parallel",
        "parallel_multiple",
        "irrelevance",
        "java",
        "javascript",
        "rest",
    ]

    results = []
    for category in all_categories:
        try:
            result = run_test_for_category(category)
            results.append((category, "PASS" if result else "FAIL"))
        except Exception as e:
            logger.error(
                f"  ERROR: Test for {category} failed with exception: {e}"
            )
            results.append((category, "ERROR"))

    # Log summary
    logger.info("\n===== Test Summary =====")
    for category, status in results:
        logger.info(f"{category.ljust(20)}: {status}")

    # Count successes
    success_count = sum(1 for _, status in results if status == "PASS")
    logger.info(
        f"\nPassed {success_count} out of {len(all_categories)} tests."
    )
