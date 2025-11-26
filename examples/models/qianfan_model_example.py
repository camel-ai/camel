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

from camel.agents import ChatAgent
from camel.configs import QianfanConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create ERNIE 5.0 Thinking model configuration
model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.ERNIE_5_0_THINKING,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Explain how Generative AI works."""

# Get response information
# response = camel_agent.step(user_msg)
# print(response.msgs[0].reasoning_content)
# print("========================")
# print(response.msgs[0].content)

'''
===============================================================================
The user is asking for an explanation of how Generative AI works. This is a 
broad topic, so I should start with a simple analogy to make it accessible, 
then gradually introduce more technical details. 

The analogy of a student learning from examples seems effective—it mirrors how 
generative models learn patterns from data. I can break it down into three key 
stages: training, learning representations, and generating new content. 

For the technical part, I should focus on the most common architectures like 
GANs and Transformers, since they represent distinct approaches (adversarial 
training vs. probabilistic modeling). It's important to highlight the role of 
latent space and probability distributions, as these are core to how 
generative models create novel outputs. 

I'll wrap up with a concise summary to reinforce the main ideas. The goal is 
to balance clarity with depth, avoiding unnecessary jargon unless I explain 
it.
========================
Let's break down how Generative AI works, from a simple analogy to the 
technical core.

### The Simple Analogy: A Student Learning Art

Imagine a student who wants to learn to paint like "Impressionist Art."

1.  **Training**: You show this student thousands of paintings by Monet, 
Renoir, and others. They don't memorize any single painting. Instead, they 
start to understand the *concepts*: the brush strokes, the use of light, 
the color palettes, the common subjects (water lilies, Parisian streets).
2.  **Learning the "Essence"**: The student's brain forms an internal,
abstract understanding of what makes an Impressionist painting. This 
isn't a specific image; it's the *idea* or *essence* of Impressionism.
3.  **Creating (Generating)**: Now, you ask the student: "Paint me a *new* 
picture in the style of Impressionism." Using their learned internal model, 
they create a completely original painting that has never existed before, 
but it still looks like a valid Impressionist piece because it follows the 
rules and patterns they learned.

**Generative AI works exactly like this student.** It is trained on a massive 
dataset (e.g., all of Wikipedia, a huge collection of images, or a library of 
music). It doesn't store copies of this data; instead, it learns the 
underlying patterns, relationships, and "essence" of the data. Then, 
it uses this learned model to create new, original content that fits 
within those patterns.

---

### The Technical Core: How It Actually Works

The "magic" happens through a type of machine learning model called a 
**neural network**, specifically designed for generation. The two most 
important architectures are **Generative Adversarial Networks (GANs)** and 
**Transformers** (which power models like GPT and DALL-E).
Let's look at the process in three key stages:
#### Stage 1: Training - Learning the Patterns

The model is fed a colossal amount of data—text, images, audio, etc. The goal 
is for the model to learn the probability distribution of the data. In simpler 
terms, it learns what kinds of things are likely to appear together.

*   **For Text**: It learns that the word "sky" is often followed by "is," 
    "was," or "blue," and almost never by "photosynthesis."
*   **For Images**: It learns that in a face, eyes are usually above a nose, 
    and a nose is usually above a mouth. It learns the texture of fur, the 
    shape of a wheel, the reflection of light on water.

#### Stage 2: The Model's Internal "World" (Latent Space)

This is a crucial concept. The model doesn't just store a giant database of 
images or text. It compresses the information it learns into a much smaller, 
dense, and abstract mathematical representation called **latent space**.

Think of latent space as a vast map of all possible concepts the model has 
learned.
*   For a face-generating AI, this map would have regions for "smiling faces," 
    "faces with glasses," "faces with long hair," etc.
*   Moving a little in one direction on this map might change a person's 
    expression from neutral to smiling. Moving in another direction might add 
    glasses.

This space is continuous, meaning every point in it corresponds to a valid 
piece of data (e.g., a specific face that doesn't exist but *could* exist).

#### Stage 3: Generation - Creating Something New

When you give a generative AI a prompt (e.g., "a cat wearing a top hat"), it 
uses this learned model and latent space to create a response.

**Interpretation**: The model converts your text prompt into a mathematical 
representation that points to a specific region in its latent space. In 
this case, it's the area where "cat" and "top hat" concepts overlap.

**Sampling**: The model then picks a random point within that targeted 
region of the latent space. Because the space is continuous, this point is 
unique and haven't been seen before.

**Decoding**: The model then works backwards, using its neural network as a 
"decoder." It takes this abstract point from latent space and gradually 
transforms it into a concrete output—pixel by pixel for an image, or word 
by word for text.

This is why you can ask for "a photorealistic cat wearing a red top hat, 
sitting on a couch," and it will generate a unique image that fits that 
description. It's not copying and pasting; it's navigating its internal "map" 
of concepts to a new location and then rendering what that location looks like.

---

### Two Key Architectural Approaches

1.  **Generative Adversarial Networks (GANs) - Common for Images**
*   **How it works**: A GAN pits two neural networks against each other in a 
    game.
*   **The Generator**: Tries to create fake data (e.g., a fake human face).
*   **The Discriminator**: Tries to tell the difference between real data 
    (from the training set) and fake data from the Generator.
*   **The "Adversarial" Process**: The Generator gets better at fooling the 
    Discriminator, and the Discriminator gets better at catching fakes. This 
    competition drives both to become incredibly sophisticated, resulting in 
    highly realistic generated content.

2.  **Transformers & Autoregressive Models - Common for Text (e.g., ChatGPT)**
*   **How it works**: These models predict the next most likely piece of data 
    in a sequence.
*   **For Text**: Given the prompt "The cat sat on the," the model calculates 
    the probability for every possible next word. "Mat" might have a high 
    probability, "cloud" a very low one. It then selects a word (sometimes 
    introducing a bit of randomness for creativity) and repeats the process: 
    "The cat sat on the mat. It then..." and so on, word by word, until it 
    generates a complete response.
*   **For Images (like DALL-E)**: They can treat a  n image as a sequence of 
    patches and predict the next patch based on the previous ones and the text 
    prompt.

### Summary

In a nutshell, Generative AI works by:

1.  **Training** on a massive dataset to learn the underlying patterns.
2.  **Compressing** this knowledge into an abstract mathematical space 
    (latent space).
3.  **Generating** new content by navigating this space based on a user's 
    prompt and then decoding that abstract point into a concrete output 
    (text, image, sound, etc.).

It's a powerful form of pattern recognition and probabilistic creation, not 
conscious thought or understanding.
===============================================================================
'''

# Create ERNIE 4.5 VL model configuration
model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.ERNIE_4_5_TURBO_VL,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

image_list = [
    "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
]

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Please tell me what is in the image!",
    image_list=image_list,
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].reasoning_content)
print("========================")
print(response.msgs[0].content)

"""
===============================================================================
Okay, the user has shared an image with the logo of "CAMEL-AI" which features 
a stylized camel and the text "CAMEL-AI" in purple. 
First, I need to recognize that this is a brand logo. The camel is a 
well-known symbol associated with endurance and reliability, often used by 
brands that want to convey strength or dependability. The text is in 
uppercase, bold, and purple - a color that can represent creativity, wisdom, 
or luxury. The user's request is straightforward: they want to know what's in 
the image. Since this is a simple identification task, I should respond 
clearly and directly. No need for complex analysis unless the user asks for 
deeper interpretation. I notice the user didn't provide any context about 
why they're asking. Maybe they encountered this logo somewhere and got 
curious, or perhaps they're testing my recognition abilities. Either way, 
keeping the response simple and factual is best. The logo appears clean and 
professional - likely from a tech or AI company given the "-AI" suffix. But 
since the user didn't ask for brand analysis, I'll stick to basic description. 
Hmm, should I mention possible interpretations of the camel symbolism? Probably
not - that would be overcomplicating a simple identification request. If the 
user wants more, they'll ask. 
Final decision: Just state the obvious elements - camel icon and "CAMEL-AI" 
text in purple. Keep it concise.

========================
The image shows the **logo for "CAMEL-AI"**, featuring two primary elements:

1. **Stylized Camel Icon**:  
   On the left, a minimalist silhouette of a camel in **solid purple**. 
   The design is abstract, emphasizing the camel's distinctive hump and 
   profile with clean lines and no intricate details.

2. **Text "CAMEL-AI"**:  
   To the right of the camel icon, the words "**CAMEL-AI**" are written in 
   **bold, uppercase purple letters**. The font is modern, sans-serif, and 
   evenly spaced, matching the camel icon's color for visual unity.

### Key Details:
- **Color Scheme**: Uniform purple (#4A248E or similar) on a white background, 
   creating high contrast and a professional aesthetic.  
- **Design Style**: Minimalist and geometric, prioritizing simplicity and 
    clarity.  
- **Symbolism**: The camel likely represents endurance, reliability, or 
"carrying" intelligence, while "-AI" explicitly denotes a focus on artificial 
intelligence.  

This logo likely represents a tech company, platform, or initiative bridging 
the identity of "Camel" with AI innovation.
===============================================================================
"""
