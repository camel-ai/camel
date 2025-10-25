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

import glob
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.types import OpenAIBackendRole
from camel.utils.context_utils import ContextUtility, WorkflowSummary

logger = get_logger(__name__)


class WorkflowSelectionMethod(Enum):
    r"""Enum representing the method used to select workflows.

    Attributes:
        AGENT_SELECTED: Agent-based intelligent selection using metadata.
        ROLE_NAME_MATCH: Pattern matching by role_name.
        MOST_RECENT: Fallback to most recent workflows.
        ALL_AVAILABLE: Returned all workflows (fewer than max requested).
        NONE: No workflows available.
    """

    AGENT_SELECTED = "agent_selected"
    ROLE_NAME_MATCH = "role_name_match"
    MOST_RECENT = "most_recent"
    ALL_AVAILABLE = "all_available"
    NONE = "none"


class WorkflowMemoryManager:
    r"""Manages workflow memory operations for workforce workers.

    This class encapsulates all workflow memory functionality including
    intelligent loading, saving, and selection of workflows. It separates
    workflow management concerns from the core worker task processing logic.

    Args:
        worker (ChatAgent): The worker agent that will use workflows.
        description (str): Description of the worker's role.
        context_utility (Optional[ContextUtility]): Shared context utility
            for workflow operations. If None, creates a new instance.
    """

    def __init__(
        self,
        worker: ChatAgent,
        description: str,
        context_utility: Optional[ContextUtility] = None,
    ):
        # validate worker type at initialization
        if not isinstance(worker, ChatAgent):
            raise TypeError(
                f"Worker must be a ChatAgent instance, "
                f"got {type(worker).__name__}"
            )

        self.worker = worker
        self.description = description
        self._context_utility = context_utility

    def _get_context_utility(self) -> ContextUtility:
        r"""Get context utility with lazy initialization."""
        if self._context_utility is None:
            self._context_utility = ContextUtility.get_workforce_shared()
        return self._context_utility

    def load_workflows(
        self,
        pattern: Optional[str] = None,
        max_files_to_load: int = 3,
        session_id: Optional[str] = None,
        use_smart_selection: bool = True,
    ) -> bool:
        r"""Load workflow memories using intelligent agent-based selection.

        This method uses the worker agent to intelligently select the most
        relevant workflows based on workflow information (title, description,
        tags) rather than simple filename pattern matching.

        Args:
            pattern (Optional[str]): Legacy parameter for backward
                compatibility. When use_smart_selection=False, uses this
                pattern for file matching. Ignored when smart selection
                is enabled.
            max_files_to_load (int): Maximum number of workflow files to load.
                (default: :obj:`3`)
            session_id (Optional[str]): Specific workforce session ID to load
                from. If None, searches across all sessions.
                (default: :obj:`None`)
            use_smart_selection (bool): Whether to use agent-based
                intelligent workflow selection. When True, uses workflow
                information and LLM to select most relevant workflows. When
                False, falls back to pattern matching. (default: :obj:`True`)

        Returns:
            bool: True if workflow memories were successfully loaded, False
                otherwise.
        """
        try:
            # reset system message to original state before loading
            # this prevents duplicate workflow context on multiple calls
            self.worker.reset_to_original_system_message()

            # determine which selection method to use
            if use_smart_selection:
                # smart selection: use workflow information and agent
                # intelligence
                context_util = self._get_context_utility()
                workflows_metadata = context_util.get_all_workflows_info(
                    session_id
                )

                if not workflows_metadata:
                    logger.info("No workflow files found")
                    return False

                # use agent to select most relevant workflows
                selected_files, selection_method = (
                    self._select_relevant_workflows(
                        workflows_metadata, max_files_to_load, session_id
                    )
                )

                if not selected_files:
                    logger.info(
                        f"No workflows selected "
                        f"(method: {selection_method.value})"
                    )
                    return False

                # log selection method used
                logger.info(
                    f"Workflow selection method: {selection_method.value}"
                )

                # load selected workflows
                loaded_count = self._load_workflow_files(
                    selected_files, max_files_to_load
                )

            else:
                # legacy pattern matching approach
                workflow_files = self._find_workflow_files(pattern, session_id)
                if not workflow_files:
                    return False

                loaded_count = self._load_workflow_files(
                    workflow_files, max_files_to_load
                )

            # report results
            if loaded_count > 0:
                logger.info(
                    f"Successfully loaded {loaded_count} workflow file(s) for "
                    f"{self.description}"
                )
            return loaded_count > 0

        except Exception as e:
            logger.warning(
                f"Error loading workflow memories for {self.description}: "
                f"{e!s}"
            )
            return False

    def save_workflow(
        self, conversation_accumulator: Optional[ChatAgent] = None
    ) -> Dict[str, Any]:
        r"""Save the worker's current workflow memories using agent
        summarization.

        This method generates a workflow summary from the worker agent's
        conversation history and saves it to a markdown file.

        Args:
            conversation_accumulator (Optional[ChatAgent]): Optional
                accumulator agent with collected conversations. If provided,
                uses this instead of the main worker agent.

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Generated workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used
        """
        try:
            # setup context utility and agent
            context_util = self._get_context_utility()
            self.worker.set_context_utility(context_util)

            # prepare workflow summarization components
            structured_prompt = self._prepare_workflow_prompt()

            # check if we should use role_name or let summarize extract
            # task_title
            clean_name = self._get_sanitized_role_name()
            use_role_name_for_filename = clean_name not in {
                'assistant',
                'agent',
                'user',
                'system',
            }

            # if role_name is explicit, use it for filename
            # if role_name is generic, pass none to let summarize use
            # task_title
            filename = (
                self._generate_workflow_filename()
                if use_role_name_for_filename
                else None
            )

            # select agent for summarization
            agent_to_summarize = self.worker
            if conversation_accumulator is not None:
                accumulator_messages, _ = (
                    conversation_accumulator.memory.get_context()
                )
                if accumulator_messages:
                    conversation_accumulator.set_context_utility(context_util)
                    agent_to_summarize = conversation_accumulator
                    logger.info(
                        f"Using conversation accumulator with "
                        f"{len(accumulator_messages)} messages for workflow "
                        f"summary"
                    )

            # generate and save workflow summary
            result = agent_to_summarize.summarize(
                filename=filename,
                summary_prompt=structured_prompt,
                response_format=WorkflowSummary,
            )

            # add worker metadata
            result["worker_description"] = self.description
            return result

        except Exception as e:
            return {
                "status": "error",
                "summary": "",
                "file_path": None,
                "worker_description": self.description,
                "message": f"Failed to save workflow memories: {e!s}",
            }

    async def save_workflow_async(
        self, conversation_accumulator: Optional[ChatAgent] = None
    ) -> Dict[str, Any]:
        r"""Asynchronously save the worker's current workflow memories using
        agent summarization.

        This is the async version of save_workflow() that uses asummarize() for
        non-blocking LLM calls, enabling parallel summarization of multiple
        workers.

        Args:
            conversation_accumulator (Optional[ChatAgent]): Optional
                accumulator agent with collected conversations. If provided,
                uses this instead of the main worker agent.

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Generated workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used
        """
        try:
            # setup context utility and agent
            context_util = self._get_context_utility()
            self.worker.set_context_utility(context_util)

            # prepare workflow summarization components
            structured_prompt = self._prepare_workflow_prompt()

            # select agent for summarization
            agent_to_summarize = self.worker
            if conversation_accumulator is not None:
                accumulator_messages, _ = (
                    conversation_accumulator.memory.get_context()
                )
                if accumulator_messages:
                    conversation_accumulator.set_context_utility(context_util)
                    agent_to_summarize = conversation_accumulator
                    logger.info(
                        f"Using conversation accumulator with "
                        f"{len(accumulator_messages)} messages for workflow "
                        f"summary"
                    )

            # check if we should use role_name or let asummarize extract
            # task_title
            clean_name = self._get_sanitized_role_name()
            use_role_name_for_filename = clean_name not in {
                'assistant',
                'agent',
                'user',
                'system',
            }

            # generate and save workflow summary
            # if role_name is explicit, use it for filename
            # if role_name is generic, pass none to let asummarize use
            # task_title
            filename = (
                self._generate_workflow_filename()
                if use_role_name_for_filename
                else None
            )

            # **KEY CHANGE**: Using asummarize() instead of summarize()
            result = await agent_to_summarize.asummarize(
                filename=filename,
                summary_prompt=structured_prompt,
                response_format=WorkflowSummary,
            )

            # add worker metadata
            result["worker_description"] = self.description
            return result

        except Exception as e:
            return {
                "status": "error",
                "summary": "",
                "file_path": None,
                "worker_description": self.description,
                "message": f"Failed to save workflow memories: {e!s}",
            }

    def _select_relevant_workflows(
        self,
        workflows_metadata: List[Dict[str, Any]],
        max_files: int,
        session_id: Optional[str] = None,
    ) -> tuple[List[str], WorkflowSelectionMethod]:
        r"""Use worker agent to select most relevant workflows.

        This method creates a prompt with all available workflow information
        and uses the worker agent to intelligently select the most relevant
        workflows based on the worker's role and description.

        Args:
            workflows_metadata (List[Dict[str, Any]]): List of workflow
                information dicts (contains title, description, tags,
                file_path).
            max_files (int): Maximum number of workflows to select.
            session_id (Optional[str]): Specific workforce session ID to
                search in for fallback pattern matching. If None, searches
                across all sessions. (default: :obj:`None`)

        Returns:
            tuple[List[str], WorkflowSelectionMethod]: Tuple of (selected
                workflow file paths, selection method used).
        """
        if not workflows_metadata:
            return [], WorkflowSelectionMethod.NONE

        # format workflows for selection
        workflows_str = self._format_workflows_for_selection(
            workflows_metadata
        )

        # create selection prompt
        selection_prompt = (
            f"You are a {self.description}. "
            f"Review the following {len(workflows_metadata)} available "
            f"workflow memories and select the {max_files} most relevant "
            f"ones for your current role. Consider:\n"
            f"1. Task similarity to your role\n"
            f"2. Domain relevance\n"
            f"3. Tool and capability overlap\n\n"
            f"Available workflows:\n{workflows_str}\n\n"
            f"Respond with ONLY the workflow numbers you selected "
            f"(e.g., '1, 3, 5'), separated by commas. "
            f"Select exactly {max_files} workflows."
        )

        try:
            # use worker agent for selection
            from camel.messages import BaseMessage

            selection_msg = BaseMessage.make_user_message(
                role_name="user", content=selection_prompt
            )

            response = self.worker.step(selection_msg)

            # parse response to extract workflow numbers
            numbers_str = response.msgs[0].content
            numbers = re.findall(r'\d+', numbers_str)
            selected_indices = [int(n) - 1 for n in numbers[:max_files]]

            # validate indices and get file paths
            selected_paths = []
            for idx in selected_indices:
                if 0 <= idx < len(workflows_metadata):
                    selected_paths.append(workflows_metadata[idx]['file_path'])
                else:
                    logger.warning(
                        f"Agent selected invalid workflow index {idx + 1}, "
                        f"only {len(workflows_metadata)} workflows available"
                    )

            if selected_paths:
                logger.info(
                    f"Agent selected {len(selected_paths)} workflow(s) for "
                    f"{self.description}"
                )
                return selected_paths, WorkflowSelectionMethod.AGENT_SELECTED

            # agent returned empty results
            logger.warning(
                "Agent selection returned no valid workflows, "
                "falling back to role-based pattern matching"
            )

        except Exception as e:
            logger.warning(
                f"Error during agent selection: {e!s}. "
                f"Falling back to role-based pattern matching"
            )

        finally:
            # clean up selection conversation from memory to prevent
            # pollution. this runs whether selection succeeded, failed,
            # or raised exception
            self.worker.memory.clear()
            if self.worker._system_message is not None:
                self.worker.update_memory(
                    self.worker._system_message, OpenAIBackendRole.SYSTEM
                )

        # fallback: try pattern matching by role_name
        pattern_matched_files = self._find_workflow_files(
            pattern=None, session_id=session_id
        )
        if pattern_matched_files:
            return (
                pattern_matched_files[:max_files],
                WorkflowSelectionMethod.ROLE_NAME_MATCH,
            )

        # last resort: return most recent workflows
        logger.info(
            "No role-matched workflows found, using most recent workflows"
        )
        return (
            [wf['file_path'] for wf in workflows_metadata[:max_files]],
            WorkflowSelectionMethod.MOST_RECENT,
        )

    def _format_workflows_for_selection(
        self, workflows_metadata: List[Dict[str, Any]]
    ) -> str:
        r"""Format workflow information into a readable prompt for selection.

        Args:
            workflows_metadata (List[Dict[str, Any]]): List of workflow
                information dicts (contains title, description, tags,
                file_path).

        Returns:
            str: Formatted string presenting workflows for LLM selection.
        """
        if not workflows_metadata:
            return "No workflows available."

        formatted_lines = []
        for i, workflow in enumerate(workflows_metadata, 1):
            formatted_lines.append(f"\nWorkflow {i}:")
            formatted_lines.append(f"- Title: {workflow.get('title', 'N/A')}")
            formatted_lines.append(
                f"- Description: {workflow.get('description', 'N/A')}"
            )
            tags = workflow.get('tags', [])
            tags_str = ', '.join(tags) if tags else 'No tags'
            formatted_lines.append(f"- Tags: {tags_str}")
            formatted_lines.append(
                f"- File: {workflow.get('file_path', 'N/A')}"
            )

        return '\n'.join(formatted_lines)

    def _find_workflow_files(
        self, pattern: Optional[str], session_id: Optional[str] = None
    ) -> List[str]:
        r"""Find and return sorted workflow files matching the pattern.

        Args:
            pattern (Optional[str]): Custom search pattern for workflow files.
                If None, uses worker role_name to generate pattern.
            session_id (Optional[str]): Specific session ID to search in.
                If None, searches across all sessions.

        Returns:
            List[str]: Sorted list of workflow file paths (empty if
                validation fails).
        """
        # generate filename-safe search pattern from worker role name
        if pattern is None:
            # get sanitized role name
            clean_name = self._get_sanitized_role_name()

            # check if role_name is generic
            generic_names = {'assistant', 'agent', 'user', 'system'}
            if clean_name in generic_names:
                # for generic role names, search for all workflow files
                # since filename is based on task_title
                pattern = "*_workflow*.md"
            else:
                # for explicit role names, search for role-specific files
                pattern = f"{clean_name}_workflow*.md"

        # get the base workforce_workflows directory
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if camel_workdir:
            base_dir = os.path.join(camel_workdir, "workforce_workflows")
        else:
            base_dir = "workforce_workflows"

        # search for workflow files in specified or all session directories
        if session_id:
            search_path = str(Path(base_dir) / session_id / pattern)
        else:
            # search across all session directories using wildcard pattern
            search_path = str(Path(base_dir) / "*" / pattern)
        workflow_files = glob.glob(search_path)

        if not workflow_files:
            logger.info(f"No workflow files found for pattern: {pattern}")
            return []

        # prioritize most recent sessions by session timestamp in
        # directory name
        def extract_session_timestamp(filepath: str) -> str:
            match = re.search(r'session_(\d{8}_\d{6}_\d{6})', filepath)
            return match.group(1) if match else ""

        workflow_files.sort(key=extract_session_timestamp, reverse=True)
        return workflow_files

    def _collect_workflow_contents(
        self, workflow_files: List[str]
    ) -> List[Dict[str, str]]:
        r"""Collect and load workflow file contents.

        Args:
            workflow_files (List[str]): List of workflow file paths to load.

        Returns:
            List[Dict[str, str]]: List of dicts with 'filename' and
                'content' keys.
        """
        workflows_to_load = []
        for file_path in workflow_files:
            try:
                # extract file and session info from full path
                filename = os.path.basename(file_path).replace('.md', '')
                session_dir = os.path.dirname(file_path)
                session_id = os.path.basename(session_dir)

                # create context utility for the specific session
                temp_utility = ContextUtility.get_workforce_shared(session_id)

                # load the workflow content
                content = temp_utility.load_markdown_file(filename)

                if content and content.strip():
                    # filter out metadata section
                    content = temp_utility._filter_metadata_from_content(
                        content
                    )
                    workflows_to_load.append(
                        {'filename': filename, 'content': content}
                    )
                    logger.info(f"Loaded workflow content: {filename}")
                else:
                    logger.warning(
                        f"Workflow file empty or not found: {filename}"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to load workflow file {file_path}: {e!s}"
                )
                continue

        return workflows_to_load

    def _format_workflows_for_context(
        self, workflows_to_load: List[Dict[str, str]]
    ) -> str:
        r"""Format workflows into a context string for the agent.

        Args:
            workflows_to_load (List[Dict[str, str]]): List of workflow
                dicts with 'filename' and 'content' keys.

        Returns:
            str: Formatted workflow context string with header and all
                workflows.
        """
        # create single header for all workflows
        if len(workflows_to_load) == 1:
            prefix_prompt = (
                "The following is the context from a previous "
                "session or workflow which might be useful for "
                "the current task. This information might help you "
                "understand the background, choose which tools to use, "
                "and plan your next steps."
            )
        else:
            prefix_prompt = (
                f"The following are {len(workflows_to_load)} previous "
                "workflows which might be useful for "
                "the current task. These workflows provide context about "
                "similar tasks, tools used, and approaches taken. "
                "Review them to understand patterns and make informed "
                "decisions for your current task."
            )

        # combine all workflows into single content block
        combined_content = f"\n\n--- Previous Workflows ---\n{prefix_prompt}\n"

        for i, workflow_data in enumerate(workflows_to_load, 1):
            combined_content += (
                f"\n\n{'=' * 60}\n"
                f"Workflow {i}: {workflow_data['filename']}\n"
                f"{'=' * 60}\n\n"
                f"{workflow_data['content']}"
            )

        return combined_content

    def _add_workflows_to_system_message(self, workflow_context: str) -> bool:
        r"""Add workflow context to agent's system message.

        Args:
            workflow_context (str): The formatted workflow context to add.

        Returns:
            bool: True if successful, False otherwise.
        """
        # check if agent has a system message
        if self.worker._original_system_message is None:
            logger.error(
                f"Agent {self.worker.agent_id} has no system message. "
                "Cannot append workflow memories."
            )
            return False

        # update the current system message
        current_system_message = self.worker._system_message
        if current_system_message is not None:
            new_sys_content = current_system_message.content + workflow_context
            self.worker._system_message = (
                current_system_message.create_new_instance(new_sys_content)
            )

            # replace the system message in memory
            self.worker.memory.clear()
            self.worker.update_memory(
                self.worker._system_message, OpenAIBackendRole.SYSTEM
            )

        return True

    def _load_workflow_files(
        self, workflow_files: List[str], max_workflows: int
    ) -> int:
        r"""Load workflow files and return count of successful loads.

        Loads all workflows together with a single header to avoid repetition.

        Args:
            workflow_files (List[str]): List of workflow file paths to load.
            max_workflows (int): Maximum number of workflows to load.

        Returns:
            int: Number of successfully loaded workflow files.
        """
        if not workflow_files:
            return 0

        # collect workflow contents from files
        workflows_to_load = self._collect_workflow_contents(
            workflow_files[:max_workflows]
        )

        if not workflows_to_load:
            return 0

        # format workflows into context string
        try:
            workflow_context = self._format_workflows_for_context(
                workflows_to_load
            )

            # add workflow context to agent's system message
            if not self._add_workflows_to_system_message(workflow_context):
                return 0

            char_count = len(workflow_context)
            logger.info(
                f"Appended {len(workflows_to_load)} workflow(s) to agent "
                f"{self.worker.agent_id} ({char_count} characters)"
            )

            return len(workflows_to_load)

        except Exception as e:
            logger.error(
                f"Failed to append workflows to system message: {e!s}"
            )
            return 0

    def _get_sanitized_role_name(self) -> str:
        r"""Get the sanitized role name for the worker.

        Returns:
            str: Sanitized role name suitable for use in filenames.
        """
        role_name = getattr(self.worker, 'role_name', 'assistant')
        return ContextUtility.sanitize_workflow_filename(role_name)

    def _generate_workflow_filename(self) -> str:
        r"""Generate a filename for the workflow based on worker role name.

        Uses the worker's explicit role_name when available.

        Returns:
            str: Sanitized filename without timestamp and without .md
                extension. Format: {role_name}_workflow
        """
        clean_name = self._get_sanitized_role_name()
        return f"{clean_name}_workflow"

    def _prepare_workflow_prompt(self) -> str:
        r"""Prepare the structured prompt for workflow summarization.

        Returns:
            str: Structured prompt for workflow summary.
        """
        workflow_prompt = WorkflowSummary.get_instruction_prompt()
        return StructuredOutputHandler.generate_structured_prompt(
            base_prompt=workflow_prompt, schema=WorkflowSummary
        )
