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
from unittest.mock import MagicMock, mock_open, patch

from camel.agents import ChatAgent
from camel.datagen.self_instruct import (
    InstructionFilter,
    SelfInstructPipeline,
)


class TestSelfInstructPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_agent = MagicMock(spec=ChatAgent)
        self.mock_agent.step.return_value.msgs = [
            MagicMock(content="Generated task")
        ]

        self.seed_data = [
            {"instruction": "Human task 1"},
            {"instruction": "Human task 2"},
            {"instruction": "Human task 3"},
        ]

        self.exists_patch = patch("os.path.exists", return_value=True)
        self.mock_exists = self.exists_patch.start()

        self.open_patch = patch(
            "builtins.open",
            mock_open(
                read_data='[{"instruction": "Human task 1"}, '
                '{"instruction": "Human task 2"}, '
                '{"instruction": "Human task 3"}]'
            ),
        )
        self.mock_open = self.open_patch.start()

        self.mock_filter = MagicMock(spec=InstructionFilter)
        self.mock_filter.filter.return_value = True
        self.mock_filter.filters = []

    def tearDown(self):
        self.exists_patch.stop()
        self.open_patch.stop()

    def test_load_seed(self):
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            instruction_filter=self.mock_filter,
        )

        self.assertEqual(len(pipeline.human_tasks), 3)
        self.assertEqual(
            pipeline.human_tasks[0]["instruction"], "Human task 1"
        )

    def test_sample_human_tasks(self):
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            instruction_filter=self.mock_filter,
        )
        sampled = pipeline.sample_human_tasks(2)
        self.assertEqual(len(sampled), 2)
        sampled_all = pipeline.sample_human_tasks(10)
        self.assertEqual(len(sampled_all), 3)

    def test_sample_machine_tasks_no_tasks_yet(self):
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            instruction_filter=self.mock_filter,
        )
        sampled = pipeline.sample_machine_tasks(2)
        self.assertEqual(len(sampled), 2)
        self.assertEqual(sampled[0]["instruction"], "")
        self.assertEqual(sampled[1]["instruction"], "")

    def test_sample_machine_tasks_with_existing(self):
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            instruction_filter=self.mock_filter,
        )
        pipeline.machine_tasks = [
            {"instruction": "Machine task 1"},
            {"instruction": "Machine task 2"},
            {"instruction": "Machine task 3"},
        ]
        sampled = pipeline.sample_machine_tasks(2)
        self.assertEqual(len(sampled), 2)
        self.assertTrue(all("instruction" in t for t in sampled))

    def test_generate_machine_instruction(self):
        self.mock_agent.step.return_value.msgs = [
            MagicMock(content="Task 1: Something\nTask 2: Another\nTask 3:")
        ]
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            human_to_machine_ratio=(2, 1),
            instruction_filter=self.mock_filter,
        )
        instruction = pipeline.generate_machine_instruction()
        self.assertEqual(instruction, "Task 1: Something")

    @patch.object(
        SelfInstructPipeline, 'identify_instruction', return_value=True
    )
    def test_generate(self, mock_identify):
        self.mock_agent.step.return_value.msgs = [
            MagicMock(content="Generated machine task\n")
        ]

        pass_once = [True, False, False, True, True]
        self.mock_filter.filter.side_effect = pass_once

        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            num_machine_instructions=3,
            instruction_filter=self.mock_filter,
        )

        pipeline.generate()
        self.assertEqual(len(pipeline.machine_tasks), 3)
        self.assertGreaterEqual(mock_identify.call_count, 3)

    @patch("json.dump")
    def test_construct_data(self, mock_dump):
        pipeline = SelfInstructPipeline(
            agent=self.mock_agent,
            seed="some_path.json",
            instruction_filter=self.mock_filter,
        )
        pipeline.machine_tasks = [
            {
                "id": "machine_task_1",
                "instruction": "Some instruction",
                "is_classification": True,
                "instances": [],
            }
        ]
        pipeline.construct_data()
        mock_dump.assert_called_once()
        args, kwargs = mock_dump.call_args
        self.assertEqual(args[0], pipeline.machine_tasks)


if __name__ == "__main__":
    unittest.main()
