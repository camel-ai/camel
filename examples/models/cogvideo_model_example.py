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

import asyncio

from camel.models import CogVideoModel
from camel.types import ModelType


async def main():
    # Initialize the CogVideo model
    model = CogVideoModel(
        model_type=ModelType.COGVIDEOX_5B,
        model_config_dict={"video_length": 4, "frame_rate": 8},
    )

    # Define the text prompt fro video generation
    prompt = "A video of a cat playing with a ball."

    # Run the model to generate video from the text prompt
    try:
        video_url = await model.run(prompt=prompt)
        print(f"Generated video URL: {video_url}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # Note: To run this code, you need to have a CogVideo server running
    # locally or remotely that provides endpoints for this model.
    # Ensure that the server is accessible at the specified URL
    # in the CogVideoModel class.
    asyncio.run(main())
