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
from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.typing import RoleType


# flake8: noqa :E501
class ToolAgentsPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `tool_agents`.

    Attributes:
        GORILLA_GENERATE_CODE (TextPrompt): A prompt to generate code with gorilla-inspired APIs.
    """
    GORILLA_GENERATE_CODE = TextPrompt(
        """I will ask you to perform a task based on a given API, your job is to come up with a series of simple commands in Python that will perform the task.
I will give you some information about the API including the task domin, the API method name, the API provider and the description of its usage. Sometimes there are several lines of codes for referencing.
Each instruction in Python should be a simple assignment. You can print intermediate results if it makes sense to do so.
You should make sure the code is runnable. You should import all necessary libraries by yourself. You should print or save the result at the end.

Task: "Draw me a picture of a camel."

API info: <<<domain>>>: Multimodal Text-to-Image
<<<api_call>>>: StableDiffusionPipeline.from_pretrained('stabilityai/stable-diffusion-2-1-base', scheduler=EulerDiscreteScheduler.from_pretrained(stabilityai/stable-diffusion-2-1-base, subfolder=scheduler), torch_dtype=torch.float16)
<<<api_provider>>>: Hugging Face
<<<explanation>>>: 1. Import the required libraries: StableDiffusionPipeline and EulerDiscreteScheduler from the diffusers package, and torch.
2. Load the pre-trained model 'stabilityai/stable-diffusion-2-1-base' and the EulerDiscreteScheduler from the diffusers package using the from_pretrained methods.
3. Set the model.to() to the proper device (e.g., cuda for GPU).
4. Move the pipeline to the GPU if available (e.g., with .to('cuda')).
5. Provide a text prompt describing the desired image.
6. Generate the image with the provided text prompt using the pipeline.
7. Save the generated image to a file.
<<<code>>>: from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
import torch
model_id = 'stabilityai/stable-diffusion-2-1-base'
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder='scheduler')
pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler, torch_dtype=torch.float16)
pipe = pipe.to('cuda')
prompt = 'a picture of an astronaut riding a horse on mars'
image = pipe(prompt).images[0]
image.save('astronaut_rides_horse.png')

Answer:
```py
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
import torch
model_id = 'stabilityai/stable-diffusion-2-1-base'
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder='scheduler')
pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler, torch_dtype=torch.float16)
pipe = pipe.to('cuda')
prompt = 'a picture of a camel'
image = pipe(prompt).images[0]
image.save('camel.png')
```

Task: "Translate this sentence from English to Chinese: Please give me a cup of water."

API info:
<<<domain>>>: Natural Language Processing Translation
<<<api_call>>>: AutoModelForSeq2SeqLM.from_pretrained('Helsinki-NLP/opus-mt-en-zh')
<<<api_provider>>>: Hugging Face Transformers
<<<explanation>>>: 1. Import the necessary classes from the transformers library, which are AutoTokenizer and AutoModelForSeq2SeqLM.
2. Use the from_pretrained method of the AutoTokenizer class to load the tokenizer of the model 'Helsinki-NLP/opus-mt-en-zh'.
3. Use the from_pretrained method of the AutoModelForSeq2SeqLM class to load the pre-trained translation model 'Helsinki-NLP/opus-mt-en-zh'. This model is trained to translate English text to Chinese.
4. You can now use this model to translate any given English text to Chinese using the tokenizer and the model together.

Answer:
```py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained('Helsinki-NLP/opus-mt-en-zh')
model = AutoModelForSeq2SeqLM.from_pretrained('Helsinki-NLP/opus-mt-en-zh')

english_text = "Please give me a cup of water."
input_text = tokenizer.encode(english_text, return_tensors="pt")
translation = model.generate(input_text)
chinese_text = tokenizer.decode(translation[0], skip_special_tokens=True)

print(chinese_text)
```
Task: "{task}"

API info:
{api_info}

Answer:
""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            "gorilla": self.GORILLA_GENERATE_CODE,
            RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            RoleType.USER: self.USER_PROMPT,
            RoleType.CRITIC: self.CRITIC_PROMPT,
        })