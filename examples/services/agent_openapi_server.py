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
    r"""Demonstrates a minimal example of initializing a single agent,
    assigning it a tool from the registry, sending one message, and viewing
    the agent's memory history.

    This example uses the OpenAPI-compatible FastAPI interface for
    `ChatAgentOpenAPIServer` and includes:

    - POST /v1/agents/init: Initializes the agent with a system message and a
      wiki search tool.
    - POST /v1/agents/step: Sends a user message prompting the agent to call
      the tool.
    - GET /v1/agents/history: Retrieves the agent's full conversation history.

    The tool used is `search_wiki`, wrapped with `FunctionTool` and
    retrieved from the `SearchToolkit`.

    Prints the server response at each step.
    """

    from camel.toolkits import FunctionTool, SearchToolkit

    wiki_tool = FunctionTool(SearchToolkit().search_wiki)

    tool_registry = {"search_wiki": [wiki_tool]}

    server = ChatAgentOpenAPIServer(tool_registry=tool_registry)
    client = TestClient(server.get_app())

    r = client.post(
        "/v1/agents/init",
        json={
            "agent_id": "demo",
            "tools_names": ["search_wiki"],
            "system_message": (
                "You are a helpful assistant with access to "
                "a wiki search tool."
            ),
        },
    )
    print("Init response:", r.json())
    """
    Init response:
    {'agent_id': 'demo', 'message': 'Agent initialized.'}
    """

    r = client.post(
        "/v1/agents/step/demo",  #
        json={"input_message": "Search: What is machine learning?"},
    )
    print("Step response:", r.json())

    """
    Step response:
    {'msgs': [{'role_name': 'Assistant',
               'role_type': 'assistant',
               'meta_dict': {},
               'content': 'Machine learning (ML) is a field of study in '
                          'artificial intelligence focused on '
                          'developing statistical algorithms that can '
                          'learn from data and generalize to unseen data, '
                          'allowing them to perform tasks without explicit '
                          'instructions. A notable advancement in this '
                          'area is deep learning, which uses neural '
                          'networks to achieve superior performance over '
                          'traditional machine learning methods. \n\nML is '
                          'applied in various fields such as natural '
                          'language processing, computer vision, speech '
                          'recognition, email filtering, agriculture, and '
                          'medicine. When used to address business '
                          'challenges, it is referred to as predictive '
                          'analytics. The foundations of machine learning '
                          'are built on statistics and mathematical '
                          'optimization methods.',
               'video_bytes': None,
               'image_list': None,
               'image_detail': 'auto',
               'video_detail': 'low',
               'parsed': None}],
    'terminated': False,
    'info': {'id': 'chatcmpl-BW6SV6iEFkVpqcxwJuodhLOSQcmde',
          'usage': {'completion_tokens': 121,
                    'prompt_tokens': 254,
                    'total_tokens': 375,
                    'completion_tokens_details': {
                        'accepted_prediction_tokens': 0,
                        'audio_tokens': 0,
                        'reasoning_tokens': 0,
                        'rejected_prediction_tokens': 0},
                    'prompt_tokens_details': {
                        'audio_tokens': 0,
                        'cached_tokens': 0}},
          'termination_reasons': ['stop'],
          'num_tokens': 201,
          'tool_calls': [{
              'tool_name': 'search_wiki',
              'args': {
                  'entity': 'Machine learning'
              },
              'result': 'Machine learning (ML) is a field of study in '
                        'artificial intelligence concerned with the '
                        'development and study of statistical '
                        'algorithms that can learn from data and '
                        'generalise to unseen data, and thus perform '
                        'tasks without explicit instructions. Within a '
                        'subdiscipline in machine learning, advances in '
                        'the field of deep learning have allowed neural '
                       'networks, a class of statistical algorithms, to '
                        'surpass many previous machine learning '
                        'approaches in performance.\nML finds '
                        'application in many fields, including natural '
                        'language processing, computer vision, speech '
                        'recognition, email filtering, agriculture, and '
                        'medicine. The application of ML to business '
                        'problems is known as predictive analytics.\n'
                        'Statistics and mathematical optimisation '
                        '(mathematical programming) methods comprise '
                        'the foundations of machine learning.',
              'tool_call_id': 'call_lYVcPVKqPNPZi7TsSRRbanZ2'
          }],
    """

    r = client.get("/v1/agents/history/demo")
    print("History:", r.json())

    """
    History:
    [{'role': 'system',
    'content': 'You are a helpful assistant with access to a wiki search '
             'tool.'},
    {'role': 'user',
    'content': 'Search: What is machine learning?'},
    {'role': 'assistant',
    'content': '',
    'tool_calls': [{'id': 'call_lYVcPVKqPNPZi7TsSRRbanZ2',
                  'type': 'function',
                  'function': {'name': 'search_wiki',
                               'arguments': '{"entity": "Machine '
                                            'learning"}'}}]},
    {'role': 'tool',
    'content': 'Machine learning (ML) is a field of study in artificial '
             'intelligence concerned with the development and study of '
             'statistical algorithms that can learn from data and '
             'generalise to unseen data, and thus perform tasks without '
             'explicit instructions. Within a subdiscipline in machine '
             'learning, advances in the field of deep learning have '
             'allowed neural networks, a class of statistical '
             'algorithms, to surpass many previous machine learning '
             'approaches in performance.\nML finds application in many '
             'fields, including natural language processing, computer '
             'vision, speech recognition, email filtering, agriculture, '
             'and medicine. The application of ML to business problems '
             'is known as predictive analytics.\nStatistics and '
             'mathematical optimisation (mathematical programming) '
             'methods comprise the foundations of machine learning.',
    'tool_call_id': 'call_lYVcPVKqPNPZi7TsSRRbanZ2'},
    {'role': 'assistant',
    'content': 'Machine learning (ML) is a field of study in artificial '
             'intelligence focused on developing statistical algorithms '
             'that can learn from data and generalize to unseen data, '
             'allowing them to perform tasks without explicit '
             'instructions. A notable advancement in this area is deep '
             'learning, which uses neural networks to achieve superior '
             'performance over traditional machine learning methods. '
             '\n\nML is applied in various fields such as natural '
             'language processing, computer vision, speech recognition, '
             'email filtering, agriculture, and medicine. When used to '
             'address business challenges, it is referred to as '
             'predictive analytics. The foundations of machine learning '
             'are built on statistics and mathematical optimization '
             'methods.'}]
    """

    # Reset Agent
    r = client.post("/v1/agents/reset/demo")
    print("Reset:", r.json())
    """
    Reset: {'message': 'Agent demo reset.'}
    """

    # Display history again after reset
    r = client.get("/v1/agents/history/demo")
    print("History:", r.json())
    """
    History: [{'role': 'system',
     'content': 'You are a helpful assistant 
     with access to a wiki search tool.'}]
    """


