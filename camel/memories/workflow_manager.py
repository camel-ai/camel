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

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from camel.agents import ChatAgent

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.tasks.task import Task, TaskState
from camel.toolkits.note_taking_toolkit import NoteTakingToolkit

logger = get_logger(__name__)


class WorkflowRecorder:
    r"""A recorder for storing and retrieving agent workflows in markdown
    format.

    This class provides functionality to:
    1. Record detailed workflows from task execution with agent summarization
    2. Provide hierarchical tree view of workflows for agent selection
    3. Store workflows as human-readable markdown files
    4. Simple file-based workflow retrieval

    Args:
        working_directory (str, optional): Directory for storing workflow
            files. If not provided, uses CAMEL_WORKDIR environment variable
            or defaults to "camel_working_dir".
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
    ) -> None:
        # initialize note taking toolkit for markdown file operations
        self.note_toolkit = NoteTakingToolkit(
            working_directory=working_directory
        )

        logger.info(
            f"WorkflowRecorder initialized with working directory: "
            f"{self.note_toolkit.working_directory}"
        )

    async def record_workflow_from_task(
        self,
        task: Task,
        agent: 'ChatAgent',
        agent_role: str = "Agent",
        agent_id: Optional[str] = None,
    ) -> str:
        r"""Record a workflow from a completed task using agent summarization.

        Args:
            task (Task): The completed task to record workflow from.
            agent (ChatAgent): The agent that executed the task, used for
                generating workflow summary.
            agent_role (str): The role/description of the agent for context.
            agent_id (str, optional): ID of the agent that executed the task.

        Returns:
            str: The name of the created workflow file, or empty string if
                failed.
        """
        try:
            # determine status
            status = "Success" if task.state == TaskState.DONE else "Failure"

            # get workflow summary from agent
            workflow_summary = await self._get_agent_workflow_summary(
                agent, task, agent_role, status
            )

            if not workflow_summary:
                logger.warning(
                    "Failed to generate workflow summary, skipping recording"
                )
                return ""

            # prepare metadata
            metadata = {
                'agent_id': agent_id or 'Unknown',
                'task_id': task.id,
                'timestamp': time.time(),
                'status': status,
            }

            # format as markdown using agent-generated content
            markdown_content = self._format_agent_workflow_markdown(
                workflow_summary, metadata, task
            )

            # create readable filename based on workflow name
            workflow_name = workflow_summary.get(
                'workflow_name', 'unnamed_workflow'
            )
            # sanitize workflow name for filename
            safe_name = "".join(
                c
                for c in workflow_name.lower()
                if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            safe_name = safe_name.replace(' ', '_')[:50]  # limit length
            if not safe_name:
                safe_name = 'unnamed_workflow'
            filename = f"workflow_{safe_name}"

            # save to file using note toolkit
            self.note_toolkit.create_note(filename, markdown_content)

            logger.info(f"Workflow recorded: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error recording workflow: {e}")
            return ""

    async def _get_agent_workflow_summary(
        self, agent: 'ChatAgent', task: Task, agent_role: str, status: str
    ) -> Optional[Dict[str, Any]]:
        r"""Get workflow summary from the agent that executed the task.

        Args:
            agent (ChatAgent): The agent to ask for the summary.
            task (Task): The completed task.
            agent_role (str): Role/description of the agent.
            status (str): Task completion status.

        Returns:
            Dict[str, Any]: Workflow summary from the agent, or None if failed.
        """
        try:
            import json

            from camel.societies.workforce.prompts import (
                WORKFLOW_SUMMARIZATION_PROMPT,
            )

            # format the prompt with task details
            prompt_content = WORKFLOW_SUMMARIZATION_PROMPT.format(
                task_content=task.content,
                task_result=task.result or "No result available",
                task_status=status,
                agent_role=agent_role,
            )

            # create message to send to agent
            summary_message = BaseMessage.make_user_message(
                role_name="WorkflowRecorder", content=prompt_content
            )

            # get response from agent
            response = agent.step(summary_message)

            if response and response.msg:
                try:
                    # parse the JSON response
                    workflow_data = json.loads(response.msg.content)

                    # validate required fields
                    required_fields = [
                        'workflow_name',
                        'description',
                        'steps',
                        'key_findings',
                    ]
                    if all(
                        field in workflow_data for field in required_fields
                    ):
                        return workflow_data
                    else:
                        logger.warning(
                            f"Agent response missing required fields: "
                            f"{workflow_data}"
                        )
                        return None

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse agent workflow summary JSON: {e}"
                    )
                    logger.debug(
                        f"Agent response content: {response.msg.content}"
                    )
                    return None

            logger.warning(
                "Agent did not provide a valid workflow summary response"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting agent workflow summary: {e}")
            return None

    def get_workflows_tree(self) -> str:
        r"""Generate a hierarchical ASCII tree view of all workflows.

        Returns:
            str: ASCII tree showing workflows and their step structure.
        """
        try:
            # get all workflow files
            workflows_list = self.note_toolkit.list_note()

            if "No notes have been created yet." in workflows_list:
                return (
                    "Workflows Directory\n"
                    "└── (empty - no workflows recorded yet)"
                )

            # parse workflow filenames
            workflow_files = []
            for line in workflows_list.split('\n'):
                if 'workflow_' in line and '.md' in line:
                    # extract filename (remove size info and formatting)
                    filename = line.split('.md')[0].split('- ')[-1].strip()
                    if filename.startswith('workflow_'):
                        workflow_files.append(filename)

            if not workflow_files:
                return (
                    "Workflows Directory\n"
                    "└── (empty - no workflows recorded yet)"
                )

            tree = "Workflows Directory\n"

            for i, filename in enumerate(workflow_files):
                is_last = i == len(workflow_files) - 1
                prefix = "└──" if is_last else "├──"

                # get workflow details
                workflow_info = self._extract_workflow_info(filename)
                workflow_name = workflow_info.get('name', 'Unknown Workflow')
                steps = workflow_info.get('steps', [])

                tree += f"{prefix} {workflow_name}\n"
                tree += (
                    f"    {'   ' if is_last else '│  '} File: {filename}.md\n"
                )

                # add step structure
                for j, step in enumerate(steps):
                    step_is_last = j == len(steps) - 1
                    step_prefix = "└──" if step_is_last else "├──"
                    step_connector = "    " if is_last else "│   "
                    tree += f"{step_connector}{step_prefix} {step}\n"

            return tree

        except Exception as e:
            logger.error(f"Error generating workflows tree: {e}")
            return f"Workflows Directory\n└── Error reading workflows: {e}"

    def _extract_workflow_info(self, filename: str) -> Dict[str, Any]:
        r"""Extract workflow name and step names from a workflow file.

        Args:
            filename (str): The workflow filename (without .md extension).

        Returns:
            Dict[str, Any]: Dictionary with workflow name and list of step
                names.
        """
        try:
            content = self.note_toolkit.read_note(filename)

            if not content or "Error" in content:
                return {'name': 'Unknown Workflow', 'steps': []}

            # extract workflow name from first line
            lines = content.split('\n')
            workflow_name = 'Unknown Workflow'
            steps = []

            for line in lines:
                line = line.strip()

                # find workflow name
                if line.startswith('# Workflow:'):
                    workflow_name = line.replace('# Workflow:', '').strip()

                # find step names
                elif line.startswith('### Step '):
                    # extract step name after "Step N: "
                    if ':' in line:
                        step_name = line.split(':', 1)[1].strip()
                        steps.append(step_name)

            return {'name': workflow_name, 'steps': steps}

        except Exception as e:
            logger.error(
                f"Error extracting workflow info from {filename}: {e}"
            )
            return {'name': 'Unknown Workflow', 'steps': []}

    def _format_agent_workflow_markdown(
        self,
        workflow_summary: Dict[str, Any],
        metadata: Dict[str, Any],
        task: Task,
    ) -> str:
        r"""Format agent-generated workflow summary into markdown.

        Args:
            workflow_summary (Dict[str, Any]): Workflow summary from agent.
            metadata (Dict[str, Any]): Task metadata.
            task (Task): Original task.

        Returns:
            str: Formatted markdown content.
        """
        workflow_name = workflow_summary.get(
            'workflow_name', 'Unknown Workflow'
        )
        description = workflow_summary.get(
            'description', 'No description provided'
        )
        steps = workflow_summary.get('steps', [])
        key_findings = workflow_summary.get(
            'key_findings', 'No key findings provided'
        )

        # format timestamp
        timestamp = metadata.get('timestamp', time.time())
        if isinstance(timestamp, (int, float)):
            formatted_time = datetime.fromtimestamp(timestamp).strftime(
                '%Y-%m-%d %H:%M:%S'
            )
        else:
            formatted_time = str(timestamp)

        # build markdown content
        markdown_content = f"""# Workflow: {workflow_name}

