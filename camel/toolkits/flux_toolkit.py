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
import base64
import os
import uuid
from io import BytesIO
from typing import List

import torch
from diffusers import FluxPipeline
from PIL import Image

from camel.toolkits import OpenAIFunction
from camel.toolkits.base import BaseToolkit


class FluxToolkit(BaseToolkit):
    r"""A class representing a toolkit for image generation using Flux.

    This class provides methods to handle image generation using the Flux
    model.
    """

    def __init__(self):
        self.token = os.getenv("HUGGINGFACE_TOKEN")
        if not self.token:
            raise ValueError(
                "Hugging Face token not found in environment variables. "
                "Please set 'HUGGINGFACE_TOKEN'."
            )
        from diffusers import FluxPipeline

        self.FluxPipeline = FluxPipeline

    def image_to_base64(self, image: Image.Image) -> str:
        r"""Converts an image into a base64-encoded string.

        Args:
            image: The image object to be encoded, supports any image format
                that can be saved in PNG format.

        Returns:
            str: A base64-encoded string of the image.
        """
        try:
            with BytesIO() as buffered_image:
                image.save(buffered_image, format="PNG")
                buffered_image.seek(0)
                image_bytes = buffered_image.read()
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                return base64_str
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""

    def generate_flux_img(self, prompt: str, image_dir: str = "img") -> str:
        r"""Generate an image using the Flux model.
            The generated image is saved to the specified directory.

        Args:
            prompt (str): The text prompt based on which the image is
            generated.
            image_dir (str): The directory to save the generated image.
                Defaults to 'img'.

        Returns:
            str: The path to the saved image.
        """

        pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16
        )
        if torch.cuda.is_available():
            device = torch.device("cuda")
            pipe.enable_model_cpu_offload()
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
            pipe = pipe.to(device)
        else:
            device = torch.device("cpu")
            pipe = pipe.to(device)

        image = pipe(
            prompt,
            height=1024,
            width=1024,
            guidance_scale=3.5,
            num_inference_steps=50,
            max_sequence_length=512,
            generator=torch.Generator("cpu").manual_seed(0),
        ).images[0]

        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, f"{uuid.uuid4()}.png")
        image.save(image_path)

        return image_path

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the functions
        in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects representing
                the functions in the toolkit.
        """
        return [OpenAIFunction(self.generate_flux_img)]


FLUX_FUNCS: List[OpenAIFunction] = FluxToolkit().get_tools()

if __name__ == "__main__":
    # Initialize the FluxToolkit
    flux_toolkit = FluxToolkit()

    # Define the prompt for image generation
    prompt = "A futuristic cityscape at sunset"

    # Generate the image using the provided prompt
    image_path = flux_toolkit.generate_flux_img(prompt)

    # Print the path to the saved image
    print(f"Generated image saved at: {image_path}")

    # Optionally, convert the image to a base64 string
    image = Image.open(image_path)
    base64_str = flux_toolkit.image_to_base64(image)

    # Print the base64 string
    print(f"Base64 string of the generated image: {base64_str}")
