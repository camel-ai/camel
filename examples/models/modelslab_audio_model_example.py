# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.models import ModelsLabAudioModel

# Initialize the ModelsLab audio model.
# API key is read from the MODELSLAB_API_KEY environment variable by default.
audio_model = ModelsLabAudioModel(
    voice_id=5,  # Female voice (1=neutral, 2=male, 3=warm male, 4=deep male,
    #              5=female, 6=clear female)
    language="english",
    speed=1.0,
)

# Example text to convert to speech
input_text = """CAMEL-AI.org is an open-source community dedicated to the study
of autonomous and communicative agents. We believe that studying these agents
on a large scale offers valuable insights into their behaviors, capabilities,
and potential risks. To facilitate research in this field, we provide,
implement, and support various types of agents, tasks, prompts, models,
datasets, and simulated environments.

Join us via Slack, Discord, or WeChat in pushing the boundaries of building
AI Society."""

# Output path for the generated audio
storage_path = "examples/modelslab_audio/example_audio.mp3"

# Convert text to speech and save locally
audio_bytes = audio_model.text_to_speech(
    input=input_text,
    storage_path=storage_path,
)

print(f"Audio saved to: {storage_path} ({len(audio_bytes)} bytes)")

'''
===============================================================================
Audio saved to: examples/modelslab_audio/example_audio.mp3 (12345 bytes)
===============================================================================
'''
