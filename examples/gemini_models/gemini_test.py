from camel.models import GeminiModel
from camel.types.enums import ModelType

#model1 use stream 
model = GeminiModel(ModelType.GEMINI_1_5_FLASH, {'stream' : True})
#model2 
model = GeminiModel(ModelType.GEMINI_1_5_FLASH)
# messages = [{'role':'user', 'parts': ['Tell me a story about basketball']}]
messages = 'Tell me a story about basketball'
response = model.run(messages)


if(model.stream):
    for chunk in response:
        print(chunk.text)
else:
    print(response.text)