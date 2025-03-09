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
from camel.models.openai_audio_models import OpenAIAudioModels
from camel.toolkits import FunctionTool
from camel.toolkits.audio_analysis_toolkit import AudioAnalysisToolkit

audio_path = '/Users/humengkang/Downloads/test.mp3'


def test_audio_to_text():
    transcribe_model = OpenAIAudioModels()
    tool = FunctionTool(
        AudioAnalysisToolkit(transcribe_model=transcribe_model).audio2text
    )
    print(tool(audio_path))


def test_audio_qa():
    transcribe_model = OpenAIAudioModels()
    tool = FunctionTool(
        AudioAnalysisToolkit(
            transcribe_model=transcribe_model
        ).ask_question_about_audio
    )
    question = 'Please output all numbers in the audio, seperated by comma.'
    print(tool(audio_path, question))


if __name__ == "__main__":
    # test_audio_to_text()
    test_audio_qa()
