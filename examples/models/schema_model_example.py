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

from huggingface_hub import login
from pydantic import BaseModel, Field

from camel.models import SchemaModel
from camel.types import ModelType


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


login(token="your_token")  # Hugging Face token

# Create SchemaModel instance
cache_dir = None  # Path to the cache directory
schema_model = SchemaModel(
    model_type=ModelType.TRANSFORMERS,
    # ex. ModelType.LLAMACPP, ModelType.VLLM
    model_config_dict={
        "model_name": "mistralai/Mistral-7B-v0.3",
        "cache_dir": cache_dir,
    },
)

# Define user message
user_msg = {
    "role": "user",
    "content": (
        "I want to practice my legs today. Help me make a fitness and "
        "diet plan."
    ),
}

# Get response using SchemaModel
response = schema_model.run([user_msg], FitnessPlan)

# Print the structured response
print(response.choices[0].message.content)
