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

from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import MapReduceSociety
from camel.types import ModelPlatformType, ModelType

# ── Shared model ─────────────────────────────────────────────────────────


def _get_model():
    """Create a Groq model backend for testing."""
    return ModelFactory.create(
        model_platform=ModelPlatformType.GROQ,
        model_type=ModelType.GROQ_LLAMA_3_3_70B,
    )


# ── Unit Tests (no API calls) ───────────────────────────────────────────


def test_map_reduce_init():
    """Test that MapReduceSociety initializes all agents correctly."""
    society = MapReduceSociety(
        task_prompt="Analyze renewable energy",
        num_mappers=3,
        model=_get_model(),
    )

    assert society.task_prompt == "Analyze renewable energy"
    assert society.num_mappers == 3
    assert society.splitter_agent is not None
    assert len(society.mapper_agents) == 3
    assert society.reducer_agent is not None
    assert society.sub_tasks is None
    assert society.mapper_results is None
    assert society.final_result is None


def test_map_reduce_init_invalid_mappers():
    """Test that num_mappers < 1 raises ValueError."""
    with pytest.raises(ValueError, match="num_mappers must be >= 1"):
        MapReduceSociety(
            task_prompt="Test",
            num_mappers=0,
        )


def test_map_reduce_init_custom_roles():
    """Test initialization with custom role names."""
    society = MapReduceSociety(
        task_prompt="Test task",
        num_mappers=2,
        mapper_role_name="Data Scientist",
        reducer_role_name="Chief Analyst",
        splitter_role_name="Project Manager",
        model=_get_model(),
    )

    assert society.mapper_role_name == "Data Scientist"
    assert society.reducer_role_name == "Chief Analyst"
    assert society.splitter_role_name == "Project Manager"
    assert len(society.mapper_agents) == 2


def test_parse_sub_tasks_json():
    """Test parsing sub-tasks from valid JSON."""
    raw = '["task1", "task2", "task3"]'
    result = MapReduceSociety._parse_sub_tasks(raw, 3)
    assert result == ["task1", "task2", "task3"]


def test_parse_sub_tasks_json_in_markdown():
    """Test parsing sub-tasks from JSON wrapped in markdown."""
    raw = '```json\n["task1", "task2"]\n```'
    result = MapReduceSociety._parse_sub_tasks(raw, 2)
    assert result == ["task1", "task2"]


def test_parse_sub_tasks_numbered_lines():
    """Test fallback parsing from numbered lines."""
    raw = "1. First sub-task\n2. Second sub-task\n3. Third sub-task"
    result = MapReduceSociety._parse_sub_tasks(raw, 3)
    assert result == [
        "First sub-task",
        "Second sub-task",
        "Third sub-task",
    ]


def test_parse_sub_tasks_newlines():
    """Test fallback parsing from plain newlines."""
    raw = "Task A\nTask B"
    result = MapReduceSociety._parse_sub_tasks(raw, 2)
    assert result == ["Task A", "Task B"]


def test_parse_sub_tasks_empty():
    """Test that empty output raises ValueError."""
    with pytest.raises(ValueError, match="Failed to parse"):
        MapReduceSociety._parse_sub_tasks("", 3)


def test_map_reduce_reset():
    """Test that reset() clears all state."""
    society = MapReduceSociety(
        task_prompt="Test",
        num_mappers=2,
        model=_get_model(),
    )

    # Manually set some state
    society.sub_tasks = ["a", "b"]
    society.mapper_results = ["r1", "r2"]
    society.final_result = "final"

    society.reset()

    assert society.sub_tasks is None
    assert society.mapper_results is None
    assert society.final_result is None


# ── Integration Tests (real API calls via Groq) ─────────────────────────


@pytest.mark.model_backend
def test_map_reduce_step():
    """Test the full step() pipeline with real Groq API."""
    society = MapReduceSociety(
        task_prompt=(
            "List one advantage and one disadvantage of solar energy, "
            "wind energy, and nuclear energy."
        ),
        num_mappers=3,
        model=_get_model(),
    )

    result = society.step()

    # Verify response structure
    assert result is not None
    assert result.msgs is not None
    assert len(result.msgs) == 1
    assert isinstance(result.msgs[0], BaseMessage)
    assert result.msg is not None
    assert len(result.msg.content) > 0
    assert result.terminated is False

    # Verify info contains MapReduce metadata
    assert 'sub_tasks' in result.info
    assert 'mapper_results' in result.info
    assert 'num_mappers' in result.info
    assert len(result.info['sub_tasks']) == 3
    assert len(result.info['mapper_results']) == 3

    # Verify state was tracked
    assert society.sub_tasks is not None
    assert society.mapper_results is not None
    assert society.final_result is not None


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_map_reduce_astep():
    """Test the full astep() pipeline with real Groq API."""
    society = MapReduceSociety(
        task_prompt=(
            "Give one fact about Python and one fact about JavaScript."
        ),
        num_mappers=2,
        model=_get_model(),
    )

    result = await society.astep()

    assert result is not None
    assert result.msgs is not None
    assert len(result.msgs) == 1
    assert len(result.msg.content) > 0
    assert 'sub_tasks' in result.info
    assert result.info['num_mappers'] == 2


@pytest.mark.model_backend
@pytest.mark.parametrize("num_mappers", [1, 2])
def test_map_reduce_custom_num_mappers(num_mappers):
    """Test with different numbers of mapper agents."""
    society = MapReduceSociety(
        task_prompt="Briefly describe the color blue.",
        num_mappers=num_mappers,
        model=_get_model(),
    )

    assert len(society.mapper_agents) == num_mappers

    result = society.step()
    assert result.msg is not None
    assert len(result.msg.content) > 0
    assert result.info['num_mappers'] == num_mappers
