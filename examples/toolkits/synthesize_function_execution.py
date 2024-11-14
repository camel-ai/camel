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
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.toolkits import FunctionTool


# example function
def movie_data_by_id(id: int) -> Dict[str, Any]:
    """
    Fetch movie data by its ID from the IMDB Top 100 Movies API.

    Parameters:
        id (int): The ID of the movie to retrieve information for.

    Returns:
        Dict[str, Any]: A dictionary with the following keys:
            - rank (int): The rank of the movie in the top 100 list.
            - title (str): The title of the movie.
            - rating (str): The movie's rating.
            - id (str): The unique identifier of the movie.
            - year (int): The release year of the movie.
            - description (str): A brief description of the movie.

    Raises:
        Exception: If an unexpected error occurs while fetching the data.
    """
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


# Define the response format for movie data
class MovieResponse(BaseModel):
    title: str = Field(description="The title of the movie.")
    rating: str = Field(description="The movie's rating.")


real_get_movie = FunctionTool(movie_data_by_id)
synthesized_get_movie = FunctionTool(movie_data_by_id, synthesize_output=True)

assistant_sys_msg = "You are a helpful assistant."
user_msg = "What is the title and rating of the movie with id 2048"

print("Synthesize output: False")
real_agent = ChatAgent(assistant_sys_msg, tools=[real_get_movie])
assistant_response = real_agent.step(user_msg)
print(assistant_response.msg.content)

print("\nSynthesize output: True")
synthesized_agent = ChatAgent(assistant_sys_msg, tools=[synthesized_get_movie])
assistant_response = synthesized_agent.step(
    user_msg, response_format=MovieResponse
)
print(assistant_response.msg.content)

"""
===============================================================================
Warning: No synthesize_output_model provided. Use `gpt-4o-mini` to synthesize
the output.
Synthesize output: False
It seems that I am unable to access the movie data at the moment due to a
subscription issue. However, you can usually find movie information such as
title and rating on popular movie databases like IMDb or Rotten Tomatoes. If
you have any other questions or need assistance with something else, feel free
to ask!

Synthesize output: True
The title of the movie with ID 2048 is "Inception" and its rating is 8.8.
===============================================================================
"""
