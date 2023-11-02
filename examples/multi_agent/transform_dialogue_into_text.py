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

from colorama import Fore

from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig
from camel.typing import ModelType


def main(model_type=ModelType.GPT_3_5_TURBO_16K) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    # Possible categories: "ASSISTANCE", "ANALYSIS", "AUXILIARY",
    # "NON-SUBSTANTIAL"
    dialogue_examples = {
        "birthday_cake_order": {
            "user":
            "Customer",
            "assistant":
            "Bakery Assistant",
            "task_prompt":
            ("Help a customer order a customized birthday cake for their "
             "child."),
            "user_conversation":
            ("I need a birthday cake for my son's 5th birthday. "
             "He loves dinosaurs. Can you suggest something special?"),
            "assistant_conversation":
            ("Absolutely! For your son's dinosaur-themed birthday, "
             "we could create a 3D cake shaped like a T-Rex, complete "
             "with edible jungle decorations and a chocolate lava "
             "volcano. We can also include his name and age in a fun, "
             "prehistoric font. Does that sound exciting to you?"),
            "categories": ["ASSISTANCE", "AUXILIARY"]
        },
        "novel_analysis": {
            "user":
            "Literature Student",
            "assistant":
            "Literature Professor",
            "task_prompt":
            ("Provide an analysis of the novel '1984' by George Orwell."),
            "user_conversation":
            ("I'm struggling to understand the main themes in '1984'. "
             "Can you help me analyze them?"),
            "assistant_conversation":
            ("Certainly! '1984' primarily explores themes of "
             "totalitarianism, surveillance, and the manipulation of "
             "truth. Orwell critiques oppressive government control and "
             "the erosion of individual freedom. The omnipresent Big "
             "Brother symbolizes constant surveillance, while Newspeak "
             "and the alteration of past events reflect the manipulation "
             "of reality and history. It's a profound warning about the "
             "dangers of unchecked political power."),
            "categories": ["ANALYSIS", "ASSISTANCE"]
        },
        "weekend_trip_planning": {
            "user":
            "Travel Enthusiast",
            "assistant":
            "Travel Advisor",
            "task_prompt":
            "Assist in planning a weekend getaway.",
            "user_conversation":
            ("I'm planning a weekend trip to Paris. What should be on my "
             "itinerary?"),
            "assistant_conversation":
            ("In Paris for the weekend, I recommend starting with the "
             "Louvre Museum, followed by a stroll along the Seine River. "
             "Don't miss the Eiffel Tower and a visit to Notre-Dame "
             "Cathedral. For dinner, explore the charming cafes in "
             "Montmartre. If time allows, a boat cruise on the Seine in "
             "the evening is magical."),
            "categories": ["ASSISTANCE", "AUXILIARY"]
        },
        "favorite_food_discussion": {
            "user":
            "Food Lover",
            "assistant":
            "Culinary Expert",
            "task_prompt":
            ("Engage in a light, casual conversation about favorite foods."),
            "user_conversation":
            ("I absolutely love sushi! What about you, what's your favorite "
             "food?"),
            "assistant_conversation":
            ("Sushi is a fantastic choice! It offers such a variety of "
             "flavors and textures. As an AI, I don't eat, but I can "
             "understand why sushi is a favorite for many. Do you have a "
             "preferred type of sushi or a favorite sushi restaurant?"),
            "categories": ["NON-SUBSTANTIAL", "AUXILIARY"]
        }
    }

    # Run 4 examples about dialogue transformation
    for key, dialogue in dialogue_examples.items():
        user = dialogue["user"]
        assistant = dialogue["assistant"]
        task_prompt = dialogue["task_prompt"]
        user_conversation = dialogue["user_conversation"]
        assistant_conversation = dialogue["assistant_conversation"]

        transformed_text_with_category = \
            role_assignment_agent.transform_dialogue_into_text(
                user=user, assistant=assistant, task_prompt=task_prompt,
                user_conversation=user_conversation,
                assistant_conversation=assistant_conversation
                )

        # Check if the identity of the categories is appropriate
        is_in_categories = False
        for category in transformed_text_with_category["categories"]:
            is_in_categories = category in dialogue["categories"]
            if is_in_categories:
                break
        if not is_in_categories:
            raise ValueError(f"Category is not correct for {key}." +
                             f"Expected: {dialogue['categories']}, " +
                             "Actual: " +
                             f"{transformed_text_with_category['categories']}")

        print(Fore.GREEN + "Text transformed from dialogue:\n" +
              f"{json.dumps(transformed_text_with_category, indent=4)}")


if __name__ == "__main__":
    main()
