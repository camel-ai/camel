from tool_manager import ToolManager
from utils import ChatGPTWrapper, GPT4Wrapper
import re
from api_call_extraction import parse_api_call, get_api_call
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='log.txt')

prompt = '''
You will be given a API box, including a set of APIs, such as Calculator, Translator, WikiSearch, etc. When you want to use a API, you must search it by keywords in a API search engine. Try to describe it by these keywords. Then the tool search engine will return you the most related tool information (api name, description, input/output parameters). You should understand this information and use it in a natural way.
I am a client to help you communicate with the user (front stage), as well as help you communicate with the backend (I will play the backend too) for calling API (back stage, invisible to me). I will forward your response to the right receiver, it requires you to declare the recipient of your reply (Bot or API call) before each reply. 
During the dialogue with the user, you can always use the tool search engine (format: [ToolSearcher(keywords='keyword1 keyword2 ...')]) to search the tool you need. This searching process is invisible to the client. If the information is beyond your knowledge, call the API for queries if possible.
Note that if you encounter some required input parameters that you have not ever known its value, you have to collect it before calling API, instead of filling in the parameters directly by yourself.
Here is an example for API search, ChatGPT represent you, and Client represent me.
Example:
Client: (User) Can you help me calculate something?
ChatGPT: (API call) [ToolSearcher(keywords='calculator')] (wait for the result)
Client: (API return) {"name": "Calculator", "description": "This API provides basic arithmetic operations: addition, subtraction, multiplication, and division.", "input_parameters": {"formula": {"type": "str", "description": "The formula that needs to be calculated. Only integers are supported. Valid operators are +, -, *, /, and (, ). For example, '(1 + 2) * 3'."}}, "output_parameters": {"result": {"type": "float", "description": "The result of the formula."}}}
ChatGPT: (Bot) Please provide the formula.
Client: (User) (5+3)*6
ChatGPT: (API call) [Calculator(formula='(5+3)*6')] (wait for the result)
Client: (API return) {'result': 48}
ChatGPT: (Bot) The result of (5+3)*6 is 48.
Client: (User) Thank you.

Now, we start. The following is the first utterence of Client:
'''

class Simulater():
    def __init__(self, api_key, gpt4=False):
        self.prompt = prompt
        self.tool_manager = ToolManager()
        if gpt4:
            self.chat_gpt = GPT4Wrapper(api_key=api_key)
        else:
            self.chat_gpt = ChatGPTWrapper(api_key=api_key)
        self.chat_history = [{'role': 'system', 'content': self.prompt}]

    def run(self):
        while True:
            user_input = input('Please enter your message:\n')
            user_input = '(User) ' + user_input

            logging.info(user_input)

            self.chat_history.append({'role': 'user', 'content': user_input})
            response = self.chat_gpt.call(self.chat_history)
            response = response['choices'][0]['message']['content']            

            while get_api_call(response):
                print(response)
                logging.info(response)
                api_name, param_dict = parse_api_call(response)
                try:
                    result = self.tool_manager.api_call(api_name, **param_dict)
                except Exception as e:
                    api_result = '(API) ' + str(e)
                else:
                    if result['exception']:
                        api_result = '(API) Exception: ' + str(result['exception'])
                    else:
                        api_result = '(API) ' + str(result['output'])
                print(api_result)
                logging.info(api_result)
                self.chat_history.append({'role': 'assistant', 'content': response})
                self.chat_history.append({'role': 'system', 'content': api_result})
                response = self.chat_gpt.call(self.chat_history)
                response = response['choices'][0]['message']['content']

            print(response)
            logging.info(response)

if __name__ == '__main__':
    simulater = Simulater(api_key="YOUR_API_KEY")
    simulater.run()