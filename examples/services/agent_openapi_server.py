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
from fastapi.testclient import TestClient

from camel.services.agent_openapi_server import ChatAgentOpenAPIServer


def example_init_and_step():
    client = TestClient(ChatAgentOpenAPIServer().get_app())

    # Initialize agent
    r = client.post("/v1/init", json={"agent_id": "demo"})
    print("Init response:", r.json())
    # Example output:
    # Init response: {'agent_id': 'demo', 'message': 'Agent initialized.'}

    # Send one message
    r = client.post("/v1/step/demo", json={"input_message": "Hello"})
    print("Step response:", r.json())
    # Example output:
    # Step response: {
    #     'msgs': [{
    #         'role_name': 'assistant',
    #         'role_type': 'assistant',
    #         'meta_dict': {},
    #         'content': 'Hello! How can I assist you today?',
    #         'video_bytes': None,
    #         'image_list': None,
    #         'image_detail': 'auto',
    #         'video_detail': 'low',
    #         'parsed': None
    #     }],
    #     'terminated': False,
    #     'info': {
    #         'id': 'chatcmpl-BVX5f4zWco0PRvi6IOzS5Oo41ZT0x',
    #         'usage': {
    #             'completion_tokens': 10,
    #             'prompt_tokens': 8,
    #             'total_tokens': 18,
    #             'completion_tokens_details': {
    #                 'accepted_prediction_tokens': 0,
    #                 'audio_tokens': 0,
    #                 'reasoning_tokens': 0,
    #                 'rejected_prediction_tokens': 0
    #             },
    #             'prompt_tokens_details': {
    #                 'audio_tokens': 0,
    #                 'cached_tokens': 0
    #             }
    #         },
    #         'termination_reasons': ['stop'],
    #         'num_tokens': 8,
    #         'tool_calls': [],
    #         'external_tool_call_requests': None
    #     }
    # }

    # View history
    r = client.get("/v1/history/demo")
    print("History:", r.json())
    # Example output:
    # History: [{'role': 'user', 'content': 'Hello'},
    #   {'role': 'assistant', 'content': 'Hello! How can I assist you today?'}]


if __name__ == "__main__":
    import sys

    example = sys.argv[1] if len(sys.argv) > 1 else "basic"

    if example == "basic":
        example_init_and_step()
    # elif example == "debate":
    #     example_multi_agent_turns()
    else:
        print("Unknown example. Use: basic | debate")
