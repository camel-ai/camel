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

from camel.models import OpenAIAudioModels

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

# Convert the generated audio file into text
text_output = audio_models.speech_to_text(audio_file_path=storage_path)

print(text_output)
"""
===============================================================================
CamelAI.org is an open-source community dedicated to the study of autonomous 
and communicative agents. We believe that studying these agents on a large 
scale offers valuable insights into their behaviors, capabilities, and 
potential risks. To facilitate research in this field, we provide, implement, 
and support various types of agents, tasks, prompts, models, datasets, and 
simulated environments. Join us via Slack, Discord, or WeChat in pushing the 
boundaries of building AI society.
===============================================================================
"""
