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

import pytest

from camel.toolkits import SearxNGToolkit


class TestSearxNGToolkitInitialization:
    r"""Test cases for SearxNGToolkit initialization."""

    def test_init_with_valid_parameters(self):
        r"""Test initialization with valid parameters."""
        toolkit = SearxNGToolkit(
            searxng_host="https://searx.example.org",
            language="en",
            categories=["general"],
            time_range="day",
            safe_search=1,
        )
        assert toolkit.searxng_host == "https://searx.example.org"
        assert toolkit.language == "en"
        assert toolkit.categories == ["general"]
        assert toolkit.time_range == "day"
        assert toolkit.safe_search == 1

    def test_init_with_default_parameters(self):
        r"""Test initialization with default parameters."""
        toolkit = SearxNGToolkit(searxng_host="https://searx.example.org")
        assert toolkit.searxng_host == "https://searx.example.org"
        assert toolkit.language == "en"
        assert toolkit.categories == ["general"]
        assert toolkit.time_range is None
        assert toolkit.safe_search == 1

    def test_init_with_trailing_slash_in_host(self):
        r"""Test that trailing slashes are removed from the host URL."""
        toolkit = SearxNGToolkit(searxng_host="https://searx.example.org/")
        assert toolkit.searxng_host == "https://searx.example.org"


class TestSearxNGToolkitTimeRangeValidation:
    r"""Test cases specifically for the time_range validation functionality."""

    @pytest.mark.parametrize(
        "time_range",
        ["day", "week", "month", "year"],
    )
    def test_valid_time_ranges(self, time_range):
        r"""Test that valid time ranges are accepted."""
        # This should not raise an exception
        toolkit = SearxNGToolkit(
            searxng_host="https://searx.example.org",
            time_range=time_range,
        )
        assert toolkit.time_range == time_range

    @pytest.mark.parametrize(
        "invalid_time_range",
        [
            "hour",
            "daily",
            "monthly",
            "yearly",
            "quarter",
            "decade",
            "century",
            "",
            "DAY",  # Case sensitive
            " day",  # With whitespace
            "day ",
            123,  # Wrong type (will be caught by type checking)
        ],
    )
    def test_invalid_time_ranges(self, invalid_time_range):
        r"""Test that invalid time ranges raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range=invalid_time_range,
            )

        # Verify the error message contains useful information
        error_message = str(excinfo.value)
        assert "Invalid time_range" in error_message
        assert str(invalid_time_range) in error_message
        assert "day" in error_message
        assert "week" in error_message
        assert "month" in error_message
        assert "year" in error_message

    def test_none_time_range(self):
        r"""Test that None is accepted as a time_range value."""
        # This should not raise an exception
        toolkit = SearxNGToolkit(
            searxng_host="https://searx.example.org",
            time_range=None,
        )
        assert toolkit.time_range is None

    def test_direct_method_call(self):
        r"""Test directly calling the _validate_time_range method."""
        toolkit = SearxNGToolkit(searxng_host="https://searx.example.org")

        # Valid time ranges should not raise exceptions
        for valid_range in ["day", "week", "month", "year"]:
            toolkit._validate_time_range(valid_range)  # Should not raise

        # Invalid time range should raise ValueError
        with pytest.raises(ValueError):
            toolkit._validate_time_range("invalid_range")


class TestSearxNGToolkitTimeRangeEdgeCases:
    r"""Test edge cases for time_range validation."""

    def test_time_range_case_sensitivity(self):
        r"""Test that time range validation is case sensitive."""
        with pytest.raises(ValueError):
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range="Day",  # Capitalized
            )

        with pytest.raises(ValueError):
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range="WEEK",  # All caps
            )

    def test_time_range_with_whitespace(self):
        r"""Test that time range validation rejects values with whitespace."""
        with pytest.raises(ValueError):
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range=" day",  # Leading space
            )

        with pytest.raises(ValueError):
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range="month ",  # Trailing space
            )

        with pytest.raises(ValueError):
            SearxNGToolkit(
                searxng_host="https://searx.example.org",
                time_range=" year ",  # Both leading and trailing space
            )
