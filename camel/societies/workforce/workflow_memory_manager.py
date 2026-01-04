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
from camel.societies.workforce.utils import (
    WorkflowConfig,
    WorkflowMetadata,
    is_generic_role_name,
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
        role_identifier (Optional[str]): Role identifier for organizing
            workflows by role. If provided, workflows will be stored in
            role-based folders. If None, uses default workforce context.
        config (Optional[WorkflowConfig]): Configuration for workflow
            management. If None, uses default configuration.
    """

    def __init__(
        self,
        worker: ChatAgent,
        description: str,
        context_utility: Optional[ContextUtility] = None,
        role_identifier: Optional[str] = None,
        config: Optional[WorkflowConfig] = None,
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
        self._role_identifier = role_identifier
        self.config = config if config is not None else WorkflowConfig()

        # mapping of loaded workflow filenames to their full file paths
        # populated when workflows are loaded, used to resolve update targets
        self._loaded_workflow_paths: Dict[str, str] = {}

        # cached loaded workflow contents for reuse in prompt preparation
        # list of dicts with 'filename' and 'content' keys
        self._loaded_workflow_contents: List[Dict[str, str]] = []

    def _get_context_utility(self) -> ContextUtility:
        r"""Get context utility with lazy initialization.

        Uses role-based context if role_identifier is set, otherwise falls
        back to default workforce shared context.
        """
        if self._context_utility is None:
            if self._role_identifier:
                self._context_utility = (
                    ContextUtility.get_workforce_shared_by_role(
                        self._role_identifier
                    )
                )
            else:
                self._context_utility = ContextUtility.get_workforce_shared()
        return self._context_utility

    def _extract_existing_workflow_metadata(
        self, file_path: Path
    ) -> Optional[WorkflowMetadata]:
        r"""Extract metadata from an existing workflow file for versioning.

        This method reads the metadata section from an existing workflow
        markdown file to retrieve version number and creation timestamp,
        enabling proper version tracking when updating workflows.

        Args:
            file_path (Path): Path to the existing workflow file.

        Returns:
            Optional[WorkflowMetadata]: WorkflowMetadata instance if file
                exists and metadata is successfully parsed, None otherwise.
        """
        try:
            # check if parent directory exists first
            if not file_path.parent.exists():
                return None

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # extract metadata section
            metadata_match = re.search(
                r'## Metadata\s*\n(.*?)(?:\n##|$)', content, re.DOTALL
            )

            if not metadata_match:
                return None

            metadata_section = metadata_match.group(1).strip()

            # parse metadata lines (format: "- key: value")
            metadata_dict: Dict[str, Any] = {}
            for line in metadata_section.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    # remove leading "- " and split on first ":"
                    line = line[1:].strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()

                        # convert workflow_version to int
                        if key == 'workflow_version':
                            try:
                                metadata_dict[key] = int(value)
                            except ValueError:
                                metadata_dict[key] = 1
                        # convert message_count to int
                        elif key == 'message_count':
                            try:
                                metadata_dict[key] = int(value)
                            except ValueError:
                                metadata_dict[key] = 0
                        else:
                            metadata_dict[key] = value

            # create WorkflowMetadata instance if we have required fields
            required_fields = {
                'session_id',
                'working_directory',
                'created_at',
                'agent_id',
            }
            if not required_fields.issubset(metadata_dict.keys()):
                logger.warning(
                    f"Existing workflow missing required metadata fields: "
                    f"{file_path}"
                )
                return None

            # ensure we have updated_at and workflow_version
            if 'updated_at' not in metadata_dict:
                metadata_dict['updated_at'] = metadata_dict['created_at']
            if 'workflow_version' not in metadata_dict:
                metadata_dict['workflow_version'] = 1
            if 'message_count' not in metadata_dict:
                metadata_dict['message_count'] = 0

            return WorkflowMetadata(**metadata_dict)

        except Exception as e:
            logger.warning(
                f"Error extracting workflow metadata from {file_path}: {e}"
            )
            return None

    def _try_role_based_loading(
        self,
        role_name: str,
        pattern: Optional[str],
        max_files_to_load: int,
        use_smart_selection: bool,
    ) -> bool:
        r"""Try loading workflows from role-based directory structure.

        Args:
            role_name (str): Role name to load workflows from.
            pattern (Optional[str]): Custom search pattern for workflow files.
            max_files_to_load (int): Maximum number of workflow files to load.
            use_smart_selection (bool): Whether to use agent-based selection.

        Returns:
            bool: True if workflows were successfully loaded, False otherwise.
        """
        logger.info(f"Attempting to load workflows for role: {role_name}")

        loaded = self.load_workflows_by_role(
            role_name=role_name,
            pattern=pattern,
            max_files_to_load=max_files_to_load,
            use_smart_selection=use_smart_selection,
        )

        return loaded

    def _try_session_based_loading(
        self,
        session_id: str,
        role_name: str,
        pattern: Optional[str],
        max_files_to_load: int,
        use_smart_selection: bool,
    ) -> bool:
        r"""Try loading workflows from session-based directory (deprecated).

        Args:
            session_id (str): Workforce session ID to load from.
            role_name (str): Role name (for deprecation warning).
            pattern (Optional[str]): Custom search pattern for workflow files.
            max_files_to_load (int): Maximum number of workflow files to load.
            use_smart_selection (bool): Whether to use agent-based selection.

        Returns:
            bool: True if workflows were successfully loaded, False otherwise.
        """
        import warnings

        warnings.warn(
            f"Session-based workflow loading "
            f"(session_id={session_id}) is deprecated. "
            f"Workflows are now organized by role in "
            f"workforce_workflows/{{role_name}}/ folders. "
            f"No workflows found for role '{role_name}'.",
            FutureWarning,
            stacklevel=2,
        )

        logger.info(
            f"Falling back to session-based loading for "
            f"session_id={session_id}"
        )

        if use_smart_selection:
            return self._session_based_smart_loading(
                session_id, max_files_to_load
            )
        else:
            return self._session_based_pattern_loading(
                pattern, session_id, max_files_to_load
            )

    def _session_based_smart_loading(
        self, session_id: str, max_files_to_load: int
    ) -> bool:
        r"""Load workflows from session using smart selection.

        Args:
            session_id (str): Session ID to load from.
            max_files_to_load (int): Maximum number of files to load.

        Returns:
            bool: True if workflows were loaded, False otherwise.
        """
        context_util = self._get_context_utility()
        workflows_metadata = context_util.get_all_workflows_info(session_id)

        if workflows_metadata:
            selected_files, selection_method = self._select_relevant_workflows(
                workflows_metadata,
                max_files_to_load,
                session_id,
            )

            if selected_files:
                logger.info(
                    f"Workflow selection method: {selection_method.value}"
                )
                loaded_count = self._load_workflow_files(
                    selected_files, max_files_to_load
                )
                return loaded_count > 0

        return False

    def _session_based_pattern_loading(
        self,
        pattern: Optional[str],
        session_id: str,
        max_files_to_load: int,
    ) -> bool:
        r"""Load workflows from session using pattern matching.

        Args:
            pattern (Optional[str]): Pattern for file matching.
            session_id (str): Session ID to load from.
            max_files_to_load (int): Maximum number of files to load.

        Returns:
            bool: True if workflows were loaded, False otherwise.
        """
        workflow_files = self._find_workflow_files(pattern, session_id)
        if workflow_files:
            loaded_count = self._load_workflow_files(
                workflow_files, max_files_to_load
            )
            return loaded_count > 0

        return False

    def load_workflows(
        self,
        pattern: Optional[str] = None,
        max_files_to_load: Optional[int] = None,
        session_id: Optional[str] = None,
        use_smart_selection: bool = True,
    ) -> bool:
        r"""Load workflow memories using intelligent agent-based selection.

        This method first tries to load workflows from the role-based folder
        structure. If no workflows are found and session_id is provided, falls
        back to session-based loading (deprecated).

        Args:
            pattern (Optional[str]): Legacy parameter for backward
                compatibility. When use_smart_selection=False, uses this
                pattern for file matching. Ignored when smart selection
                is enabled.
            max_files_to_load (Optional[int]): Maximum number of workflow files
                to load. If None, uses config.default_max_files_to_load.
                (default: :obj:`None`)
            session_id (Optional[str]): Deprecated. Specific workforce session
                ID to load from using legacy session-based organization.
                (default: :obj:`None`)
            use_smart_selection (bool): Whether to use agent-based
                intelligent workflow selection. When True, uses workflow
                information and LLM to select most relevant workflows. When
                False, falls back to pattern matching. (default: :obj:`True`)

        Returns:
            bool: True if workflow memories were successfully loaded, False
                otherwise. Check logs for detailed error messages.
        """
        try:
            # use config default if not specified
            if max_files_to_load is None:
                max_files_to_load = self.config.default_max_files_to_load

            # reset system message to original state before loading
            # this prevents duplicate workflow context on multiple calls
            self.worker.reset_to_original_system_message()

            # determine role name to use
            role_name = (
                self._role_identifier
                if self._role_identifier
                else self._get_sanitized_role_name()
            )

            # try role-based loading first
            loaded = self._try_role_based_loading(
                role_name, pattern, max_files_to_load, use_smart_selection
            )

            if loaded:
                logger.info(
                    f"Successfully loaded workflows for role '{role_name}'"
                )
                return True

            # fallback to session-based if session_id is provided
            if session_id is not None:
                loaded = self._try_session_based_loading(
                    session_id,
                    role_name,
                    pattern,
                    max_files_to_load,
                    use_smart_selection,
                )
                if loaded:
                    logger.info(
                        f"Successfully loaded workflows from session "
                        f"'{session_id}' (deprecated)"
                    )
                    return True

            logger.info(
                f"No workflow files found for role '{role_name}'. "
                f"This may be expected if no workflows have been saved yet."
            )
            return False

        except Exception as e:
            logger.error(
                f"Error loading workflow memories for "
                f"{self.description}: {e!s}",
                exc_info=True,
            )
            return False

    def load_workflows_by_role(
        self,
        role_name: Optional[str] = None,
        pattern: Optional[str] = None,
        max_files_to_load: Optional[int] = None,
        use_smart_selection: bool = True,
    ) -> bool:
        r"""Load workflow memories from role-based directory structure.

        This method loads workflows from the new role-based folder structure:
        workforce_workflows/{role_name}/*.md

        Args:
            role_name (Optional[str]): Role name to load workflows from. If
                None, uses the worker's role_name or role_identifier.
            pattern (Optional[str]): Custom search pattern for workflow files.
                Ignored when use_smart_selection=True.
            max_files_to_load (Optional[int]): Maximum number of workflow files
                to load. If None, uses config.default_max_files_to_load.
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
            # use config default if not specified
            if max_files_to_load is None:
                max_files_to_load = self.config.default_max_files_to_load

            # reset system message to original state before loading
            self.worker.reset_to_original_system_message()

            # determine role name to use
            if role_name is None:
                role_name = (
                    self._role_identifier or self._get_sanitized_role_name()
                )

            # determine which selection method to use
            if use_smart_selection:
                # smart selection: use workflow information and agent
                # intelligence
                context_util = self._get_context_utility()

                # find workflow files in role-based directory
                workflow_files = self._find_workflow_files_by_role(
                    role_name, pattern
                )

                # get workflow metadata for smart selection
                workflows_metadata = []
                for file_path in workflow_files:
                    metadata = context_util.extract_workflow_info(file_path)
                    if metadata:
                        workflows_metadata.append(metadata)

                if not workflows_metadata:
                    logger.info(
                        f"No workflow files found for role: {role_name}"
                    )
                    return False

                # use agent to select most relevant workflows
                selected_files, selection_method = (
                    self._select_relevant_workflows(
                        workflows_metadata, max_files_to_load
                    )
                )

                if not selected_files:
                    logger.info(
                        f"No workflows selected for role {role_name} "
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
                workflow_files = self._find_workflow_files_by_role(
                    role_name, pattern
                )

                if not workflow_files:
                    logger.info(
                        f"No workflow files found for role: {role_name}"
                    )
                    return False

                loaded_count = self._load_workflow_files(
                    workflow_files, max_files_to_load
                )

            # report results
            if loaded_count > 0:
                logger.info(
                    f"Successfully loaded {loaded_count} workflow file(s) for "
                    f"role {role_name}"
                )
            return loaded_count > 0

        except Exception as e:
            logger.warning(
                f"Error loading workflow memories for role {role_name}: {e!s}"
            )
            return False

    def save_workflow(
        self, conversation_accumulator: Optional[ChatAgent] = None
    ) -> Dict[str, Any]:
        r"""Save the worker's current workflow memories using agent
        summarization.

        This method uses a two-pass approach: first generates the workflow
        summary to determine operation_mode (update vs create), then saves
        to the appropriate file path based on that decision.

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
            # pass 1: generate workflow summary (without saving to disk)
            summary_result = self.generate_workflow_summary(
                conversation_accumulator=conversation_accumulator
            )

            if summary_result["status"] != "success":
                return {
                    "status": "error",
                    "summary": "",
                    "file_path": None,
                    "worker_description": self.description,
                    "message": f"Failed to generate summary: "
                    f"{summary_result['status']}",
                }

            workflow_summary = summary_result["structured_summary"]
            if not workflow_summary:
                return {
                    "status": "error",
                    "summary": "",
                    "file_path": None,
                    "worker_description": self.description,
                    "message": "No structured summary generated",
                }

            # pass 2: save using save_workflow_content which handles
            # operation_mode branching
            context_util = self._get_context_utility()
            result = self.save_workflow_content(
                workflow_summary=workflow_summary,
                context_utility=context_util,
                conversation_accumulator=conversation_accumulator,
            )

            return result

        except Exception as e:
            return {
                "status": "error",
                "summary": "",
                "file_path": None,
                "worker_description": self.description,
                "message": f"Failed to save workflow memories: {e!s}",
            }

    def generate_workflow_summary(
        self,
        conversation_accumulator: Optional[ChatAgent] = None,
    ) -> Dict[str, Any]:
        r"""Generate a workflow summary without saving to disk.

        This method generates a workflow summary by calling a dedicated
        summarizer agent. It does NOT save to disk - only generates the
        summary content and structured output. Use this when you need to
        inspect the summary (e.g., extract operation_mode) before determining
        where to save it.

        Args:
            conversation_accumulator (Optional[ChatAgent]): Optional
                accumulator agent with collected conversations. If provided,
                uses this instead of the main worker agent.

        Returns:
            Dict[str, Any]: Result dictionary with:
                - structured_summary: WorkflowSummary instance or None
                - summary_content: Raw text content
                - status: "success" or error message
        """

        result: Dict[str, Any] = {
            "structured_summary": None,
            "summary_content": "",
            "status": "",
        }

        try:
            # setup context utility
            context_util = self._get_context_utility()
            self.worker.set_context_utility(context_util)

            # prepare workflow summarization prompt
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

            # get conversation from agent's memory
            source_agent = (
                conversation_accumulator
                if conversation_accumulator
                else self.worker
            )
            messages, _ = source_agent.memory.get_context()

            if not messages:
                result["status"] = "No conversation context available"
                return result

            # build conversation text
            conversation_text, _ = (
                agent_to_summarize._build_conversation_text_from_messages(
                    messages, include_summaries=False
                )
            )

            if not conversation_text:
                result["status"] = "Conversation context is empty"
                return result

            # create or reuse summarizer agent
            if agent_to_summarize._context_summary_agent is None:
                agent_to_summarize._context_summary_agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that summarizes "
                        "conversations"
                    ),
                    model=agent_to_summarize.model_backend,
                    agent_id=f"{agent_to_summarize.agent_id}_context_summarizer",
                )
            else:
                agent_to_summarize._context_summary_agent.reset()

            # prepare prompt
            prompt_text = (
                f"{structured_prompt.rstrip()}\n\n"
                f"AGENT CONVERSATION TO BE SUMMARIZED:\n"
                f"{conversation_text}"
            )

            # call summarizer agent with structured output
            response = agent_to_summarize._context_summary_agent.step(
                prompt_text, response_format=WorkflowSummary
            )

            if not response.msgs:
                result["status"] = "Failed to generate summary"
                return result

            summary_content = response.msgs[-1].content.strip()
            structured_output = None
            if response.msgs[-1].parsed:
                structured_output = response.msgs[-1].parsed

            result.update(
                {
                    "structured_summary": structured_output,
                    "summary_content": summary_content,
                    "status": "success",
                }
            )
            return result

        except Exception as exc:
            error_message = f"Failed to generate summary: {exc}"
            logger.error(error_message)
            result["status"] = error_message
            return result

    async def generate_workflow_summary_async(
        self,
        conversation_accumulator: Optional[ChatAgent] = None,
    ) -> Dict[str, Any]:
        r"""Asynchronously generate a workflow summary without saving to disk.

        This is the async version of generate_workflow_summary() that uses
        astep() for non-blocking LLM calls. It does NOT save to disk - only
        generates the summary content and structured output.

        Args:
            conversation_accumulator (Optional[ChatAgent]): Optional
                accumulator agent with collected conversations. If provided,
                uses this instead of the main worker agent.

        Returns:
            Dict[str, Any]: Result dictionary with:
                - structured_summary: WorkflowSummary instance or None
                - summary_content: Raw text content
                - status: "success" or error message
        """
        result: Dict[str, Any] = {
            "structured_summary": None,
            "summary_content": "",
            "status": "",
        }

        try:
            # setup context utility
            context_util = self._get_context_utility()
            self.worker.set_context_utility(context_util)

            # prepare workflow summarization prompt
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

            # get conversation from agent's memory
            source_agent = (
                conversation_accumulator
                if conversation_accumulator
                else self.worker
            )
            messages, _ = source_agent.memory.get_context()

            if not messages:
                result["status"] = "No conversation context available"
                return result

            # build conversation text
            conversation_text, _ = (
                agent_to_summarize._build_conversation_text_from_messages(
                    messages, include_summaries=False
                )
            )

            if not conversation_text:
                result["status"] = "Conversation context is empty"
                return result

            # create or reuse summarizer agent
            if agent_to_summarize._context_summary_agent is None:
                agent_to_summarize._context_summary_agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that summarizes "
                        "conversations"
                    ),
                    model=agent_to_summarize.model_backend,
                    agent_id=f"{agent_to_summarize.agent_id}_context_summarizer",
                )
            else:
                agent_to_summarize._context_summary_agent.reset()

            # prepare prompt
            prompt_text = (
                f"{structured_prompt.rstrip()}\n\n"
                f"AGENT CONVERSATION TO BE SUMMARIZED:\n"
                f"{conversation_text}"
            )

            # call summarizer agent with structured output (async)
            response = await agent_to_summarize._context_summary_agent.astep(
                prompt_text, response_format=WorkflowSummary
            )

            if not response.msgs:
                result["status"] = "Failed to generate summary"
                return result

            summary_content = response.msgs[-1].content.strip()
            structured_output = None
            if response.msgs[-1].parsed:
                structured_output = response.msgs[-1].parsed

            result.update(
                {
                    "structured_summary": structured_output,
                    "summary_content": summary_content,
                    "status": "success",
                }
            )
            return result

        except Exception as exc:
            error_message = f"Failed to generate summary: {exc}"
            logger.error(error_message)
            result["status"] = error_message
            return result

    def save_workflow_content(
        self,
        workflow_summary: 'WorkflowSummary',
        context_utility: Optional[ContextUtility] = None,
        conversation_accumulator: Optional[ChatAgent] = None,
    ) -> Dict[str, Any]:
        r"""Save a pre-generated workflow summary to disk.

        This method takes a pre-generated WorkflowSummary object and saves
        it to disk using the provided context utility. It does NOT call the
        LLM - just formats and saves the content. Use this for two-pass
        workflows where the summary is generated first, then saved to a
        location determined by the summary content.

        Args:
            workflow_summary (WorkflowSummary): Pre-generated workflow summary
                object containing task_title, agent_title, etc.
            context_utility (Optional[ContextUtility]): Context utility with
                correct working directory. If None, uses default.
            conversation_accumulator (Optional[ChatAgent]): An optional agent
                that holds accumulated conversation history. Used to get
                accurate message_count metadata. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Formatted workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used
        """

        def _create_error_result(message: str) -> Dict[str, Any]:
            """helper to create error result dict."""
            return {
                "status": "error",
                "summary": "",
                "file_path": None,
                "worker_description": self.description,
                "message": message,
            }

        try:
            # validate workflow_summary input
            if not workflow_summary:
                return _create_error_result("workflow_summary is required")

            # validate required fields exist
            if not hasattr(workflow_summary, 'task_title'):
                return _create_error_result(
                    "workflow_summary must have task_title field"
                )

            if not hasattr(workflow_summary, 'agent_title'):
                return _create_error_result(
                    "workflow_summary must have agent_title field"
                )

            # validate agent_title is not empty
            agent_title = getattr(workflow_summary, 'agent_title', '').strip()
            if not agent_title:
                return _create_error_result(
                    "workflow_summary.agent_title cannot be empty"
                )

            # use provided context utility or get default
            if context_utility is None:
                context_utility = self._get_context_utility()

            # set context utility on worker
            self.worker.set_context_utility(context_utility)

            # determine file path based on operation mode
            operation_mode = getattr(
                workflow_summary, 'operation_mode', 'create'
            )
            target_filename = getattr(
                workflow_summary, 'target_workflow_filename', None
            )

            # validate operation_mode - default to create for unexpected values
            if operation_mode not in ("create", "update"):
                logger.warning(
                    f"Unexpected operation_mode '{operation_mode}', "
                    "defaulting to 'create'."
                )
                operation_mode = "create"

            if operation_mode == "update":
                # if only one workflow loaded and no target specified,
                # assume agent meant that one
                has_single_workflow = len(self._loaded_workflow_paths) == 1
                if not target_filename and has_single_workflow:
                    target_filename = next(
                        iter(self._loaded_workflow_paths.keys())
                    )
                    logger.info(
                        f"Auto-selecting single loaded workflow: "
                        f"{target_filename}"
                    )

                # validate target filename exists in loaded workflows
                if (
                    target_filename
                    and target_filename in self._loaded_workflow_paths
                ):
                    # use the stored path for the target workflow
                    file_path = Path(
                        self._loaded_workflow_paths[target_filename]
                    )
                    base_filename = target_filename
                    logger.info(f"Updating existing workflow: {file_path}")
                else:
                    # invalid or missing target, fall back to create mode
                    available = list(self._loaded_workflow_paths.keys())
                    logger.warning(
                        f"Invalid target_workflow_filename "
                        f"'{target_filename}', available: {available}. "
                        "Falling back to create mode."
                    )
                    operation_mode = "create"

            if operation_mode == "create":
                # use task_title from summary for filename
                task_title = workflow_summary.task_title
                clean_title = ContextUtility.sanitize_workflow_filename(
                    task_title
                )
                base_filename = (
                    f"{clean_title}{self.config.workflow_filename_suffix}"
                    if clean_title
                    else "workflow"
                )

                file_path = (
                    context_utility.get_working_directory()
                    / f"{base_filename}.md"
                )
                logger.info(f"Creating new workflow: {file_path}")

            # check if workflow file already exists to handle versioning
            existing_metadata = self._extract_existing_workflow_metadata(
                file_path
            )

            # build metadata - get message count from accumulator if available
            source_agent = (
                conversation_accumulator
                if conversation_accumulator
                else self.worker
            )

            # determine version and created_at based on existing metadata
            # only increment version if versioning is enabled
            if self.config.enable_versioning and existing_metadata:
                workflow_version = existing_metadata.workflow_version + 1
                created_at = existing_metadata.created_at
            else:
                workflow_version = 1
                created_at = None

            metadata = context_utility.get_session_metadata(
                workflow_version=workflow_version, created_at=created_at
            )
            metadata.update(
                {
                    "agent_id": self.worker.agent_id,
                    "message_count": len(source_agent.memory.get_context()[0]),
                }
            )

            # convert WorkflowSummary to markdown
            # exclude operation_mode and target_workflow_filename as they're
            # only used for save logic, not persisted in the workflow file
            summary_content = context_utility.structured_output_to_markdown(
                structured_data=workflow_summary,
                metadata=metadata,
                exclude_fields=['operation_mode', 'target_workflow_filename'],
            )

            # save to disk
            save_status = context_utility.save_markdown_file(
                base_filename,
                summary_content,
            )

            # format summary with context prefix
            formatted_summary = (
                f"[CONTEXT_SUMMARY] The following is a summary of our "
                f"conversation from a previous session: {summary_content}"
            )

            status = "success" if save_status == "success" else save_status
            return {
                "status": status,
                "summary": formatted_summary,
                "file_path": str(file_path),
                "worker_description": self.description,
            }

        except Exception as e:
            return _create_error_result(
                f"Failed to save workflow content: {e!s}"
            )

    async def save_workflow_content_async(
        self,
        workflow_summary: 'WorkflowSummary',
        context_utility: Optional[ContextUtility] = None,
        conversation_accumulator: Optional[ChatAgent] = None,
    ) -> Dict[str, Any]:
        r"""Async wrapper for save_workflow_content.

        Delegates to sync version since file I/O operations are synchronous.
        This method exists for API consistency with save_workflow_async().

        Args:
            workflow_summary (WorkflowSummary): Pre-generated workflow summary
                object containing task_title, agent_title, etc.
            context_utility (Optional[ContextUtility]): Context utility with
                correct working directory. If None, uses default.
            conversation_accumulator (Optional[ChatAgent]): An optional agent
                that holds accumulated conversation history. Used to get
                accurate message_count metadata. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Formatted workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used
        """
        return self.save_workflow_content(
            workflow_summary=workflow_summary,
            context_utility=context_utility,
            conversation_accumulator=conversation_accumulator,
        )

    async def save_workflow_async(
        self, conversation_accumulator: Optional[ChatAgent] = None
    ) -> Dict[str, Any]:
        r"""Asynchronously save the worker's current workflow memories using
        agent summarization.

        This is the async version of save_workflow() that uses a two-pass
        approach: first generate the workflow summary (async LLM call), then
        save to disk using the appropriate file path based on operation_mode
        (update vs create).

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
            # pass 1: generate workflow summary (without saving to disk)
            summary_result = await self.generate_workflow_summary_async(
                conversation_accumulator=conversation_accumulator
            )

            if summary_result["status"] != "success":
                return {
                    "status": "error",
                    "summary": "",
                    "file_path": None,
                    "worker_description": self.description,
                    "message": f"Failed to generate summary: "
                    f"{summary_result['status']}",
                }

            workflow_summary = summary_result["structured_summary"]
            if not workflow_summary:
                return {
                    "status": "error",
                    "summary": "",
                    "file_path": None,
                    "worker_description": self.description,
                    "message": "No structured summary generated",
                }

            # pass 2: save using save_workflow_content which handles
            # operation_mode branching (sync - file I/O doesn't need async)
            context_util = self._get_context_utility()
            return self.save_workflow_content(
                workflow_summary=workflow_summary,
                context_utility=context_util,
                conversation_accumulator=conversation_accumulator,
            )

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

        .. note::
            Session-based workflow search will be deprecated in a future
            version. Consider using :meth:`_find_workflow_files_by_role` for
            role-based organization instead.

        Args:
            pattern (Optional[str]): Custom search pattern for workflow files.
                If None, uses worker role_name to generate pattern.
            session_id (Optional[str]): Specific session ID to search in.
                If None, searches across all sessions.

        Returns:
            List[str]: Sorted list of workflow file paths (empty if
                validation fails).
        """
        import warnings

        warnings.warn(
            "Session-based workflow search is deprecated and will be removed "
            "in a future version. Consider using load_workflows_by_role() for "
            "role-based organization instead.",
            FutureWarning,
            stacklevel=2,
        )

        # generate filename-safe search pattern from worker role name
        if pattern is None:
            # get sanitized role name
            clean_name = self._get_sanitized_role_name()

            # check if role_name is generic
            if is_generic_role_name(clean_name):
                # for generic role names, search for all workflow files
                # since filename is based on task_title
                pattern = f"*{self.config.workflow_filename_suffix}*.md"
            else:
                # for explicit role names, search for role-specific files
                pattern = (
                    f"{clean_name}{self.config.workflow_filename_suffix}*.md"
                )

        # get the base workflow directory from config
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if camel_workdir:
            base_dir = os.path.join(
                camel_workdir, self.config.workflow_folder_name
            )
        else:
            base_dir = self.config.workflow_folder_name

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

    def _find_workflow_files_by_role(
        self, role_name: Optional[str] = None, pattern: Optional[str] = None
    ) -> List[str]:
        r"""Find workflow files in role-based directory structure.

        This method searches for workflows in the new role-based folder
        structure: workforce_workflows/{role_name}/*.md

        Args:
            role_name (Optional[str]): Role name to search for. If None,
                uses the worker's role_name or role_identifier.
            pattern (Optional[str]): Custom search pattern for workflow files.
                If None, searches for all workflow files in the role directory.

        Returns:
            List[str]: Sorted list of workflow file paths by modification time
                (most recent first).
        """
        # determine role name to use
        if role_name is None:
            role_name = (
                self._role_identifier or self._get_sanitized_role_name()
            )

        # sanitize role name for filesystem use
        clean_role = ContextUtility.sanitize_workflow_filename(role_name)
        if not clean_role:
            clean_role = "unknown_role"

        # get the base workflow directory from config
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if camel_workdir:
            base_dir = os.path.join(
                camel_workdir, self.config.workflow_folder_name, clean_role
            )
        else:
            base_dir = os.path.join(
                self.config.workflow_folder_name, clean_role
            )

        # use provided pattern or default to all workflow files
        if pattern is None:
            pattern = f"*{self.config.workflow_filename_suffix}*.md"

        # search for workflow files in role directory
        search_path = str(Path(base_dir) / pattern)
        workflow_files = glob.glob(search_path)

        if not workflow_files:
            logger.info(
                f"No workflow files found in role directory: {base_dir}"
            )
            return []

        # sort by file modification time (most recent first)
        workflow_files.sort(key=os.path.getmtime, reverse=True)
        return workflow_files

    def _collect_workflow_contents(
        self, workflow_files: List[str]
    ) -> List[Dict[str, str]]:
        r"""Collect and load workflow file contents.

        Also populates the _loaded_workflow_paths mapping for use during
        workflow save operations (to support update mode).

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
                    # store filename -> full path mapping for update mode
                    self._loaded_workflow_paths[filename] = file_path
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

    def _format_workflow_list(
        self, workflows_to_load: List[Dict[str, str]]
    ) -> str:
        r"""Format a list of workflows into a readable string.

        This is a helper method that formats workflow content without
        adding outer headers/footers. Used by _format_workflows_for_context
        and _prepare_workflow_prompt.

        Args:
            workflows_to_load (List[Dict[str, str]]): List of workflow
                dicts with 'filename' and 'content' keys.

        Returns:
            str: Formatted workflow list string.
        """
        if not workflows_to_load:
            return ""

        formatted_content = ""
        for i, workflow_data in enumerate(workflows_to_load, 1):
            formatted_content += (
                f"\n\n{'=' * 60}\n"
                f"Workflow {i}: {workflow_data['filename']}\n"
                f"{'=' * 60}\n\n"
                f"{workflow_data['content']}"
            )

        return formatted_content

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

        # combine header, formatted workflows, and footer
        combined_content = f"\n\n--- Previous Workflows ---\n{prefix_prompt}"
        combined_content += self._format_workflow_list(workflows_to_load)
        combined_content += "\n\n--- End of Previous Workflows ---\n"

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
        Clears and repopulates the _loaded_workflow_paths mapping.

        Args:
            workflow_files (List[str]): List of workflow file paths to load.
            max_workflows (int): Maximum number of workflows to load.

        Returns:
            int: Number of successfully loaded workflow files.
        """
        if not workflow_files:
            return 0

        # clear previous mapping and cached contents before loading
        self._loaded_workflow_paths.clear()
        self._loaded_workflow_contents.clear()

        # collect workflow contents from files (also populates the mapping)
        workflows_to_load = self._collect_workflow_contents(
            workflow_files[:max_workflows]
        )

        if not workflows_to_load:
            return 0

        # cache loaded contents for reuse in prompt preparation
        self._loaded_workflow_contents = workflows_to_load

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
                extension. Format: {role_name}{workflow_filename_suffix}
        """
        clean_name = self._get_sanitized_role_name()
        return f"{clean_name}{self.config.workflow_filename_suffix}"

    def _prepare_workflow_prompt(self) -> str:
        r"""Prepare the structured prompt for workflow summarization.

        Includes operation mode instructions if workflows were loaded,
        guiding the agent to decide whether to update an existing
        workflow or create a new one.

        Returns:
            str: Structured prompt for workflow summary.
        """
        workflow_prompt = WorkflowSummary.get_instruction_prompt()

        # add operation mode instructions based on loaded workflows
        if self._loaded_workflow_paths:
            loaded_filenames = list(self._loaded_workflow_paths.keys())

            workflow_prompt += (
                "\n\nOPERATION MODE SELECTION:\n"
                "You have previously loaded workflow(s). Review them below "
                "and decide whether to update one or create a new workflow."
                "\n\nDecision rules:\n"
                "- If this task is a continuation, improvement, or refinement "
                "of a loaded workflow → set operation_mode='update' and "
                "target_workflow_filename to that workflow's exact filename\n"
                "- If this is a distinctly different task with different "
                "goals/tools → set operation_mode='create'\n\n"
                "When choosing 'update', select the single most relevant "
                "workflow filename. The updated workflow should incorporate "
                "learnings from this session.\n\n"
                f"Available workflow filenames: {loaded_filenames}"
            )

            # include formatted workflow content for reference
            if self._loaded_workflow_contents:
                workflow_prompt += "\n\n--- Loaded Workflows Reference ---"
                workflow_prompt += self._format_workflow_list(
                    self._loaded_workflow_contents
                )
                workflow_prompt += "\n\n--- End of Loaded Workflows ---"
        else:
            workflow_prompt += (
                "\n\nOPERATION MODE:\n"
                "No workflows were loaded. Set operation_mode='create'."
            )

        return StructuredOutputHandler.generate_structured_prompt(
            base_prompt=workflow_prompt, schema=WorkflowSummary
        )
