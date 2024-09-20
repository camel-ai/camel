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
from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import OPENAPI_FUNCS
from camel.toolkits.ask_news_toolkit import ASKNEWS_FUNCS, AskNewsToolkit
from camel.types import ModelPlatformType, ModelType

# # Define system message
# sys_msg = BaseMessage.make_assistant_message(
#     role_name='News Assistant',
#     content='You are a knowledgeable news assistant',
# )

# # Set model configuration
# tools = [*OPENAPI_FUNCS, *ASKNEWS_FUNCS]
# model_config_dict = ChatGPTConfig(
#     tools=tools,
#     temperature=0.0,
# ).as_dict()

# # Create model instance
# model = ModelFactory.create(
#     model_platform=ModelPlatformType.OPENAI,
#     model_type=ModelType.GPT_4O,
#     model_config_dict=model_config_dict,
# )

# # Initialize chat agent
# camel_agent = ChatAgent(
#     system_message=sys_msg,
#     model=model,
#     tools=tools,
# )
# camel_agent.reset()

# # Define user message
# usr_msg = BaseMessage.make_user_message(
#     role_name='User', content='Give me the latest news about AI advancements.'
# )

# # Get response information
# response = camel_agent.step(usr_msg)
# print(response.info['tool_calls'])

toolkit = AskNewsToolkit()

# Example usage of the chat_query method
try:
    print("Running chat_query for tech news...")
    chat_response = toolkit.chat_query(
        "What's going on in the latest tech news?"
    )
    # print(f"Chat Response: {chat_response}")
    print("chat_query executed successfully.")
except Exception as e:
    print(f"An error occurred in chat_query: {e}")

# Example usage of the get_news method:
try:
    print("Running get_news for AI advancements...")
    news = toolkit.get_news("Give me the latest news about AI advancements.")
    # print(news)
    print("get_news executed successfully.")
except Exception as e:
    print(f"An error occurred in get_news: {e}")

# Example usage of the get_stories method
try:
    print("Running get_stories for Technology and Science...")
    stories = toolkit.get_stories(
        categories=["Technology", "Science"],
        continent="North America",
        sort_by="coverage",
        sort_type="desc",
        reddit=3,
        expand_updates=True,
        max_updates=2,
        max_articles=10,
    )

    # for story in stories["stories"]:
    #     print(f"Headline: {story['headline']}")
    #     for update in story["updates"]:
    #         print(f"  Update Headline: {update['headline']}")
    #         print(f"  Story Content: {update['story']}")
    print("get_stories executed successfully.")
except Exception as e:
    print(f"An error occurred in get_stories: {e}")


# Example usage of the search_reddit method
try:
    print("Running search_reddit for sentiment, bitcoin, and halving...")
    reddit_response = toolkit.search_reddit(
        keywords=["sentiment", "bitcoin", "halving"], return_type="both"
    )

    # if isinstance(reddit_response, tuple):
    #     print(f"Reddit Response (String): {reddit_response[0]}")
    #     print(f"Reddit Response (Dict): {reddit_response[1]}")
    # else:
    #     print(f"Reddit Response: {reddit_response}")
    print("search_reddit executed successfully.")
except Exception as e:
    print(f"An error occurred in search_reddit: {e}")

# Example usage of the finance_query method
try:
    print("Running finance_query for Amazon sentiment data...")
    # Example returning a descriptive string
    sentiment_data_string = toolkit.finance_query(
        asset="amazon",
        metric="news_positive",
        date_from="2024-03-20T10:00:00Z",
        date_to="2024-03-24T23:00:00Z",
        return_type="string",
    )
    # print(f"Sentiment Data (String):\n{sentiment_data_string}")
    print("finance_query executed successfully.")
except Exception as e:
    print(f"An error occurred in finance_query: {e}")

"""
Running chat_query for tech news...
chat_query executed successfully.
Running get_news for AI advancements...
get_news executed successfully.
Running get_stories for Technology and Science...
get_stories executed successfully.
Running search_reddit for sentiment, bitcoin, and halving...
search_reddit executed successfully.
Running finance_query for Amazon sentiment data...
finance_query executed successfully.
"""
