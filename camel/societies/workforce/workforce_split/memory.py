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

from typing import Dict, List

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.memories.records import MemoryRecord
from camel.societies.workforce.single_agent_worker import SingleAgentWorker

logger = get_logger(__name__)


class SharedMemoryManager:
    r"""A class to manage shared memory operations across agents in a
    workforce.

    This class provides functionality to collect, share, and synchronize memory
    across coordinator agents, task agents, and worker agents.
    """

    def __init__(self):
        r"""Initialize the SharedMemoryManager."""
        pass

    def collect_shared_memory(
        self,
        coordinator_agent: ChatAgent,
        task_agent: ChatAgent,
        children: List,
        share_memory: bool = False,
    ) -> Dict[str, List]:
        r"""Collect memory from all SingleAgentWorker instances for sharing.

        Args:
            coordinator_agent (ChatAgent): The coordinator agent.
            task_agent (ChatAgent): The task agent.
            children (List): List of child workers.
            share_memory (bool, optional): Whether to share memory.
                (default: :obj:`False`)

        Returns:
            Dict[str, List]: A dictionary mapping agent types to their memory
                records. Contains entries for 'coordinator', 'task_agent',
                and 'workers'.
        """
        # TODO: add memory collection for RolePlayingWorker and nested
        # Workforce instances
        if not share_memory:
            return {}

        shared_memory: Dict[str, List] = {
            'coordinator': [],
            'task_agent': [],
            'workers': [],
        }

        try:
            # Collect coordinator agent memory
            coord_records = coordinator_agent.memory.retrieve()
            shared_memory['coordinator'] = [
                record.memory_record.to_dict() for record in coord_records
            ]

            # Collect task agent memory
            task_records = task_agent.memory.retrieve()
            shared_memory['task_agent'] = [
                record.memory_record.to_dict() for record in task_records
            ]

            # Collect worker memory only from SingleAgentWorker instances
            for child in children:
                if isinstance(child, SingleAgentWorker):
                    worker_records = child.worker.memory.retrieve()
                    worker_memory = [
                        record.memory_record.to_dict()
                        for record in worker_records
                    ]
                    shared_memory['workers'].extend(worker_memory)

        except Exception as e:
            logger.warning(f"Error collecting shared memory: {e}")

        return shared_memory

    def share_memory_with_agents(
        self,
        shared_memory: Dict[str, List],
        coordinator_agent: ChatAgent,
        task_agent: ChatAgent,
        children: List,
        share_memory: bool = False,
    ) -> None:
        r"""Share collected memory with coordinator, task agent, and
        SingleAgentWorker instances.

        Args:
            shared_memory (Dict[str, List]): Memory records collected from
                all agents to be shared.
            coordinator_agent (ChatAgent): The coordinator agent.
            task_agent (ChatAgent): The task agent.
            children (List): List of child workers.
            share_memory (bool, optional): Whether to share memory.
                (default: :obj:`False`)
        """
        if not share_memory or not shared_memory:
            return

        try:
            # Create a consolidated memory from all collected records
            all_records = []
            for _memory_type, records in shared_memory.items():
                all_records.extend(records)

            if not all_records:
                return

            # Create consolidated memory objects from records
            memory_records: List[MemoryRecord] = []
            for record_dict in all_records:
                try:
                    memory_record = MemoryRecord.from_dict(record_dict)
                    memory_records.append(memory_record)
                except Exception as e:
                    logger.warning(f"Failed to reconstruct memory record: {e}")
                    continue

            if not memory_records:
                logger.warning(
                    "No valid memory records could be reconstructed "
                    "for sharing"
                )
                return

            # Share with coordinator agent
            for record in memory_records:
                # Only add records from other agents to avoid duplication
                if record.agent_id != coordinator_agent.agent_id:
                    coordinator_agent.memory.write_record(record)

            # Share with task agent
            for record in memory_records:
                if record.agent_id != task_agent.agent_id:
                    task_agent.memory.write_record(record)

            # Share with SingleAgentWorker instances only
            single_agent_workers = [
                child
                for child in children
                if isinstance(child, SingleAgentWorker)
            ]

            for worker in single_agent_workers:
                for record in memory_records:
                    if record.agent_id != worker.worker.agent_id:
                        worker.worker.memory.write_record(record)

            logger.info(
                f"Shared {len(memory_records)} memory records across "
                f"{len(single_agent_workers) + 2} agents"
            )

        except Exception as e:
            logger.warning(f"Error sharing memory with agents: {e}")

    def sync_shared_memory(
        self,
        coordinator_agent: ChatAgent,
        task_agent: ChatAgent,
        children: List,
        share_memory: bool = False,
    ) -> None:
        r"""Synchronize memory across all agents by collecting and sharing.

        Args:
            coordinator_agent (ChatAgent): The coordinator agent.
            task_agent (ChatAgent): The task agent.
            children (List): List of child workers.
            share_memory (bool, optional): Whether to share memory.
                (default: :obj:`False`)
        """
        if not share_memory:
            return

        try:
            shared_memory = self.collect_shared_memory(
                coordinator_agent, task_agent, children, share_memory
            )
            self.share_memory_with_agents(
                shared_memory,
                coordinator_agent,
                task_agent,
                children,
                share_memory,
            )
        except Exception as e:
            logger.warning(f"Error synchronizing shared memory: {e}")
