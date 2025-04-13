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
import unittest
from unittest.mock import MagicMock, patch

from camel.datagen.self_instruct import (
    FILTER_REGISTRY,
    FilterFunction,
    InstructionFilter,
)


class DummyPassFilter(FilterFunction):
    """A dummy filter that always passes."""

    def apply(self, instruction: str) -> bool:
        return True


class DummyFailFilter(FilterFunction):
    """A dummy filter that always fails."""

    def apply(self, instruction: str) -> bool:
        return False


class TestInstructionFilter(unittest.TestCase):
    def setUp(self):
        self.config_all_pass = {
            "length": {},
            "keyword": {},
        }

        self.config_mixed = {
            "length": {"min_len": 2, "max_len": 5},
            "keyword": {"keywords": ["forbidden"]},
        }

    @patch.dict(FILTER_REGISTRY, {"pass_filter": lambda _: DummyPassFilter()})
    def test_all_pass_filters(self):
        filters_config = {"pass_filter": {}}
        instruction_filter = InstructionFilter(filters_config)
        self.assertTrue(
            instruction_filter.filter(prompt="", instruction="Any instruction")
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="Any instruction", return_details=True
        )
        self.assertTrue(result)
        self.assertEqual(len(failed_filters), 0)

    @patch.dict(
        FILTER_REGISTRY,
        {
            "first_fail_filter": lambda _: DummyFailFilter(),
            "second_fail_filter": lambda _: DummyFailFilter(),
        },
    )
    def test_all_fail_filters(self):
        filters_config = {"first_fail_filter": {}, "second_fail_filter": {}}
        instruction_filter = InstructionFilter(filters_config)
        self.assertFalse(
            instruction_filter.filter(prompt="", instruction="Any instruction")
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="Any instruction", return_details=True
        )
        self.assertFalse(result)
        self.assertEqual(len(failed_filters), 2)
        self.assertIn("DummyFailFilter", failed_filters)

    @patch.dict(
        FILTER_REGISTRY,
        {
            "first_fail_filter": lambda _: DummyFailFilter(),
            "second_fail_filter": lambda _: DummyFailFilter(),
        },
    )
    def test_all_fail_filters_early_stop(self):
        filters_config = {"first_fail_filter": {}, "second_fail_filter": {}}
        instruction_filter = InstructionFilter(
            filters_config, stop_on_first_failure=True
        )
        self.assertFalse(
            instruction_filter.filter(prompt="", instruction="Any instruction")
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="Any instruction", return_details=True
        )
        self.assertFalse(result)
        self.assertEqual(len(failed_filters), 1)
        self.assertIn("DummyFailFilter", failed_filters)

    @patch.dict(
        FILTER_REGISTRY,
        {
            "length": lambda kwargs: MagicMock(
                spec=FilterFunction,
                apply=lambda instr: 2 <= len(instr.split()) <= 5,
            ),
            "keyword": lambda kwargs: MagicMock(
                spec=FilterFunction,
                apply=lambda instr: "forbidden" not in instr.lower(),
            ),
        },
    )
    def test_mixed_filters(self):
        instruction_filter = InstructionFilter(self.config_mixed)

        self.assertTrue(
            instruction_filter.filter(prompt="", instruction="This is valid")
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="This is valid", return_details=True
        )
        self.assertTrue(result)
        self.assertEqual(len(failed_filters), 0)

        self.assertFalse(
            instruction_filter.filter(
                prompt="",
                instruction="This instruction is definitely too long",
            )
        )
        result, failed_filters = instruction_filter.filter(
            prompt="",
            instruction="This instruction is definitely too long",
            return_details=True,
        )
        self.assertFalse(result)
        self.assertIn("MagicMock", failed_filters)

        self.assertFalse(
            instruction_filter.filter(
                prompt="", instruction="This is forbidden"
            )
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="This is forbidden", return_details=True
        )
        self.assertFalse(result)
        self.assertIn("MagicMock", failed_filters)

    @patch.dict(FILTER_REGISTRY, {})
    def test_unknown_filter_raises(self):
        with self.assertRaises(ValueError):
            InstructionFilter({"unknown_filter": {}})

    @patch.dict(FILTER_REGISTRY, {"pass_filter": lambda _: DummyPassFilter()})
    def test_add_custom_filter(self):
        filters_config = {"pass_filter": {}}
        instruction_filter = InstructionFilter(filters_config)
        self.assertTrue(
            instruction_filter.filter(
                prompt="", instruction="Some instruction"
            )
        )

        instruction_filter.add_filter(DummyFailFilter())
        self.assertFalse(
            instruction_filter.filter(
                prompt="", instruction="Some instruction"
            )
        )
        result, failed_filters = instruction_filter.filter(
            prompt="", instruction="Some instruction", return_details=True
        )
        self.assertFalse(result)
        self.assertIn("DummyFailFilter", failed_filters)


if __name__ == "__main__":
    unittest.main()
