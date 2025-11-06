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
from camel.models import ModelFactory, OpenAIAudioModels
from camel.toolkits import AudioAnalysisToolkit
from camel.types import ModelPlatformType, ModelType

audio_models = OpenAIAudioModels()

# Set example input
input = """CAMEL-AI.org is an open-source community dedicated to the study of 
autonomous and communicative agents. We believe that studying these agents on 
a large scale offers valuable insights into their behaviors, capabilities, and 
potential risks. To facilitate research in this field, we provide, implement, 
and support various types of agents, tasks, prompts, models, datasets, and 
simulated environments.

Join us via Slack, Discord, or WeChat in pushing the boundaries of building AI 
Society."""

# Set example local path to store the file
storage_path = "examples/openai_audio_models/example_audio.mp3"

# Convert the example input into audio and store it locally
audio_models.text_to_speech(input=input, storage_path=storage_path)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_MINI,
)


audio_reason_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_MINI,
)

# Create the AudioAnalysisToolkit with our reasoning model
audio_toolkit = AudioAnalysisToolkit(audio_reasoning_model=audio_reason_model)

# Create a ChatAgent with the audio toolkit tools
agent = ChatAgent(
    system_message="You are an assistant specialized in audio analysis.",
    model=model,
    tools=[*audio_toolkit.get_tools()],
)

question = "What content can you hear in this audio?"
response = agent.step(
    f"I have an audio file at {storage_path}. Can you analyze it and tell "
    f"me {question}"
)
print(response.msgs[0].content)
print("\n")

response = agent.step(f"Please transcribe the audio file at {storage_path}")
print(response.msgs[0].content)
print("\n")

"""
==========================================================================
2025-03-09 22:54:55,822 - camel.camel.toolkits.audio_analysis_toolkit - 
WARNING - No audio transcription model provided. Using OpenAIAudioModels.

The audio content discusses Camel AI, an open-source community dedicated to 
the study of autonomous and communicative agents. It emphasizes the belief 
that large-scale research on these agents can yield valuable insights into 
their behaviors, capabilities, and potential risks. The community provides 
resources to support research, including various types of agents, tasks, 
prompts, models, datasets, and simulated environments. Additionally, it 
invites listeners to join the community through platforms like Slack, Discord, 
or WeChat to contribute to the development of AI society.


Here is the transcription of the audio:

"CamelAI.org is an open-source community dedicated to the study of autonomous 
and communicative agents. We believe that studying these agents on a large 
scale offers valuable insights into their behaviors, capabilities, and 
potential risks. To facilitate research in this field, we provide, implement, 
and support various types of agents, tasks, prompts, models, datasets, and 
simulated environments. Join us via Slack, Discord, or WeChat in pushing the 
boundaries of building AI society."
==========================================================================
"""
