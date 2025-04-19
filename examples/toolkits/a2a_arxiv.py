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
from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import ArxivToolkit
from camel.toolkits.a2a import A2AChatAgent
from camel.types import ModelPlatformType, ModelType

load_dotenv()

sys_msg = "You are a helpful assistant"

# Set model config
tools = ArxivToolkit().get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()
print("creating model...")

model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

server = A2AChatAgent(camel_agent)
print("starting server...")
server.run(
    name="arxiv_search",
    description="Search arxiv papers",
    tags=["arxiv", "search"],
    example=[
        "Search paper 'attention is all you need' for me",
        "Download paper 'attention is all you need' for me to my computer",
    ],
)

print("server started")


"""
(.venv) PS D:\camel\examples\toolkits> python .\a2a_arxiv.py
creating model...
starting server...
Starting server on 0.0.0.0:10000
INFO:     Started server process [13964]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
INFO:     127.0.0.1:63673 - "GET /.well-known/agent.json HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [13964]
server started


PS D:\camel> curl http://127.0.0.1:10000/.well-known/agent.json


StatusCode        : 200
StatusDescription : OK
Content           : {"name":"arxiv_search","description":"Search arxiv papers","url":"http://0.0.0.0:10000/","version":"1.0.0","capabilities":{"stream 
                    ing":false,"pushNotifications":false,"stateTransitionHistory":false},"...
RawContent        : HTTP/1.1 200 OK
                    Content-Length: 505
                    Content-Type: application/json
                    Date: Sun, 13 Apr 2025 17:34:55 GMT
                    Server: uvicorn

                    {"name":"arxiv_search","description":"Search arxiv papers","url":"http://0...
Forms             : {}
Headers           : {[Content-Length, 505], [Content-Type, application/json], [
Date, Sun, 13 Apr 2025 17:34:55 GMT], [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 505

"""
