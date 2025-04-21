# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Any, Optional

from camel.agents.base import BaseAgent
from camel.agents.search_agent import SearchAgent
from camel.retrievers.auto_retriever import AutoRetriever
from camel.toolkits.search_toolkit import SearchToolkit


class DeepResearchAgent(BaseAgent):
    r"""A minimal research agent that performs query-based document retrieval and summarization.

    This agent fetches live Wikipedia content based on the query and summarizes it into a markdown answer.
    """

    def __init__(self, top_k: int = 3,
                 retriever: Optional[AutoRetriever] = None,
                 summarizer: Optional[SearchAgent] = None) -> None:
        # Default retriever: wraps SearchToolkit with search_wiki()
        self.retriever = retriever or AutoRetriever(tool=SearchToolkit())
        self.summarizer = summarizer or SearchAgent()
        self.top_k = top_k

    def reset(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self.retriever, "reset"):
            self.retriever.reset()
        if hasattr(self.summarizer, "reset"):
            self.summarizer.reset()

    def step(self, query: str) -> str:
        """Run a research step: retrieve → summarize → format."""
        documents = self.retriever.retrieve(query, top_k=self.top_k)
        if not documents:
            return f"**No relevant documents found for:** {query}"

        # Join content for summarizer
        full_text = "\n\n".join([doc["content"] for doc in documents])
        summary = self.summarizer.summarize_text(full_text, query)

        output = f"## Query\n{query}\n\n"
        output += f"## Answer\n{summary.strip()}\n\n"
        output += "## Sources\n"
        for doc in documents:
            title = doc.get("source", "Wikipedia")
            url = doc.get("url", None)
            output += f"- [{title}]({url})\n" if url else f"- {title}\n"

        return output
