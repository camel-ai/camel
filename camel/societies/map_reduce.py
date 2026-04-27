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
import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool

logger = logging.getLogger(__name__)

# ── System prompt templates ──────────────────────────────────────────────────

SPLITTER_SYSTEM_PROMPT = (
    "You are a task coordinator. Your job is to break down a complex task "
    "into exactly {num_mappers} independent, non-overlapping sub-tasks that "
    "can be worked on in parallel.\n\n"
    "Rules:\n"
    "1. Each sub-task must be self-contained and independently solvable.\n"
    "2. Together, the sub-tasks must fully cover the original task.\n"
    "3. Return ONLY a valid JSON list of strings, where each string is one "
    "sub-task description.\n"
    "4. Do NOT include any other text, explanation, or markdown "
    "formatting.\n\n"
    "Example output for 3 sub-tasks:\n"
    '["Sub-task 1 description", "Sub-task 2 description", '
    '"Sub-task 3 description"]'
)

MAPPER_SYSTEM_PROMPT = (
    "You are a {mapper_role_name}. You will receive a specific sub-task to "
    "complete. Provide a thorough, detailed, and well-structured response "
    "for your assigned sub-task. Focus only on the sub-task given to you."
)

REDUCER_SYSTEM_PROMPT = (
    "You are a {reducer_role_name}. You will receive results from multiple "
    "analysts who each worked on a different aspect of the same overall task. "
    "Your job is to synthesize all of their results into one coherent, "
    "comprehensive, and well-organized response.\n\n"
    "Rules:\n"
    "1. Integrate all results — do not simply concatenate them.\n"
    "2. Remove redundancies while preserving all unique information.\n"
    "3. Present the final result in a clear, structured format.\n"
    "4. If there are contradictions between results, note them."
)


