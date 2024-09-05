from typing import List, Literal

from camel.interpreters import InternalPythonInterpreter
from camel.toolkits import OpenAIFunction
from camel.utils import dependencies_required
from pydantic import BaseModel

from .base import BaseToolkit
import arxiv
from arxiv2text import arxiv_to_text
from concurrent.futures import ThreadPoolExecutor
import asyncio

class ArxivMetaData(BaseModel):
    entry_id: str
    updated_date: str
    title: str
    authors: list[str]
    comment: str
    def __str__(self) -> str:
        return (
            f"Paper Url: {self.entry_id}\n"
            f"title: {self.title}"
            f"Updated Time: {self.updated_date}\n"
            f"Authors: {" ".join(self.authors)}\n"
            f"Comment: {self.comment}\n"
        )


class ArxivToolkit(BaseToolkit):

    @dependencies_required('arxiv')
    def __init__(self) -> None:
        super().__init__()
        arxiv = self._import_arxiv_or_raise()
        self.client = arxiv.Client()
        self.current_search = {}
        self.cached_paper = {}

    def search_paper(self, 
                     query: str, 
                     max_results: int=10,
                     sort_by: object=arxiv.SortCriterion.SubmittedDate) -> list[ArxivMetaData]:
        search_result = arxiv.Search(
            query = query,
            max_results = max_results,
            sort_by = sort_by
        )

        arxiv_results = self.client.results(search_result)
        results = []
        for r in arxiv_results:
            results.append(ArxivMetaData(
                entry_id=r.entry_id,
                updated_date=r.updated.strftime("%Y-%m-%d %H:%M:%S"),
                authors=[a.name for a in r.authors],
                comment=r.comment,
            ))
            self.cached_paper[r.entry_id] = r
        return results
    # can be modified to str
    def _download_single_paper(self, 
                               title: str) -> str:
        search_result = arxiv.Search(
            query = title,
            max_results = 1,
        )
        
        arxiv_results = self.client.results(search_result)
        assert len(arxiv_results) <= 1
        if arxiv_results:
            return arxiv_to_text(arxiv_results(arxiv_results[0].pdf_url))
        return ""

    def download_papers(self, titles: List[str]) -> List[str]:
        def download_with_error_handling(title: str) -> str:
            try:
                return self._download_single_paper(title)
            except Exception as e:
                print(f"Error downloading paper '{title}': {str(e)}")
                return ""

        async def async_download_all():
            with ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(executor, download_with_error_handling, title)
                    for title in titles
                ]
                return await asyncio.gather(*tasks)

        return asyncio.run(async_download_all())
    
    def get_tools(self) -> List[OpenAIFunction]:
        return [
            OpenAIFunction(self.search_paper),
            OpenAIFunction(self.download_papers),
        ]
