import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.benchmarks import MATHBenchmark, Mode

SAMPLE_DATA = [
    {"problem": "Solve for x: x^2 - 4 = 0", "solution": r"Let’s solve: $x^2 - 4 = 0 \boxed{2}$"},
    {"problem": "What is the sum of the first 10 positive integers?", "solution": r"Using the formula: $\boxed{55}$"},
]

@pytest.fixture
def benchmark():
    r"""Fixture to initialize MATHBenchmark with a fully mocked file system."""
    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.is_dir", return_value=True), patch("pathlib.Path.exists", return_value=True):
        temp_dir = tempfile.mkdtemp()
        return MATHBenchmark(data_dir=Path(temp_dir), save_to=Path(temp_dir))

def test_prepare_dataset(benchmark):
    r"""Test that _prepare_dataset extracts solutions correctly."""
    df = benchmark._prepare_dataset(SAMPLE_DATA)
    assert "solutions" in df.columns
    assert list(df["solutions"]) == ["2", "55"]

@patch("builtins.open")
@patch("pathlib.Path.is_dir", return_value=True)
@patch("pathlib.Path.exists", return_value=True)
def test_run(mock_exists, mock_is_dir, mock_file, benchmark):
    r"""Test that MATHBenchmark runs correctly and writes expected results."""
    benchmark._data = {"test": SAMPLE_DATA}
    mock_agent = MagicMock(spec=ChatAgent)
    mock_agent.step.return_value.msgs = [MagicMock(content="\boxed{2}")]
    
    results = benchmark.run(agent=mock_agent, on="test", mode=Mode("pass@k", 1))
    assert "correct" in results._results[0]
    mock_file().write.assert_called()

def test_generate_solutions(benchmark):
    r"""Test that _generate_solutions properly calls ChatAgent and formats responses."""
    df = benchmark._prepare_dataset(SAMPLE_DATA)
    mock_agent = MagicMock(spec=ChatAgent)
    mock_agent.step.return_value.msgs = [MagicMock(content="\boxed{2}")]
    
    result_df = benchmark._generate_solutions(mock_agent, df, Mode("pass@k", 1))
    assert "answers" in result_df.columns
    assert result_df["answers"].apply(lambda x: x[0] == "\boxed{2}").all()