class MapReduceSociety:
    r"""A society that implements the MapReduce pattern with LLM agents.

    The MapReduce society decomposes a complex task into independent sub-tasks
    (map phase), processes each sub-task in parallel using separate agents, and
    then aggregates the results into a single coherent output (reduce phase).

    The pipeline has three stages:
        1. **Split**: A splitter agent decomposes the task into N sub-tasks.
        2. **Map**: N mapper agents each process one sub-task in parallel.
        3. **Reduce**: A reducer agent synthesizes all mapper outputs into
           one final result.

    Args:
        task_prompt (str): The task to be processed by the society.
        num_mappers (int): Number of mapper agents to use.
            (default: :obj:`3`)
        mapper_role_name (str): Role name for mapper agents.
            (default: :obj:`"Research Analyst"`)
        reducer_role_name (str): Role name for the reducer agent.
            (default: :obj:`"Senior Editor"`)
        splitter_role_name (str): Role name for the splitter agent.
            (default: :obj:`"Task Coordinator"`)
        model (BaseModelBackend, optional): Model backend to use for all
            agents. If not specified, each agent uses the default model.
            (default: :obj:`None`)
        mapper_agent_kwargs (Dict, optional): Additional keyword arguments
            for mapper agents. (default: :obj:`None`)
        reducer_agent_kwargs (Dict, optional): Additional keyword arguments
            for the reducer agent. (default: :obj:`None`)
        splitter_agent_kwargs (Dict, optional): Additional keyword arguments
            for the splitter agent. (default: :obj:`None`)
        mapper_tools (List[Union[FunctionTool, Callable]], optional): Tools
            available to mapper agents. (default: :obj:`None`)
        reducer_tools (List[Union[FunctionTool, Callable]], optional): Tools
            available to the reducer agent. (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agents. (default: :obj:`None`)
        max_workers (int, optional): Maximum number of threads for parallel
            mapper execution in sync mode. If ``None``, defaults to
            ``num_mappers``. (default: :obj:`None`)

    Example:
        >>> from camel.societies import MapReduceSociety
        >>> society = MapReduceSociety(
        ...     task_prompt="Analyze the impact of AI on healthcare",
        ...     num_mappers=3,
        ... )
        >>> result = society.step()
        >>> print(result.msg.content)
    """

    def __init__(
        self,
        task_prompt: str,
        *,
        num_mappers: int = 3,
        mapper_role_name: str = "Research Analyst",
        reducer_role_name: str = "Senior Editor",
        splitter_role_name: str = "Task Coordinator",
        model: Optional[BaseModelBackend] = None,
        mapper_agent_kwargs: Optional[Dict[str, Any]] = None,
        reducer_agent_kwargs: Optional[Dict[str, Any]] = None,
        splitter_agent_kwargs: Optional[Dict[str, Any]] = None,
        mapper_tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        reducer_tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        output_language: Optional[str] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        if num_mappers < 1:
            raise ValueError(f"num_mappers must be >= 1, got {num_mappers}")

        self.task_prompt = task_prompt
        self.num_mappers = num_mappers
        self.mapper_role_name = mapper_role_name
        self.reducer_role_name = reducer_role_name
        self.splitter_role_name = splitter_role_name
        self.model = model
        self.output_language = output_language
        self.max_workers = max_workers or num_mappers

        # Store kwargs for agent construction
        self._mapper_agent_kwargs = mapper_agent_kwargs or {}
        self._reducer_agent_kwargs = reducer_agent_kwargs or {}
        self._splitter_agent_kwargs = splitter_agent_kwargs or {}
        self._mapper_tools = mapper_tools
        self._reducer_tools = reducer_tools

        # Initialize agents
        self.splitter_agent = self._create_splitter_agent()
        self.mapper_agents = self._create_mapper_agents()
        self.reducer_agent = self._create_reducer_agent()

        # Track results
        self.sub_tasks: Optional[List[str]] = None
        self.mapper_results: Optional[List[str]] = None
        self.final_result: Optional[str] = None

    # ── Agent Factory Methods ────────────────────────────────────────────

    def _apply_model(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        r"""Apply the shared model to kwargs if not already specified."""
        if self.model is not None and "model" not in kwargs:
            kwargs["model"] = self.model
        return kwargs

    def _create_splitter_agent(self) -> ChatAgent:
        r"""Create the splitter agent that decomposes tasks."""
        sys_msg = BaseMessage.make_assistant_message(
            role_name=self.splitter_role_name,
            content=SPLITTER_SYSTEM_PROMPT.format(
                num_mappers=self.num_mappers
            ),
        )
        kwargs = self._apply_model(dict(self._splitter_agent_kwargs))
        return ChatAgent(
            system_message=sys_msg,
            output_language=self.output_language,
            **kwargs,
        )

    def _create_mapper_agents(self) -> List[ChatAgent]:
        r"""Create N mapper agents."""
        sys_msg = BaseMessage.make_assistant_message(
            role_name=self.mapper_role_name,
            content=MAPPER_SYSTEM_PROMPT.format(
                mapper_role_name=self.mapper_role_name
            ),
        )
        agents = []
        for _ in range(self.num_mappers):
            kwargs = self._apply_model(dict(self._mapper_agent_kwargs))
            if self._mapper_tools is not None:
                kwargs.setdefault("tools", self._mapper_tools)
            agents.append(
                ChatAgent(
                    system_message=sys_msg,
                    output_language=self.output_language,
                    **kwargs,
                )
            )
        return agents

    def _create_reducer_agent(self) -> ChatAgent:
        r"""Create the reducer agent that synthesizes results."""
        sys_msg = BaseMessage.make_assistant_message(
            role_name=self.reducer_role_name,
            content=REDUCER_SYSTEM_PROMPT.format(
                reducer_role_name=self.reducer_role_name
            ),
        )
        kwargs = self._apply_model(dict(self._reducer_agent_kwargs))
        if self._reducer_tools is not None:
            kwargs.setdefault("tools", self._reducer_tools)
        return ChatAgent(
            system_message=sys_msg,
            output_language=self.output_language,
            **kwargs,
        )

    # ── Parsing ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_sub_tasks(raw_output: str, num_expected: int) -> List[str]:
        r"""Parse the splitter output into a list of sub-task strings.

        Attempts JSON parsing first, then falls back to line-based extraction.

        Args:
            raw_output (str): The raw text output from the splitter agent.
            num_expected (int): The expected number of sub-tasks.

        Returns:
            List[str]: A list of sub-task description strings.

        Raises:
            ValueError: If the output cannot be parsed or the count is wrong.
        """
        # Try to extract JSON from the output (may be wrapped in markdown)
        json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if json_match:
            try:
                tasks = json.loads(json_match.group())
                if isinstance(tasks, list) and all(
                    isinstance(t, str) for t in tasks
                ):
                    if len(tasks) == num_expected:
                        return tasks
                    logger.warning(
                        f"Splitter returned {len(tasks)} sub-tasks, "
                        f"expected {num_expected}. Using returned tasks."
                    )
                    return tasks
            except json.JSONDecodeError:
                pass

        # Fallback: split by numbered lines (1. ..., 2. ..., etc.)
        lines = re.findall(r'\d+\.\s*(.+)', raw_output)
        if lines:
            return lines

        # Last resort: split by newlines and filter empty
        lines = [
            line.strip()
            for line in raw_output.strip().split('\n')
            if line.strip()
        ]
        if lines:
            return lines

        raise ValueError(
            "Failed to parse sub-tasks from splitter output: "
            f"{raw_output[:200]}"
        )

    # ── Pipeline Stages ──────────────────────────────────────────────────

    def _run_splitter(self) -> List[str]:
        r"""Run the splitter agent to decompose the task.

        Returns:
            List[str]: A list of sub-task descriptions.
        """
        self.splitter_agent.reset()
        split_msg = BaseMessage.make_user_message(
            role_name="user",
            content=f"Break down this task into {self.num_mappers} "
            f"independent sub-tasks:\n\n{self.task_prompt}",
        )
        response = self.splitter_agent.step(split_msg)
        if response.terminated or not response.msgs:
            raise RuntimeError(
                "Splitter agent terminated without producing output."
            )
        raw = response.msgs[0].content
        parsed = self._parse_sub_tasks(raw, self.num_mappers)
        self.sub_tasks = parsed
        logger.info(f"Splitter decomposed task into {len(parsed)} sub-tasks.")
        return parsed

    async def _arun_splitter(self) -> List[str]:
        r"""Async version of :meth:`_run_splitter`.

        Returns:
            List[str]: A list of sub-task descriptions.
        """
        self.splitter_agent.reset()
        split_msg = BaseMessage.make_user_message(
            role_name="user",
            content=f"Break down this task into {self.num_mappers} "
            f"independent sub-tasks:\n\n{self.task_prompt}",
        )
        response = await self.splitter_agent.astep(split_msg)
        if response.terminated or not response.msgs:
            raise RuntimeError(
                "Splitter agent terminated without producing output."
            )
        raw = response.msgs[0].content
        parsed = self._parse_sub_tasks(raw, self.num_mappers)
        self.sub_tasks = parsed
        logger.info(f"Splitter decomposed task into {len(parsed)} sub-tasks.")
        return parsed

    def _run_single_mapper(
        self,
        agent: ChatAgent,
        sub_task: str,
        index: int,
    ) -> Tuple[int, str]:
        r"""Run a single mapper agent on a sub-task.

        Args:
            agent (ChatAgent): The mapper agent to use.
            sub_task (str): The sub-task to process.
            index (int): The mapper index (for ordering results).

        Returns:
            Tuple[int, str]: A tuple of (index, result_content).
        """
        agent.reset()
        mapper_msg = BaseMessage.make_user_message(
            role_name="user",
            content=f"Complete the following sub-task:\n\n{sub_task}",
        )
        response = agent.step(mapper_msg)
        if response.terminated or not response.msgs:
            logger.warning(f"Mapper {index} terminated without output.")
            return (index, f"[Mapper {index} produced no output]")
        return (index, response.msgs[0].content)

    async def _arun_single_mapper(
        self,
        agent: ChatAgent,
        sub_task: str,
        index: int,
    ) -> Tuple[int, str]:
        r"""Async version of :meth:`_run_single_mapper`.

        Args:
            agent (ChatAgent): The mapper agent to use.
            sub_task (str): The sub-task to process.
            index (int): The mapper index (for ordering results).

        Returns:
            Tuple[int, str]: A tuple of (index, result_content).
        """
        agent.reset()
        mapper_msg = BaseMessage.make_user_message(
            role_name="user",
            content=f"Complete the following sub-task:\n\n{sub_task}",
        )
        response = await agent.astep(mapper_msg)
        if response.terminated or not response.msgs:
            logger.warning(f"Mapper {index} terminated without output.")
            return (index, f"[Mapper {index} produced no output]")
        return (index, response.msgs[0].content)

    def _run_mappers(self, sub_tasks: List[str]) -> List[str]:
        r"""Run all mapper agents in parallel (sync, thread-based).

        Args:
            sub_tasks (List[str]): Sub-tasks to distribute among mappers.

        Returns:
            List[str]: Results from all mappers, ordered by index.
        """
        # If we have more sub-tasks than mapper agents, cycle agents
        agents = self.mapper_agents
        pairs = []
        for i, sub_task in enumerate(sub_tasks):
            agent = agents[i % len(agents)]
            pairs.append((agent, sub_task, i))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._run_single_mapper, agent, task, idx)
                for agent, task, idx in pairs
            ]
            indexed_results = [f.result() for f in futures]

        # Sort by index to preserve order
        indexed_results.sort(key=lambda x: x[0])
        results = [r for _, r in indexed_results]
        self.mapper_results = results
        logger.info(f"Completed {len(results)} mapper tasks.")
        return results

    async def _arun_mappers(self, sub_tasks: List[str]) -> List[str]:
        r"""Run all mapper agents in parallel (async).

        Args:
            sub_tasks (List[str]): Sub-tasks to distribute among mappers.

        Returns:
            List[str]: Results from all mappers, ordered by index.
        """
        agents = self.mapper_agents
        tasks = []
        for i, sub_task in enumerate(sub_tasks):
            agent = agents[i % len(agents)]
            tasks.append(self._arun_single_mapper(agent, sub_task, i))

        indexed_results = await asyncio.gather(*tasks)
        # Sort by index to preserve order
        sorted_results = sorted(indexed_results, key=lambda x: x[0])
        results = [r for _, r in sorted_results]
        self.mapper_results = results
        logger.info(f"Completed {len(results)} mapper tasks.")
        return results

    def _format_mapper_results(
        self,
        sub_tasks: List[str],
        results: List[str],
    ) -> str:
        r"""Format mapper results for the reducer.

        Args:
            sub_tasks (List[str]): The sub-task descriptions.
            results (List[str]): The mapper results.

        Returns:
            str: Formatted text combining sub-tasks and their results.
        """
        sections = []
        for i, (task, result) in enumerate(zip(sub_tasks, results), 1):
            sections.append(
                f"--- Result {i} ---\n"
                f"Sub-task: {task}\n"
                f"Response:\n{result}"
            )
        return "\n\n".join(sections)

    def _run_reducer(
        self,
        sub_tasks: List[str],
        results: List[str],
    ) -> ChatAgentResponse:
        r"""Run the reducer agent to synthesize all mapper results.

        Args:
            sub_tasks (List[str]): The sub-task descriptions.
            results (List[str]): The mapper results.

        Returns:
            ChatAgentResponse: The reducer's aggregated response.
        """
        self.reducer_agent.reset()
        formatted = self._format_mapper_results(sub_tasks, results)
        reduce_msg = BaseMessage.make_user_message(
            role_name="user",
            content=(
                f"Original task: {self.task_prompt}\n\n"
                f"Below are results from {len(results)} analysts who each "
                f"worked on a different aspect of the task. Synthesize them "
                f"into one comprehensive response.\n\n{formatted}"
            ),
        )
        response = self.reducer_agent.step(reduce_msg)
        if response.msgs:
            self.final_result = response.msgs[0].content
        return response

    async def _arun_reducer(
        self,
        sub_tasks: List[str],
        results: List[str],
    ) -> ChatAgentResponse:
        r"""Async version of :meth:`_run_reducer`.

        Args:
            sub_tasks (List[str]): The sub-task descriptions.
            results (List[str]): The mapper results.

        Returns:
            ChatAgentResponse: The reducer's aggregated response.
        """
        self.reducer_agent.reset()
        formatted = self._format_mapper_results(sub_tasks, results)
        reduce_msg = BaseMessage.make_user_message(
            role_name="user",
            content=(
                f"Original task: {self.task_prompt}\n\n"
                f"Below are results from {len(results)} analysts who each "
                f"worked on a different aspect of the task. Synthesize them "
                f"into one comprehensive response.\n\n{formatted}"
            ),
        )
        response = await self.reducer_agent.astep(reduce_msg)
        if response.msgs:
            self.final_result = response.msgs[0].content
        return response

    # ── Public API ───────────────────────────────────────────────────────

    def reset(self) -> None:
        r"""Reset all agents and clear tracked state."""
        self.splitter_agent.reset()
        for agent in self.mapper_agents:
            agent.reset()
        self.reducer_agent.reset()
        self.sub_tasks = None
        self.mapper_results = None
        self.final_result = None

    def step(self) -> ChatAgentResponse:
        r"""Run the full MapReduce pipeline synchronously.

        Executes the three-stage pipeline:
            1. **Split**: Decompose the task into sub-tasks.
            2. **Map**: Process each sub-task in parallel using threads.
            3. **Reduce**: Synthesize all results into a single response.

        Returns:
            ChatAgentResponse: The final aggregated response from the
                reducer agent.

        Raises:
            RuntimeError: If the splitter agent fails to produce sub-tasks.
            ValueError: If the splitter output cannot be parsed.
        """
        # Stage 1: Split
        sub_tasks = self._run_splitter()

        # Stage 2: Map (parallel)
        results = self._run_mappers(sub_tasks)

        # Stage 3: Reduce
        response = self._run_reducer(sub_tasks, results)

        response.info['sub_tasks'] = sub_tasks
        response.info['mapper_results'] = results
        response.info['num_mappers'] = len(sub_tasks)

        return response

    async def astep(self) -> ChatAgentResponse:
        r"""Run the full MapReduce pipeline asynchronously.

        Executes the three-stage pipeline:
            1. **Split**: Decompose the task into sub-tasks.
            2. **Map**: Process each sub-task concurrently via
               ``asyncio.gather``.
            3. **Reduce**: Synthesize all results into a single response.

        Returns:
            ChatAgentResponse: The final aggregated response from the
                reducer agent.

        Raises:
            RuntimeError: If the splitter agent fails to produce sub-tasks.
            ValueError: If the splitter output cannot be parsed.
        """
        # Stage 1: Split
        sub_tasks = await self._arun_splitter()

        # Stage 2: Map (concurrent)
        results = await self._arun_mappers(sub_tasks)

        # Stage 3: Reduce
        response = await self._arun_reducer(sub_tasks, results)

        response.info['sub_tasks'] = sub_tasks
        response.info['mapper_results'] = results
        response.info['num_mappers'] = len(sub_tasks)

        return response