def example_init_and_astep():
    r"""Demonstrates a minimal example of initializing a single agent,
    assigning it a tool from the registry, sending one message, and viewing
    the agent's memory history.

    This example uses the OpenAPI-compatible FastAPI interface for
    `ChatAgentOpenAPIServer` and includes:

    - POST /v1/agents/init: Initializes the agent with a system message and a
      wiki search tool.
    - POST /v1/agents/step: Sends a user message prompting the agent to call
      the tool.
    - GET /v1/agents/history: Retrieves the agent's full conversation history.

    The tool used is `search_wiki`, wrapped with `FunctionTool` and
    retrieved from the `SearchToolkit`.

    Prints the server response at each step.
    """

    from camel.toolkits import FunctionTool, SearchToolkit

    wiki_tool = FunctionTool(SearchToolkit().search_wiki)

    tool_registry = {"search_wiki": [wiki_tool]}

    server = ChatAgentOpenAPIServer(tool_registry=tool_registry)
    client = TestClient(server.get_app())

    r = client.post(
        "/v1/agents/init",
        json={
            "agent_id": "demo",
            "tools_names": ["search_wiki"],
            "system_message": (
                "You are a helpful assistant with access to "
                "a wiki search tool."
            ),
        },
    )
    print("Init response:", r.json())
    # Init response:
    # {'agent_id': 'demo', 'message': 'Agent initialized.'}

    r = client.post(
        "/v1/agents/astep/demo",  #
        json={"input_message": "Search: What is machine learning?"},
    )
    print("Step response (astep):", r.json())

    """
    Step response:
    {'msgs': [{'role_name': 'Assistant',
               'role_type': 'assistant',
               'meta_dict': {},
               'content': 'Machine learning (ML) is a field of study in '
                          'artificial intelligence focused on '
                          'developing statistical algorithms that can '
                          'learn from data and generalize to unseen data, '
                          'allowing them to perform tasks without explicit '
                          'instructions. A notable advancement in this '
                          'area is deep learning, which uses neural '
                          'networks to achieve superior performance over '
                          'traditional machine learning methods. \n\nML is '
                          'applied in various fields such as natural '
                          'language processing, computer vision, speech '
                          'recognition, email filtering, agriculture, and '
                          'medicine. When used to address business '
                          'challenges, it is referred to as predictive '
                          'analytics. The foundations of machine learning '
                          'are built on statistics and mathematical '
                          'optimization methods.',
               'video_bytes': None,
               'image_list': None,
               'image_detail': 'auto',
               'video_detail': 'low',
               'parsed': None}],
    'terminated': False,
    'info': {'id': 'chatcmpl-BW6SV6iEFkVpqcxwJuodhLOSQcmde',
          'usage': {'completion_tokens': 121,
                    'prompt_tokens': 254,
                    'total_tokens': 375,
                    'completion_tokens_details': {
                        'accepted_prediction_tokens': 0,
                        'audio_tokens': 0,
                        'reasoning_tokens': 0,
                        'rejected_prediction_tokens': 0},
                    'prompt_tokens_details': {
                        'audio_tokens': 0,
                        'cached_tokens': 0}},
          'termination_reasons': ['stop'],
          'num_tokens': 201,
          'tool_calls': [{
              'tool_name': 'search_wiki',
              'args': {
                  'entity': 'Machine learning'
              },
              'result': 'Machine learning (ML) is a field of study in '
                        'artificial intelligence concerned with the '
                        'development and study of statistical '
                        'algorithms that can learn from data and '
                        'generalise to unseen data, and thus perform '
                        'tasks without explicit instructions. Within a '
                        'subdiscipline in machine learning, advances in '
                        'the field of deep learning have allowed neural '
                       'networks, a class of statistical algorithms, to '
                        'surpass many previous machine learning '
                        'approaches in performance.\nML finds '
                        'application in many fields, including natural '
                        'language processing, computer vision, speech '
                        'recognition, email filtering, agriculture, and '
                        'medicine. The application of ML to business '
                        'problems is known as predictive analytics.\n'
                        'Statistics and mathematical optimisation '
                        '(mathematical programming) methods comprise '
                        'the foundations of machine learning.',
              'tool_call_id': 'call_lYVcPVKqPNPZi7TsSRRbanZ2'
          }],
    """


