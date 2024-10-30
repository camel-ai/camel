import gradio as gr
import os 
import json 
import requests

from tool_manager import ToolManager
from utils import ChatGPTWrapper, GPT4Wrapper
from api_call_extraction import get_api_call, parse_api_call
from api_call_extraction import parse_api_call
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#Streaming endpoint 
API_URL = "https://api.openai.com/v1/chat/completions"

#Huggingface provided GPT4 OpenAI API Key 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 

tool_manager = ToolManager()

proxies = None # {'http': 'http://', 'https': 'https://'} 

def history_to_chat(history):
    chat_pairs = []
    pair = (None, None) # user, model
    for item in history:
        if item['role'] == 'user':
            if pair[0] is not None:
                chat_pairs.append(pair)
                pair = (None, None)
            pair = (item['content'], pair[1])
        elif item['role'] == 'assistant':
            if pair[1] is not None:
                chat_pairs.append(pair)
                pair = (None, None)
            pair = (pair[0], item['content'])
    if pair[0] is not None or pair[1] is not None:
        chat_pairs.append(pair)
    return chat_pairs

def history_to_backend(history):
    chat_pairs = []
    pair = ('placeholder', None) # response, model
    for item in history:
        if item['role'] == 'system':
            if pair[0] is not None:
                chat_pairs.append(pair)
                pair = (None, None)
            pair = (item['content'], pair[1])
        elif item['role'] == 'assistant':
            if pair[1] is not None:
                chat_pairs.append(pair)
                pair = (None, None)
            pair = (pair[0], item['content'])
    if pair[0] is not None or pair[1] is not None:
        chat_pairs.append(pair)
    if chat_pairs[0][0] == 'placeholder':
        chat_pairs[0] = (None, chat_pairs[0][1])
    return chat_pairs

#Inferenec function
def predict(model_type, system_msg, inputs, top_p, temperature, chatbot=[], backend=[], history=[], backend_history=[], all_history=[]):  

    if model_type == 'GPT-4':
        logging.info(f"model_type is {model_type}")
        gpt = GPT4Wrapper(api_key=OPENAI_API_KEY, proxies=proxies)
    elif model_type == 'GPT-3.5':
        logging.info(f"model_type is {model_type}")
        gpt = ChatGPTWrapper(api_key=OPENAI_API_KEY, proxies=proxies)

    logging.info(f"system message is ^^ {system_msg}")
    if system_msg.strip() == '':
        system_prompt = None
        payload = {
            "temperature" : temperature, #1.0,
            "top_p": top_p, #1.0,
            "n" : 1,
        }
    else:
        system_prompt = {"role": "system", "content": system_msg}
        payload = {
            "temperature" : 1.0,
            "top_p":1.0,
            "n" : 1,
        }
        
    if system_prompt:
        all_history.append(system_prompt)
    logging.info(f"Logging : user input is - {inputs}")
    all_history.append({"role": "user", "content": "(User) " + inputs})
    history.append({"role": "user", "content": "(User) " + inputs})
    messages = all_history.copy()
    backend = history_to_backend(backend_history)
    chat = history_to_chat(history)
    yield chat, backend, history, backend_history, all_history, ''  


    logging.info(f"Logging : payload is - {payload}")

    response = gpt.call(messages, **payload)
    model_output = response['choices'][0]['message']['content']          
    while get_api_call(model_output):
        logging.info(f"Logging : api detected model_output is - {model_output}")  
        backend_history.append({"role": "assistant", "content": "(API Call) " + get_api_call(model_output)})
        all_history.append({"role": "assistant", "content": "(API Call) " + get_api_call(model_output)})
        backend = history_to_backend(backend_history)
        chat = history_to_chat(history)
        yield chat, backend, history, backend_history, all_history, response  
        
        api_name, param_dict = parse_api_call(model_output)
        try:
            result = tool_manager.api_call(api_name, **param_dict)
        except Exception as e:
            api_result = '(API) ' + str(e)
        else:
            if result['exception']:
                api_result = '(API) Exception: ' + str(result['exception'])
            else:
                api_result = '(API) ' + str(result['output'])
        # print(api_result)
        logging.info(api_result)
        backend_history.append({"role": "system", "content": api_result})
        all_history.append({"role": "system", "content": api_result})
        backend = history_to_backend(backend_history)
        chat = history_to_chat(history)
        yield chat, backend, history, backend_history, all_history, response  

        messages = all_history.copy()
        response = gpt.call(messages, **payload)
        model_output = response['choices'][0]['message']['content']

    logging.info(f"Logging : model_output is - {model_output}")  

    history.append({"role": "assistant", "content": model_output})
    all_history.append({"role": "assistant", "content": model_output})
    logging.info(f"Logging : history is - {history}")
    backend = history_to_backend(backend_history)
    chat = history_to_chat(history)

    logging.info(f"Logging : all_history is - {all_history}")
    yield chat, backend, history, backend_history, all_history, response  # resembles {chatbot: chat, state: history}  

