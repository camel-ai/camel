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
import os
import time
from typing import Any, Dict, List, Optional, Union

from camel.configs import BEDROCK_API_PARAMS, BedrockConfig
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
    dependencies_required,
)


class AWSBedrockModel(BaseModelBackend):
    r"""AWS Bedrock API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`BedrockConfig().as_dict()` will be used.
            (default: :obj:`None`)
        secret_access_key (Optional[str], optional): The secret access key for
            authenticating with the AWS Bedrock service. (default: :obj:`None`)
        access_key_id (Optional[str], optional): The access key ID for
            authenticating with the AWS Bedrock service. (default: :obj:`None`)
        api_key (Optional[str], optional): This parameter is not used.
        url (Optional[str], optional): This parameter is not used.
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        region_name (Optional[str], optional): The region name for the AWS
            Bedrock service. (default: :obj:`"eu-west-2"`)

    References:
        https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html
    """

    @dependencies_required('boto3')
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        secret_access_key: Optional[str] = None,
        access_key_id: Optional[str] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        region_name: Optional[str] = "eu-west-2",
    ) -> None:
        import boto3

        if model_config_dict is None:
            self.model_config_dict = BedrockConfig().as_dict()
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        secret_access_key = secret_access_key or os.environ.get(
            "AWS_SECRET_ACCESS_KEY"
        )
        access_key_id = access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        self.model_config_dict.setdefault('max_tokens', 400)
        self.toolconfig = {}
        self.model_config = {}
        self.model_config['maxTokens'] = self.model_config_dict.get(
            'max_tokens', 400
        )
        self.model_config['topP'] = self.model_config_dict.get('top_p', 0.7)

        tool_choice = self.model_config_dict.get('tool_choice', None)
        if tool_choice is not None:
            self.toolconfig['toolChoice'] = tool_choice
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Token counter for the model."""
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    @api_keys_required("AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID")
    def run(self, messages: List[OpenAIMessage]) -> ChatCompletion:
        r"""Runs the query to the backend model.

        Args:
            message (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion: The response object in OpenAI's format.
        """
        try:
            system_messages = [
                msg for msg in messages if msg["role"] == "system"
            ]
            messages = [msg for msg in messages if msg["role"] != "system"]
            system_prompt = (
                [{"text": system_messages[0]["content"]}]
                if system_messages
                else None
            )
            tools = self.model_config_dict.get('tools', None)
            if tools is not None:
                self.toolconfig['tools'] = self.transform_tool(tools)
            request_params = {
                'modelId': self.model_type,
                'messages': self._to_aws_bedrock_msg(messages),
                'inferenceConfig': self.model_config,
            }
            if system_prompt:
                request_params['system'] = system_prompt
            if self.toolconfig:
                request_params['toolConfig'] = self.toolconfig
            if 'top_k' in self.model_config_dict:
                request_params['additionalModelRequestFields'] = {
                    'top_k': self.model_config_dict['top_k'],
                }
            response = self.client.converse(**request_params)
            return self._to_openai_response(response)
        except Exception as e:
            raise ValueError(f"Error in AWS Bedrock API: {e}")

    def _to_aws_bedrock_msg(
        self, message: List[OpenAIMessage]
    ) -> List[Dict[str, Any]]:
        r"""Converts a message from OpenAI format to the AWS Bedrock format.

        Args:
            message (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            List[Dict[str, Any]]: Message list with the chat history in AWS
                Bedrock API format.
        """
        bedrock_messages = []
        for msg in message:
            if msg["role"] not in ['assistant', 'user']:
                raise ValueError(f"Invalid role '{msg['role']}' in message.")
            role = 'assistant' if msg["role"] == 'assistant' else 'user'
            bedrock_messages.append(
                {
                    "role": role,
                    "content": [{"text": msg["content"]}],
                }
            )
        return bedrock_messages

    def _to_openai_response(self, response: Dict) -> ChatCompletion:
        r"""Converts a response from the AWS Bedrock format to the OpenAI
            format.

        Args:
            response (Dict[str, Any]): The response object from AWS Bedrock.

        Returns:
            ChatCompletion: The response object in OpenAI's format.
        """
        return ChatCompletion.construct(
            id=response["ResponseMetadata"]["RequestId"],
            object='chat.completion',
            created=int(time.time()),
            model=self.model_type,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": response['output']['message']['role'],
                        "content": response['output']['message']['content'][0][
                            'text'
                        ],
                    },
                    "finish_reason": response['stopReason'],
                }
            ],
            usage={
                'prompt_tokens': response['usage']['inputTokens'],
                'completion_tokens': response['usage']['outputTokens'],
                'total_tokens': response['usage']['totalTokens'],
            },
        )

    def transform_tool(self, tools: List) -> List:
        r"""Transforms a tool name to the AWS Bedrock format.

        Args:
            tools (List): List of tools.

        Returns:
            List: List of tools in the AWS Bedrock format.
        """
        transform_tools = []
        for tool in tools:
            tool_func = tool["function"]
            tool_func_params = tool_func["parameters"]

            transform_tools.append(
                {
                    "toolSpec": {
                        "name": tool_func["name"],
                        "description": tool_func["description"],
                        "inputSchema": {
                            "json": {
                                "type": tool_func_params["type"],
                                "properties": tool_func_params["properties"],
                                "required": tool_func_params["required"],
                            }
                        },
                    }
                }
            )
        return transform_tools

    def check_model_config(self):
        r"""Check whether the input model configuration contains unexpected
        arguments.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected argument for this model class.
        """
        for param in self.model_config_dict:
            if param not in BEDROCK_API_PARAMS:
                raise ValueError(
                    f"Invalid parameter '{param}' in model_config_dict. "
                    f"Valid parameters are: {BEDROCK_API_PARAMS}"
                )