def example_listing_and_delete_agents():
    r"""Creates multiple agents, lists them, deletes one, and lists again
    to verify it was removed.
    """
    from fastapi.testclient import TestClient

    from camel.services.agent_openapi_server import ChatAgentOpenAPIServer

    client = TestClient(ChatAgentOpenAPIServer().get_app())

    # Step 1: Create two agents
    for agent_id in ["agent_1", "agent_2"]:
        r = client.post(
            "/v1/agents/init",
            json={
                "agent_id": agent_id,
                "system_message": f"You are {agent_id}, a helpful assistant.",
            },
        )
        print(f"Init {agent_id}:", r.json())

    # Step 2: List current agents
    r = client.get("/v1/agents/list_agent_ids")
    print("Current agents:", r.json())  # Should contain agent_1 and agent_2

    # Step 3: Delete agent_1
    r = client.post("/v1/agents/delete/agent_1")
    print("Reset agent_1:", r.json())

    # Step 4: List agents again
    r = client.get("/v1/agents/list_agent_ids")
    print("Remaining agents:", r.json())  # Should contain only agent_2

    """
    Init agent_1: {'agent_id': 'agent_1', 'message': 'Agent initialized.'}
    Init agent_2: {'agent_id': 'agent_2', 'message': 'Agent initialized.'}
    Current agents: {'agent_ids': ['agent_1', 'agent_2']}
    Reset agent_1: {'message': 'Agent agent_1 reset.'}
    Remaining agents: {'agent_ids': ['agent_1', 'agent_2']}
    """


def example_multi_agent_turns(num_rounds: int = 10):
    r"""Runs a multi-turn debate between two agents using the OpenAPI
    interface.

    The agents are initialized with opposing roles (PRO and CON) on a
    specific topic. Each agent takes turns generating a response and
    sending it as the next message to the opponent.

    Args:
        num_rounds (int): The number of turn-based exchanges in the
            debate. Each round consists of one message per agent.

    API calls used:
    - POST /v1/agents/init: Initializes each agent with a system message
      describing their debate role.
    - POST /v1/agents/step: Sends messages alternately between agents to
      simulate a live debate.

    Prints each round of the debate to stdout.
    """

    client = TestClient(ChatAgentOpenAPIServer().get_app())

    # Debate topic
    topic = "Are multiple agents better than a single agent?"

    # Define agents with topic-aware debate roles
    roles = {
        "pro": (
            f"You are the PRO side in a multi-turn debate on: '{topic}'. "
            "Argue that multiple agents are better than a single agent. "
            "Reply to the opponent directly. Do not repeat introductions. "
            "Be confident and persuasive."
        ),
        "con": (
            f"You are the CON side in a multi-turn debate on: '{topic}'. "
            "Argue that a single agent is better than multiple agents. "
            "Respond directly to your opponent. Avoid repeating intros. "
            "Be sharp, critical, and focused."
        ),
    }

    # Initialize each agent
    for agent_id, system_msg in roles.items():
        client.post(
            "/v1/agents/init",
            json={"agent_id": agent_id, "system_message": system_msg},
        )

    message = "Now start debating on this topic:" + topic
    for i in range(num_rounds):
        speaker = "pro" if i % 2 == 0 else "con"
        receiver = "con" if speaker == "pro" else "pro"

        print(f"\n[{speaker.upper()} → {receiver.upper()}]")
        response = client.post(
            f"/v1/agents/step/{speaker}", json={"input_message": message}
        ).json()
        message = response["msgs"][0]["content"]
        print(message)


if __name__ == "__main__":
    import sys

    example = sys.argv[1] if len(sys.argv) > 1 else "basic_sync"

    if example == "basic_sync":
        # An example showing how to work with a single agent with our API
        example_init_and_step()
    elif example == "basic_async":
        # An example showing how to work with a single agent with our API
        example_init_and_astep()
    elif example == "multiple_agents_list_and_delete":
        # An example showing how to work with a single agent with our API
        example_listing_and_delete_agents()
    elif example == "debate":
        # An example showing how to work with a multiple agents with our API
        # Here we are asking two agents to debate on a topic.
        example_multi_agent_turns()
    else:
        print("Unknown example. Use: basic | debate")
