# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========


from typing import Any, Dict

import requests

from camel.agents import ChatAgent
from camel.toolkits import FunctionTool


# example function
def movie_data_by_id(id: int) -> Dict[str, Any]:
    '''
    Response Schema: {
      "rank": "integer",
      "title": "string",
      "rating": "string",
      "id": "string",
      "year": "integer",
      "description": "string",
    }
    '''
    try:
        url = f"https://imdb-top-100-movies.p.rapidapi.com/{id}"
        headers = {
            "x-rapidapi-key": "Your API Key",
            "x-rapidapi-host": "imdb-top-100-movies.p.rapidapi.com",
        }
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        return {
            "error": str(e),
        }


real_get_movie = FunctionTool(movie_data_by_id)
synthesized_get_movie = FunctionTool(
    movie_data_by_id, synthesis_output=True, synthesize_schema=True
)

assistant_sys_msg = "You are a helpful assistant."

print("Synthesis Mode: False")
agent = ChatAgent(
    assistant_sys_msg,
    tools=[real_get_movie],
)
user_msg = "What is the title and rating of the movie with id 2048"
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

print("\nSynthesis Mode: True")
agent = ChatAgent(
    assistant_sys_msg,
    tools=[synthesized_get_movie],
)
user_msg = "What is the title and rating of the movie with id 2048"
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
Synthesis Mode: False
It seems that I am unable to access the movie data at the moment due to a
subscription issue. However, you can usually find movie information such as
title and rating on popular movie databases like IMDb or Rotten Tomatoes. If
you have any other questions or need assistance with something else, feel free
to ask!

Synthesis Mode: True
Warning: No model provided. Use `gpt-4o-mini` to synthesize the output of the
function.
The title of the movie with ID 2048 is "Inception" and its rating is 8.8.
===============================================================================
"""
