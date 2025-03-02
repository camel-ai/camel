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
from camel.agents import ChatAgent

agent = ChatAgent(system_message="You are a helpful assistant.")

# Creating the batch
response = agent.model_backend.current_model._batch_run(messages="batchinput.jsonl")
print(response)

# Example output:
"""
================================================================
Batch(id='batch_67b782b2641c819084d89d7ca8579677',
      completion_window='24h', created_at=1740079794,
      endpoint='/v1/chat/completions',
      input_file_id='file-CrHedFzBLUVWqUZ7tUGaB6',
      object='batch', status='validating', cancelled_at=None,
      cancelling_at=None, completed_at=None, error_file_id=None,
      errors=None, expired_at=None, expires_at=1740166194,
      failed_at=None, finalizing_at=None, in_progress_at=None,
      metadata={'description': 'Batch job'}, output_file_id=None,
      request_counts=BatchRequestCounts(completed=0, failed=0, total=0))
================================================================
"""

# Checking the status of the batch
response_status = agent.model_backend.current_model.check_batch_process_status(
    response
)
print(response_status)

# Example output:
"""
================================================================
{'status': 'in_progress', 'batch': Batch(
    id='batch_67b782b2641c819084d89d7ca8579677',
    completion_window='24h', created_at=1740079794,
    endpoint='/v1/chat/completions',
    input_file_id='file-CrHedFzBLUVWqUZ7tUGaB6',
    object='batch', status='in_progress', cancelled_at=None,
    cancelling_at=None, completed_at=None, error_file_id=None,
    errors=None, expired_at=None, expires_at=1740166194,
    failed_at=None, finalizing_at=None, in_progress_at=1740079795,
    metadata={'description': 'Batch job'}, output_file_id=None,
    request_counts=BatchRequestCounts(completed=0, failed=0, total=2)
)}
================================================================
"""
