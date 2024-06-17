from camel.models import GeminiModel
from camel.types.enums import ModelType

#model1 use stream 
model = GeminiModel(ModelType.GEMINI_1_5_FLASH, {'stream' : True})
#model2 
# model = GeminiModel(ModelType.GEMINI_1_5_FLASH)
messages1 = [{'role':'user', 'parts': ['Tell me a story about basketball']}]
# messages2 = 'Tell me a story about basketball'

response = model.run(messages1)
if(model.stream):
    for chunk in response:
        print(chunk.text)
else:
    print(response.text)

token_count = model.token_counter.count_tokens_from_messages(messages1)
print(token_count)