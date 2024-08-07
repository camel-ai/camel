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

from typing import List

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType


class Exercise(BaseModel):
    name: str
    sets: int
    reps: str


class WorkoutPlan(BaseModel):
    warm_up: List[str] = Field(..., description="List of warm-up exercises")
    strength_training: List[Exercise] = Field(
        ..., description="List of strength training exercises"
    )
    cardio: List[str] = Field(..., description="List of cardio exercises")
    cool_down: List[str] = Field(
        ..., description="List of cool-down exercises"
    )


class MealPlan(BaseModel):
    breakfast: str
    snack1: str
    lunch: str
    snack2: str
    dinner: str
    post_workout: str


class FitnessPlan(BaseModel):
    workout: WorkoutPlan
    diet: MealPlan
    hydration_tip: str


# Create SchemaModel instance
# If the class of pydantic is very complex, we recommend using a more powerful
# LLM.
model_name = "mistralai/Mistral-7B-v0.3"
cache_dir = None  # define the dir where the model is stored
model = ModelFactory.create(
    model_platform=ModelPlatformType.OUTLINES_TRANSFORMERS,
    model_type=model_name,
    model_config_dict={
        "device": "auto",  # example parameter
        "model_kwargs": {  # transformer model configuration
            "trust_remote_code": True,  # example parameter
            "cache_dir": cache_dir,  # example parameter
        },
        "tokenizer_kwargs": {  # tokenizer configuration
            "use_fast": True,  # example parameter
            "padding_side": "left",  # example parameter
            "truncation_side": "right",  # example parameter
        },
    },
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="I am a helpful assistant.",
)

# Create ChatAgent instance
schema_agent = ChatAgent(system_message=sys_msg, model=model)

# Define user message
user_msg = BaseMessage.make_user_message(
    role_name="user",
    content=(
        "I want to practice my legs today. Help me make a fitness and "
        "diet plan."
    ),
)
assistant_response = schema_agent.step(user_msg, output_schema=FitnessPlan)
print(assistant_response.msg.content)
"""
{
  "workout": {
    "warm_up": [
      "jumping jacks",
      "leg swings"
    ],
    "strength_training": [
      {
        "name": "squats",
        "sets": 3,
        "reps": ", 8}, {"
      }
    ],
    "cardio": [
      "tredmill ran"
    ],
    "cool_down": [
      "stretching"
    ]
  },
  "diet": {
    "breakfast": "oatmeal with fruit",
    "snack1": "apple",
    "lunch": "grilled chicken salad",
    "snack2": "carrots and hummus",
    "dinner": "quinoa and vegetables",
    "post_workout": "protein shake"
  },
  "hydration_tip": "drink 8 glasses of water"
}
"""
