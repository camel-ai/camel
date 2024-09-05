from typing import List, Literal

from camel.interpreters import InternalPythonInterpreter
from camel.toolkits import OpenAIFunction
from camel.utils import dependencies_required
from pydantic import BaseModel

from .base import BaseToolkit
import arxiv
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
    def __init__(self, api_key: str, ) -> None:
        super().__init__()
        arxiv = self._import_arxiv_or_raise()
        self.client = arxiv.Client()
        self.current_search = {}
        self.cached_paper = {}

    def search_paper(self, 
                     query: str, 
                     max_results: int=10,
                     sort_by: object=arxiv.SortCriterion.SubmittedDate) -> list[ArxivMetaData]:
        search = arxiv.Search(
            query = query,
            max_results = max_results,
            sort_by = sort_by
        )

        arxiv_results = self.client.results(search)
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
    
    def download_paper(self, 
                       titles: list[str]):
        for title in titles:
            self.cached_paper[title].download_pdf(filename=f"{title}.pdf")
