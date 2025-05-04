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

from camel.datagen.source2synth.data_processor import (
    Source2SynthDataGenPipeline,
    UserDataProcessor,
)
from camel.datagen.source2synth.user_data_processor_config import (
    ProcessorConfig,
)


class TestSource2SynthDataGenPipeline(unittest.TestCase):
    """Test cases for the Source2SynthDataGenPipeline class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the UserDataProcessor
        self.mock_processor = MagicMock(spec=UserDataProcessor)

        # Create sample result data
        self.sample_result = [
            {
                'text': 'Sample processed text',
                'qa_pairs': [
                    {
                        'type': 'multi_hop_qa',
                        'question': 'How does A lead to C?',
                        'reasoning_steps': [
                            {'step': 'First, A leads to B'},
                            {'step': 'Then, B leads to C'},
                        ],
                        'answer': 'A leads to C through B',
                        'supporting_facts': ['A->B', 'B->C'],
                    }
                ],
                'metadata': {'source': 'test_source', 'complexity': 0.8},
            }
        ]

        # Configure mock to return sample results
        self.mock_processor.process_text.return_value = self.sample_result
        self.mock_processor.process_batch.return_value = self.sample_result * 2

        # Create pipeline with mocked processor
        self.pipeline = Source2SynthDataGenPipeline(
            config=ProcessorConfig(seed=42), output_path="test_output.json"
        )
        self.pipeline.processor = self.mock_processor

    def test_generate_with_string(self):
        """Test generate() with a single string input."""
        # Call generate with string input
        result = self.pipeline.generate("Test input text")

        # Verify processor.process_text was called correctly
        self.mock_processor.process_text.assert_called_once_with(
            "Test input text"
        )

        # Verify result is correct
        self.assertEqual(result, self.sample_result)

    def test_generate_with_string_list(self):
        """Test generate() with a list of strings."""
        input_texts = ["Text 1", "Text 2", "Text 3"]

        # Call generate with list of strings
        result = self.pipeline.generate(input_texts)

        # Verify processor.process_batch was called correctly
        self.mock_processor.process_batch.assert_called_once_with(input_texts)

        # Verify result is correct
        self.assertEqual(result, self.sample_result * 2)

    def test_generate_with_dict_list(self):
        """Test generate() with a list of dictionaries."""
        input_data = [
            {"text": "Text 1", "source": "source1"},
            {"text": "Text 2", "source": "source2"},
        ]

        # Expected text and source lists extracted from input
        expected_texts = ["Text 1", "Text 2"]
        expected_sources = ["source1", "source2"]

        # Call generate with dict list
        result = self.pipeline.generate(input_data)

        # Verify processor.process_batch was called
        # with extracted text and sources
        self.mock_processor.process_batch.assert_called_once_with(
            expected_texts, expected_sources
        )

        # Verify result is correct
        self.assertEqual(result, self.sample_result * 2)

    def test_generate_invalid_input(self):
        """Test generate() with invalid input types."""
        # Test with invalid single input (not string)
        with self.assertRaises(ValueError):
            self.pipeline.generate(123)

        # Test with a list of invalid items - should return empty list
        result = self.pipeline.generate([1, 2, 3])
        self.assertEqual(result, [])

    @patch('time.time', side_effect=[100, 115])  # Mock start and end times
    @patch('json.dump')
    def test_execute(self, mock_dump, mock_time):
        """Test execute() method with proper result saving and timing."""
        # Mock the generate method to control its output
        with patch.object(
            self.pipeline, 'generate', return_value=self.sample_result
        ) as mock_generate:
            # Setup for file operations
            with patch('builtins.open', MagicMock()):
                # Call execute with sample input
                result = self.pipeline.execute("Test input for execute")

                # Verify generate was called with correct input
                mock_generate.assert_called_once_with("Test input for execute")

                # Verify correct result was returned
                self.assertEqual(result, self.sample_result)

                # Verify result was saved
                mock_dump.assert_called_once()
                args, kwargs = mock_dump.call_args
                # First argument should be the result data in a dict with
                # 'examples' key
                self.assertEqual(args[0], {"examples": self.sample_result})

                # Verify logging occurred (implicitly, since logging is mocked)


if __name__ == "__main__":
    unittest.main()
