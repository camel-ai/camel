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
import pytest

from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.utils import RecoveryStrategy, TaskAnalysisResult


class TestFixCommonIssuesRecoveryStrategy:
    """Regression tests for non-string ``recovery_strategy`` values.

    ``_fix_common_issues`` used to call ``.lower()`` on the value
    unconditionally, so weak-model outputs like
    ``"recovery_strategy": ["retry"]`` raised ``AttributeError`` out of the
    best-effort fix path and crashed the whole parse instead of falling back.
    """

    def test_non_string_recovery_strategy_uses_fallback_values(self):
        response = '{"reasoning": "task failed", "recovery_strategy": ["retry"]}'
        fallback_values = {
            "reasoning": "Defaulting to retry due to parsing error",
            "recovery_strategy": RecoveryStrategy.RETRY,
        }

        result = StructuredOutputHandler.parse_structured_response(
            response, TaskAnalysisResult, fallback_values=fallback_values
        )

        assert isinstance(result, TaskAnalysisResult)
        assert result.recovery_strategy == RecoveryStrategy.RETRY

    def test_non_string_recovery_strategy_without_fallback_is_safe(self):
        response = '{"reasoning": "task failed", "recovery_strategy": 3}'

        result = StructuredOutputHandler.parse_structured_response(
            response, TaskAnalysisResult
        )

        assert isinstance(result, TaskAnalysisResult)
        assert result.recovery_strategy == RecoveryStrategy.RETRY

    @pytest.mark.parametrize(
        "raw_value, expected",
        [
            ("RETRY", RecoveryStrategy.RETRY),
            ("rety", RecoveryStrategy.RETRY),
            ("replan", RecoveryStrategy.REPLAN),
        ],
    )
    def test_string_recovery_strategy_normalization_unchanged(
        self, raw_value, expected
    ):
        response = (
            '{"reasoning": "task failed", '
            f'"recovery_strategy": "{raw_value}"'
            '}'
        )

        result = StructuredOutputHandler.parse_structured_response(
            response, TaskAnalysisResult
        )

        assert isinstance(result, TaskAnalysisResult)
        assert result.recovery_strategy == expected
