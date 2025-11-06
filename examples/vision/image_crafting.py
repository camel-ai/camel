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
from camel.agents.chat_agent import ChatAgent
from camel.models import ModelFactory
from camel.prompts import PromptTemplateGenerator
from camel.toolkits import OpenAIImageToolkit
from camel.types import (
    ModelPlatformType,
    ModelType,
    RoleType,
    TaskType,
)


def main():
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.IMAGE_CRAFT, RoleType.ASSISTANT
    )
    print("=" * 20 + " SYS MSG " + "=" * 20)
    print(sys_msg)
    print("=" * 49)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    dalle_agent = ChatAgent(
        system_message=sys_msg,
        model=model,
        tools=OpenAIImageToolkit().get_tools(),
    )

    response = dalle_agent.step("Draw a picture of a camel.")

    print("=" * 20 + " RESULT " + "=" * 20)
    print(response.msg.content)
    print("=" * 48)


if __name__ == "__main__":
    main()

"""
===============================================================================
==================== SYS MSG ====================
You are tasked with creating an original image based on
        the provided descriptive captions. Use your imagination
        and artistic skills to visualize and draw the images and
        explain your thought process.
=================================================
==================== RESULT ====================
I have created an image of a camel standing in a desert oasis under the shade 
of a palm tree. You can see the realistic and detailed drawing of the camel in 
the image below. 

![Camel in a Desert Oasis](img/58a2a3fa-1e7e-407c-8cd6-4b99448b6a90.png) 

The scene captures the essence of the desert environment with the camel 
peacefully resting in the oasis.
===============================================================================
"""
