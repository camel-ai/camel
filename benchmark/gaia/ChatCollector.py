# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
from collections import defaultdict
from typing import Any, Dict, List

import openai


class ChatCollector:
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.original_chat_completion = openai.ChatCompletion.create

    def inject(self):
        def interceptor(*args, **kwargs):
            conversation_id = kwargs.get('conversation_id', 'default')

            # Collect user message
            if 'messages' in kwargs:
                for message in kwargs['messages']:
                    self.conversations[conversation_id].append(
                        {
                            'role': message['role'],
                            'content': message['content'],
                        }
                    )

            # Call the original function
            response = self.original_chat_completion(*args, **kwargs)

            # Collect assistant message
            self.conversations[conversation_id].append(
                {
                    'role': 'assistant',
                    'content': response.choices[0].message.content,
                }
            )

            # Collect tool calls and results if any
            if hasattr(response.choices[0].message, 'function_call'):
                self.conversations[conversation_id].append(
                    {
                        'role': 'assistant',
                        'function_call': response.choices[
                            0
                        ].message.function_call,
                    }
                )

            if 'function_call' in kwargs:
                self.conversations[conversation_id].append(
                    {
                        'role': 'function',
                        'name': kwargs['function_call']['name'],
                        'content': kwargs['function_call']['arguments'],
                    }
                )

            return response

        openai.ChatCompletion.create = interceptor

    def get_conversation(
        self, conversation_id: str = 'default'
    ) -> List[Dict[str, Any]]:
        return self.conversations[conversation_id]

    def get_all_conversations(self) -> Dict[str, List[Dict[str, Any]]]:
        return dict(self.conversations)

    def to_json(self, conversation_id: str = None) -> str:
        if conversation_id:
            return json.dumps(self.get_conversation(conversation_id), indent=2)
        else:
            return json.dumps(self.get_all_conversations(), indent=2)
