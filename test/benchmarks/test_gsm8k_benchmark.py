import json
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import tempfile

from camel.benchmarks import GSM8KBenchmark, Mode
from camel.agents import ChatAgent

SAMPLE_DATA = [
    {"question": "What is 5 + 7?", "answer": "#### 12"},
    {"question": "Find the product of 8 and 3.", "answer": "#### 24"},
]

@pytest.fixture
def benchmark():
    r"""Fixture to initialize GSM8KBenchmark with a fully mocked file system."""
    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.is_dir", return_value=True), patch("pathlib.Path.exists", return_value=True):
        temp_dir = tempfile.mkdtemp()
        return GSM8KBenchmark(data_dir=Path(temp_dir), save_to=Path(temp_dir))

@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path.is_dir", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
def test_run(mock_exists, mock_is_dir, mock_file, benchmark):
    r"""Test that GSM8KBenchmark runs correctly and writes expected results."""
    benchmark._data = {"test": SAMPLE_DATA}
    mock_agent = MagicMock(spec=ChatAgent)
    mock_agent.step.return_value.msgs = [MagicMock(content="#### 12")]   
    results = benchmark.run(agent=mock_agent, on="test", mode=Mode("pass@k", 1))
    assert "correct" in results._results[0]
    mock_file().write.assert_called()

def test_prepare_dataset(benchmark):
    r"""Test that _prepare_dataset extracts solutions correctly."""
    df = benchmark._prepare_dataset(SAMPLE_DATA)
    assert "solution" in df.columns
    assert list(df["solution"]) == ["12", "24"]


def test_preprocess_answers(benchmark):
    r"""Test that _preprocess_answers correctly extracts numeric values from answers."""
    raw_answers = pd.Series(["#### 12", "#### 24", "Mock test with text and numbers 13 #### -7"])
    processed = benchmark._preprocess_answers(raw_answers)
    assert list(processed) == ["12", "24", "-7"]
