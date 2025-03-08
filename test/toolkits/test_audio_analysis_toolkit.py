from camel.toolkits.audio_analysis_toolkit import AudioAnalysisToolkit
from camel.models.openai_audio_models import OpenAIAudioModels
from camel.models.openai_model import OpenAIModel
from camel.toolkits import FunctionTool



audio_path = '/Users/humengkang/Downloads/test.mp3'

def test_audio_to_text():
    transcribe_model = OpenAIAudioModels()
    tool = FunctionTool(AudioAnalysisToolkit(transcribe_model=transcribe_model).audio2text)
    print(tool(audio_path))

def test_audio_qa():
    transcribe_model = OpenAIAudioModels()
    tool = FunctionTool(AudioAnalysisToolkit(transcribe_model=transcribe_model).ask_question_about_audio)
    question = 'Please output all numbers in the audio, seperated by comma.'
    print(tool(audio_path, question))

if __name__ == "__main__":
    # test_audio_to_text()
    test_audio_qa()