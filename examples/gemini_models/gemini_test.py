from camel.models import GeminiModel
from camel.types.enums import ModelType

model = GeminiModel(ModelType.GEMINI_1_5_FLASH, {'stream' : True})
messages = [{'role':'user', 'parts': ['Tell me a story about basketball']}]
response = model.run(messages)


if(model.stream):
    for chunk in response:
        print(chunk.text)
else:
    print(response.text)