#Resetting to blank
def reset_textbox():
    return gr.update(value='')

#to set a component as visible=False
def set_visible_false():
    return gr.update(visible=False)

#to set a component as visible=True
def set_visible_true():
    return gr.update(visible=True)

def update_api_key(api_key):
    global OPENAI_API_KEY
    OPENAI_API_KEY = api_key
    logging.info(f"Logging : OPENAI_API_KEY is - {OPENAI_API_KEY}")
    return 

title = """<h1 align="center">🔥GPT with API-Bank🎉</h1>"""

#display message for themes feature
intro = """<h3 align="center">🌟Chatting with ChatGPT while interacting with API-Bank implemented APIs🏆</h3>
"""

#Using info to add additional information about System message in GPT4
system_msg_info = "The prompt used for this conversation. You can modify it yourself to improve the behavior of AI Assistant."

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
'''.strip()

# Modifying existing Gradio Theme
theme = gr.themes.Soft(primary_hue="zinc", secondary_hue="green", neutral_hue="green",
                      text_size=gr.themes.sizes.text_lg)                

with gr.Blocks(css = """#col_container { margin-left: auto; margin-right: auto;} #chatbot {height: 520px; overflow: auto;}""",
                      theme=theme) as demo:

    gr.HTML(title)
    gr.HTML(intro)
    # gr.HTML('''<center><a href="https://huggingface.co/spaces/ysharma/ChatGPT4?duplicate=true"><img src="https://bit.ly/3gLdBN6" alt="Duplicate Space"></a>Duplicate the Space and run securely with your OpenAI API Key</center>''')

    with gr.Column(elem_id = "col_container"):
        #GPT4 API Key is provided by Huggingface 
        api_key = gr.Textbox(label="OpenAI API Key", info="You can get your API key from https://platform.openai.com/account/api-keys", value=OPENAI_API_KEY, visible=False)
        model_type = gr.Radio(["GPT-3.5", "GPT-4"], label="Model", info="Which model to use for the chatbot. GPT-3.5 is the default.", value="GPT-3.5")
        with gr.Accordion(label="System message:", open=False):
            system_msg = gr.Textbox(label="Instruct the AI Assistant to set its beaviour", info = system_msg_info, value=prompt)
            accordion_msg = gr.HTML(value="🚧 To set System message you will have to refresh the app", visible=False)
        with gr.Row():
            chatbot = gr.Chatbot(label='GPT', elem_id="chatbot")
            backend = gr.Chatbot(label='Backend', elem_id="backend")

        inputs = gr.Textbox(placeholder= "Hi there!", label= "Type an input and press Enter")
        state = gr.State([]) 
        backend_state = gr.State([])
        all_state = gr.State([])
        with gr.Row():
            with gr.Column(scale=7):
                b1 = gr.Button().style(full_width=True)
            with gr.Column(scale=3):
                server_status_code = gr.Textbox(label="Status code from OpenAI server", )
    
        # top_p, temperature
        with gr.Accordion("Parameters", open=False):
            top_p = gr.Slider( minimum=-0, maximum=1.0, value=1.0, step=0.05, interactive=True, label="Top-p (nucleus sampling)",)
            temperature = gr.Slider( minimum=-0, maximum=5.0, value=1.0, step=0.1, interactive=True, label="Temperature",)

    #Event handling
    api_key.change(update_api_key, [api_key], [])

    inputs.submit( predict, [model_type, system_msg, inputs, top_p, temperature, chatbot, backend, state, backend_state, all_state], [chatbot, backend, state, backend_state, all_state, server_status_code],)  #openai_api_key
    b1.click( predict, [model_type, system_msg, inputs, top_p, temperature, chatbot, backend, state, backend_state, all_state], [chatbot, backend, state, backend_state, all_state, server_status_code],)  #openai_api_key
    
    inputs.submit(set_visible_false, [], [system_msg])
    b1.click(set_visible_false, [], [system_msg])
    inputs.submit(set_visible_true, [], [accordion_msg])
    b1.click(set_visible_true, [], [accordion_msg])
    
    b1.click(reset_textbox, [], [inputs])
    inputs.submit(reset_textbox, [], [inputs])
    b1.click(reset_textbox, [], [system_msg])
    inputs.submit(reset_textbox, [], [system_msg])
        
# demo.queue(max_size=99, concurrency_count=20).launch(debug=True)
demo.queue(concurrency_count=20)
demo.launch(show_error=True)