## General Description
{description}

## Metadata
- **Agent ID**: {metadata.get('agent_id', 'Unknown')}
- **Task ID**: {metadata.get('task_id', 'Unknown')}
- **Timestamp**: {formatted_time}
- **Status**: {metadata.get('status', 'Unknown')}

## Trajectory
"""

        # add agent-generated steps
        for i, step in enumerate(steps, 1):
            step_name = step.get('name', f'Step {i}')
            observation = step.get('observation', 'No observation recorded')
            actions = step.get('actions', 'No actions recorded')
            reasoning = step.get('reasoning', 'No reasoning recorded')
            markdown_content += f"""
### Step {i}: {step_name}
**Environment**: {observation}
**Actions**: {actions}
**Reasoning**: {reasoning}
"""

        # add results and findings
        task_result = task.result or 'No result recorded'
        markdown_content += f"""
## Results
{task_result}

## Key Findings
{key_findings}
"""

        return markdown_content

    def list_workflows(self) -> str:
        r"""List all stored workflow files.

        Returns:
            str: List of workflow files.
        """
        return self.note_toolkit.list_note()

    def read_workflow(self, workflow_name: str) -> str:
        r"""Read a specific workflow file.

        Args:
            workflow_name (str): Name of the workflow file (without .md
                extension).

        Returns:
            str: Content of the workflow file.
        """
        return self.note_toolkit.read_note(workflow_name)

    def clear_workflows(self) -> None:
        r"""Clear all stored workflows."""
        try:
            # Note: This just lists workflows for information
            # Actual clearing would need to be done manually or through
            # specific file operations since NoteTakingToolkit doesn't
            # provide a bulk delete method
            workflows_list = self.note_toolkit.list_note()
            logger.info(f"Current workflows: {workflows_list}")
            logger.warning(
                "Manual workflow file deletion required - NoteTakingToolkit "
                "doesn't support bulk delete"
            )

        except Exception as e:
            logger.error(f"Error listing workflows for clearing: {e}")
