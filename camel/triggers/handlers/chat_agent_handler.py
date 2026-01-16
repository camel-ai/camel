# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Any, Callable, Optional

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.handlers.trigger_event_handler import TriggerEventHandler
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


class ChatAgentHandler(TriggerEventHandler):
    """Handler that processes trigger events using a ChatAgent.

    This handler converts trigger events into prompts and processes them
    through a ChatAgent for single-agent response generation.

    Args:
        chat_agent (Optional[ChatAgent]): ChatAgent instance for processing.
            If None, a default ChatAgent will be created.
            (default: :obj:`None`)
        default_prompt (Optional[str]): Default prompt template to use.
            The prompt will be combined with event payload information.
            (default: :obj:`None`)
        prompt_factory (Optional[Callable[[TriggerEvent], str]]): Custom
            function to convert events to prompts. If provided, this takes
            precedence over default_prompt. (default: :obj:`None`)
    """

    def __init__(
        self,
        chat_agent: Optional[ChatAgent] = None,
        default_prompt: Optional[str] = None,
        prompt_factory: Optional[Callable[[TriggerEvent], str]] = None,
    ):
        self.default_prompt = default_prompt
        self.prompt_factory = prompt_factory

        if chat_agent is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
            self.chat_agent = ChatAgent(
                system_message=(
                    "You are a helpful assistant that processes trigger "
                    "events and tasks."
                ),
                model=model,
            )
            logger.info("Created default ChatAgent for trigger handling")
        else:
            self.chat_agent = chat_agent

    async def handle(self, event: TriggerEvent) -> Any:
        """Handle trigger event by processing with ChatAgent.

        Args:
            event (TriggerEvent): The trigger event to process.

        Returns:
            str: The response content from the ChatAgent.
        """
        # Use custom prompt factory if provided
        if self.prompt_factory:
            prompt = self.prompt_factory(event)
        elif self.default_prompt:
            prompt = (
                f"{self.default_prompt}\n\n"
                f"Trigger ID: {event.trigger_id}\n"
                f"Event Payload: {event.payload}"
            )
        else:
            prompt = (
                f"Process trigger event from {event.trigger_id}\n"
                f"Payload: {event.payload}"
            )

        # Process with ChatAgent
        response = await self.chat_agent.astep(prompt)
        return response.msg.content

    def set_default_prompt(self, prompt: str) -> None:
        """Set or update the default prompt template.

        Args:
            prompt (str): The prompt template to use.
        """
        self.default_prompt = prompt
        logger.info("Updated default prompt for ChatAgent processing")
