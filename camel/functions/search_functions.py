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
import os
from typing import Any, Dict, List

import camel.agents
from camel.functions import OpenAIFunction
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType


def search_wiki(entity: str) -> str:
    r"""Search the entity in WikiPedia and return the summary of the
    required page, containing factual information about the given entity.

    Args:
        entity (string): The entity to be searched.

    Returns:
        string: The search result. If the page corresponding to the entity
            exists, return the summary of this entity in a string.
    """
    try:
        import wikipedia
    except ImportError:
        raise ImportError(
            "Please install `wikipedia` first. You can install it by running "
            "`pip install wikipedia`.")

    result: str

    try:
        result = wikipedia.summary(entity, sentences=5, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        result = wikipedia.summary(e.options[0], sentences=5,
                                   auto_suggest=False)
    except wikipedia.exceptions.PageError:
        result = ("There is no page in Wikipedia corresponding to entity "
                  f"{entity}, please specify another word to describe the"
                  " entity to be searched.")
    except wikipedia.exceptions.WikipediaException as e:
        result = f"An exception occurred during the search: {e}"

    return result


def search_google(query: str) -> List[Dict[str, Any]]:
    r"""Use Google search engine to search information for the given query.

    Args:
        query (string): The query to be searched.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries where each dictionary
        represents a website.
            Each dictionary contains the following keys:
            - 'result_id': A number in order.
            - 'title': The title of the website.
            - 'description': A brief description of the website.
            - 'long_description': More detail of the website.
            - 'url': The URL of the website.

            Example:
            {
                'result_id': 1,
                'title': 'OpenAI',
                'description': 'An organization focused on ensuring that
                artificial general intelligence benefits all of humanity.',
                'long_description': 'OpenAI is a non-profit artificial
                 intelligence research company. Our goal is to advance digital
                intelligence in the way that is most likely to benefit humanity
                as a whole',
                'url': 'https://www.openai.com'
            }
        title, descrption, url of a website.
    """
    import requests

    # https://developers.google.com/custom-search/v1/overview
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    # https://cse.google.com/cse/all
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

    # Using the first page
    start_page_idx = 1
    # Different language may get different result
    search_language = "en"
    # How many pages to return
    num_result_pages = 10
    # Constructing the URL
    # Doc: https://developers.google.com/custom-search/v1/using_rest
    url = f"https://www.googleapis.com/customsearch/v1?" \
          f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start=" \
          f"{start_page_idx}&lr={search_language}&num={num_result_pages}"

    responses = []
    # Fetch the results given the URL
    try:
        # Make the get
        result = requests.get(url)
        data = result.json()

        # Get the result items
        if "items" in data:
            search_items = data.get("items")

            # Iterate over 10 results found
            for i, search_item in enumerate(search_items, start=1):
                if "og:description" in search_item["pagemap"]["metatags"][0]:
                    long_description = \
                        search_item["pagemap"]["metatags"][0]["og:description"]
                else:
                    long_description = "N/A"
                # Get the page title
                title = search_item.get("title")
                # Page snippet
                snippet = search_item.get("snippet")

                # Extract the page url
                link = search_item.get("link")
                response = {
                    "result_id": i,
                    "title": title,
                    "description": snippet,
                    "long_description": long_description,
                    "url": link
                }
                responses.append(response)
        else:
            responses.append({"error": "google search failed."})

    except requests.RequestException:
        responses.append({"error": "google search failed."})

    return responses


def text_extract_from_web(url: str) -> str:
    r"""Get the text information from given url.

    Args:
        url (string): The web site you want to search.

    Returns:
        string: All texts extract from the web.
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        # Request the target page
        response_text = requests.get(url).text

        # Parse the obtained page
        soup = BeautifulSoup(response_text, features="html.parser")

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        # Strip text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines
                  for phrase in line.split("  "))
        text = ".".join(chunk for chunk in chunks if chunk)

    except requests.RequestException:
        text = f"can't access {url}"

    return text


# Split a text into smaller chunks of size n
def create_chunks(text: str, n: int) -> List[str]:
    r"""Returns successive n-sized chunks from provided text."

    Args:
        text (string): The text to be split.
        n (int): The max length of a single chunk.

    Returns:
        List[str]: A list of splited texts.
    """

    chunks = []
    i = 0
    while i < len(text):
        # Find the nearest end of sentence within a range of 0.5 * n
        # and 1.5 * n tokens
        j = min(i + int(1.2 * n), len(text))
        while j > i + int(0.8 * n):
            # Decode the tokens and check for full stop or newline
            chunk = text[i:j]
            if chunk.endswith(".") or chunk.endswith("\n"):
                break
            j -= 1
        # If no end of sentence found, use n tokens as the chunk size
        if j == i + int(0.8 * n):
            j = min(i + n, len(text))
        chunks.append(text[i:j])
        i = j
    return chunks


def prompt_single_step_agent(prompt: str) -> str:
    """Prompt a single-step agent to summarize texts or answer a question."""

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = camel.agents.ChatAgent(assistant_sys_msg)
    agent.reset()

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content=prompt,
    )
    assistant_response = agent.step(user_msg)
    if assistant_response.msgs is not None:
        return assistant_response.msg.content
    return ""


def summarize_text(text: str, query: str) -> str:
    r"""Summarize the information from the text, base on the query if query is
    given.

    Args:
        text (string): Text to summarise.
        query (string): What information you want.

    Returns:
        string: Strings with information.
    """
    summary_prompt = TextPrompt(
        '''Gather information from this text that relative to the question, but
         do not directly answer the question.\nquestion: {query}\ntext ''')
    summary_prompt = summary_prompt.format(query=query)
    # Max length of each chunk
    max_len = 3000
    results = ""
    chunks = create_chunks(text, max_len)
    # Summarize
    for i, chunk in enumerate(chunks, start=1):
        prompt = summary_prompt + str(i) + ": " + chunk
        result = prompt_single_step_agent(prompt)
        results += result + "\n"

    # Final summarise
    final_prompt = TextPrompt(
        '''Here are some summarized texts which split from one text, Using the
        information to answer the question: {query}.\n\nText: ''')
    final_prompt = final_prompt.format(query=query)
    prompt = final_prompt + results

    response = prompt_single_step_agent(prompt)

    return response


def search_google_and_summarize(query: str) -> str:
    r"""Comprehensive Web Search and Information Synthesis. This function
    serves as a gateway to the vast universe of information available on the
    internet. By inputting a query, you are leveraging the powerful Google
    search engine to scan the web for relevant data, articles, studies, and
    discussions pertaining to your topic of interest.

    Here's what happens when you invoke this function:
    - Search Execution: Your query is used as the criterion for an extensive
        online search,
      executed through Google's sophisticated algorithms that prioritize
        relevance and credibility.
    - Data Aggregation: From the search results, a diverse array of sources
        is accessed,
      compiling insights, facts, and perspectives across various mediums and
        platforms.
    - Intelligent Summarization: The gathered information undergoes a
        process of condensation, where the essence of the content is
        distilled into a concise and informative summary. This involves
        filtering out the noise and focusing on the core material that is
        most informative and relevant to your query.
    - Answer Delivery: The end product is a synthesized, concise summary
        that encapsulates the key information you need, saving you the time
        and effort of sifting through countless web pages.
    Whether you're looking for a quick factual answer, an overview of a
        complex topic, or diverse viewpoints on a controversial subject,
        this function is your streamlined conduit to knowledge. Just type in
        your question, and let the tool do the rest, bringing you a clear,
        distilled answer drawn from the breadth of the internet.

    Args:
        query (string): Question you want to be answered.

    Returns:
        string: Summarized information from webs.
    """
    # Google search will return a list of urls
    responses = search_google(query)
    top_answer = None
    for item in responses:
        if "url" in item:
            url = item.get("url")
            # Extract text
            text = text_extract_from_web(str(url))
            # Using chatgpt summarise text
            # answer = summarize_text(text, query)
            insight_agent = camel.agents.InsightAgent(
                model_type=ModelType.GPT_3_5_TURBO_16K)
            insights = insight_agent.run(
                context_text=text, insights_instruction=(
                    "The CONTEXT CONTENT is the content of the web page, "
                    f"and the Google Search query is \"{query}\"."))
            answer = insight_agent.transform_into_text(insights=insights)

            # Let chatgpt decide whether to continue search or not
            prompt_tamplate = """Do you think the SEARCH_ANSWER can answer the SEARCH_QUERY. Use only 'yes' or 'no' to answer it.
===== SEARCH_ANSWER =====
{answer}
===== SEARCH_QUERY =====
{query}"""  # noqa: E501
            prompt = TextPrompt(prompt_tamplate)
            prompt = prompt.format(answer=answer, query=query)
            reply = prompt_single_step_agent(prompt)
            if "yes" in str(reply).lower():
                return answer
            elif top_answer is None:
                top_answer = answer

    return ("Failed to find the answer from google search, but only found "
            "the following information:\n" + top_answer)


SEARCH_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)
    for func in [search_wiki, search_google_and_summarize]
]
