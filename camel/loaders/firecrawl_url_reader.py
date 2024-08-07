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
from typing import Any, Dict, List, Optional

import firecrawl

from camel.types.enums import (
    FireCrawlExtractionMode,
    FireCrawlReturnFormat,
    FireCrawlSpeed,
)


class FireCrawlURLReader:
    """
    URL Reader provided by FireCrawl.\n
    This class provides methods to crawl and scrape URLs.\n
    The FireCrawl URL Reader is a powerful tool to scrape and extract
    content from websites. It can be used to scrape a single URL
    or crawl a website to scrape multiple pages.\n

    Args:
        api_key: The API key to use for the requests.
        api_url: The URL of the FireCrawl API. (Optional)

    See Also:
        https://docs.firecrawl.dev/api-reference/introduction
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        if isinstance(api_key, type(None)):
            print(
                "[FireCrawlURLReader] FIRECRAWL_API_KEY not set. "
                "This will result in a low rate limit of "
                "FireCrawl URL Reader. "
                "Get API key here: "
                "https://www.firecrawl.dev/app/api-keys."
            )
        api_url = api_url or os.getenv('FIRECRAWL_API_URL')
        if isinstance(api_url, type(None)):
            api_url = "https://api.firecrawl.dev"
        self._app = firecrawl.FirecrawlApp(api_key=api_key, api_url=api_url)

    def crawl(
        self,
        url: str,
        return_format: FireCrawlReturnFormat = FireCrawlReturnFormat.MARKDOWN,
        max_depth: Optional[int] = None,
        only_main_content: bool = False,
        limit: int = 10000,
        wait_until_done: bool = True,
        poll_interval: int = 2,
        idempotency_key: Optional[str] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
        generate_img_alt_text: bool = False,
        return_only_urls: bool = False,
        mode: FireCrawlSpeed = FireCrawlSpeed.DEFAULT,
        ignore_sitemap: bool = True,
        allow_backward_crawling: bool = False,
        allow_external_content_links: bool = False,
        only_include_tags: Optional[List[str]] = None,
        remove_tags: Optional[list[str]] = None,
        absolute_paths: bool = False,
        screenshot: bool = False,
        wait_for: int = 0,
        **kwargs: Any,
    ) -> Any:
        """
        Crawls the given URL and its subpages and returns the content
        in the specified format.\n
        (For basic use, focus on the core parameters only.)

        Args:
            url: `core parameter` The base URL to start crawling from.
            max_depth: `core parameter` Maximum depth to crawl
            relative to the entered URL.
                A maxDepth of 0 scrapes only the entered URL.
                A maxDepth of 1 scrapes the entered URL
                    and all pages one level deep.
                A maxDepth of 2 scrapes the entered URL
                    and all pages up to two levels deep.
                Higher values follow the same pattern.
            return_format: `core parameter` HTML, RAW_HTML, MARKDOWN, METADATA
            wait_until_done: Whether to wait until the crawl job is completed.
            poll_interval: Time in seconds between status checks
                when waiting for job completion.
            idempotency_key: A unique uuid key to ensure
                idempotency of requests.
            includes: URL patterns to include
            excludes: URL patterns to exclude
            generate_img_alt_text: Generate alt text for images using LLMs
                (must have a paid plan)
            return_only_urls:
                If true, returns only the URLs as a list on the crawl status.
                Attention: the return response will be \
                a list of URLs inside the data, not a list of documents.
            mode: The crawling mode to use.
                Fast mode crawls 4x faster websites without sitemap,
                but may not be as accurate
                and shouldn't be used in heavy js-rendered websites.
                Available options: DEFAULT, FAST
            ignore_sitemap: Ignore the website sitemap when crawling
            limit: Maximum number of pages to crawl
            allow_backward_crawling:
                Enables the crawler to navigate
                from a specific URL to previously linked pages.
                For instance,
                from 'example.com/product/123' back to 'example.com/product'
            allow_external_content_links:
                Allows the crawler to follow links to external websites.
            only_include_tags:
                Only include tags, classes and ids
                from the page in the final output.
            only_main_content: `core parameter` Only return the main content
                of the page excluding headers, navs, footers, etc.
            remove_tags: Tags, classes and ids to remove from the page.
            absolute_paths:
                Replace all paths with absolute paths.
            screenshot: Include a screenshot of the top
                of the page that you are scraping.
            wait_for:
                Wait x amount of milliseconds for the page
                to load to fetch content.
            **kwargs: Other options to pass to the request.

        Returns:
            A list of json objects containing the scraped content or the jobID

        Raises:
            RuntimeError: If the crawl fails.
        """
        params = {
            "crawlerOptions": {
                "includes": []
                if isinstance(includes, type(None))
                else includes,
                "excludes": []
                if isinstance(excludes, type(None))
                else excludes,
                "generateImgAltText": generate_img_alt_text,
                "returnOnlyUrls": return_only_urls,
                "maxDepth": 1000
                if isinstance(max_depth, type(None))
                else max_depth,
                "mode": mode.value,
                "ignoreSitemap": ignore_sitemap,
                "limit": limit,
                "allowBackwardCrawling": allow_backward_crawling,
                "allowExternalContentLinks": allow_external_content_links,
            },
            "pageOptions": {
                "includeHtml": True
                if return_format == FireCrawlReturnFormat.HTML.value
                else False,
                "includeRawHtml": True
                if return_format == FireCrawlReturnFormat.RAW_HTML.value
                else False,
                "onlyIncludeTags": []
                if isinstance(only_include_tags, type(None))
                else only_include_tags,
                "onlyMainContent": only_main_content,
                "removeTags": []
                if isinstance(remove_tags, type(None))
                else remove_tags,
                "replaceAllPathsWithAbsolutePaths": absolute_paths,
                "screenshot": screenshot,
                "waitFor": wait_for,
            },
            "otherOptions": kwargs,
        }
        try:
            crawl_result = self._app.crawl_url(
                url=url,
                params=params,
                wait_until_done=wait_until_done,
                poll_interval=poll_interval,
                idempotency_key=idempotency_key,
            )
            return (
                crawl_result if wait_until_done else crawl_result.get("jobId")
            )
        except Exception as e:
            raise RuntimeError(f"Failed to crawl {url}. Error: {e!s}")

    def check_crawl_job_status(self, job_id: str) -> Any:
        """
        Checks the status of a crawl job.

        Args:
            job_id: The job ID to check the status of.

        Returns:
            The status of the job.

        Raises:
            RuntimeError: If the job status check fails.
        """
        try:
            return self._app.check_crawl_status(job_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to check crawl job status for {job_id}. Error: {e!s}"
            )

    def scrape(
        self,
        url: str,
        return_format: FireCrawlReturnFormat = FireCrawlReturnFormat.MARKDOWN,
        only_include_tags: Optional[List[str]] = None,
        only_main_content: bool = False,
        remove_tags: Optional[list[str]] = None,
        absolute_paths: bool = False,
        screenshot: bool = False,
        wait_for: int = 0,
        timeout: int = 100000,
        **kwargs: Any,
    ) -> str:
        """
        Scrapes a single URL and returns the content in the specified format.\n
        (For basic use, focus on the core parameters only.)

        Args:
            url: `core parameter` the url to scrape
            return_format: `core parameter` HTML, RAW_HTML, MARKDOWN, METADATA
            only_include_tags: Only include tags, classes and ids
                from the page in the final output.
                Example: ['script', '.ad', '#footer']
            only_main_content:
                Only return the main content of the page excluding
                headers, navs, footers, etc.
            remove_tags: Tags, classes and ids to remove from the page.
                         Example: ['script', '.ad', '#footer']
            absolute_paths:
                Replace all relative paths with absolute paths.
            screenshot:
                Include a screenshot of the top of the page
                that you are scraping.
            wait_for:
                Wait x amount of milliseconds for the page
                to load to fetch content.
            timeout: Timeout in milliseconds for the request.
            kwargs: Other options to pass to the request.

        Returns:
            The scraped content in the specified format.

        Raises:
            RuntimeError: If the scrape fails.
        """

        page_options = {
            "includeHtml": True
            if return_format == FireCrawlReturnFormat.HTML.value
            else False,
            "includeRawHtml": True
            if return_format == FireCrawlReturnFormat.RAW_HTML.value
            else False,
            "onlyIncludeTags": []
            if isinstance(only_include_tags, type(None))
            else only_include_tags,
            "onlyMainContent": only_main_content,
            "removeTags": []
            if isinstance(remove_tags, type(None))
            else remove_tags,
            "replaceAllPathsWithAbsolutePaths": absolute_paths,
            "screenshot": screenshot,
            "waitFor": wait_for,
        }
        extractor_options = {
            "mode": "markdown",
            "extractionPrompt": "",
            "extractionSchema": {},
        }
        params = {
            "url": url,
            "pageOptions": page_options,
            "extractorOptions": extractor_options,
            "timeout": timeout,
            "otherOptions": kwargs,
        }
        try:
            return self._app.scrape_url(url, params).get(return_format.value)
        except Exception as e:
            raise RuntimeError(f"Failed to scrape {url}. Error: {e!s}")

    def scrape_with_llm(
        self,
        url: str,
        extraction_schema: Dict[str, Any],
        extraction_prompt: str = "",
        mode: FireCrawlExtractionMode = FireCrawlExtractionMode.DEFAULT,
        only_include_tags: Optional[List[str]] = None,
        only_main_content: bool = False,
        remove_tags: Optional[list[str]] = None,
        absolute_paths: bool = False,
        screenshot: bool = False,
        wait_for: int = 0,
        timeout: int = 100000,
        **kwargs: Any,
    ) -> dict:
        """
        Scrapes a single URL and returns the content
        in the specified format.\n
        `Consumes more credits` than the scrape
        method since it uses the LLM extraction model.\n
        (For basic use, focus on the core parameters only.)

        Args:
            url: `core parameter` the url to scrape.
            extraction_schema: `core parameter`
                                The schema to use for the extraction.
                                Better to use Pydantic models for this.
                                You can find an example in
                                test_firecrawl_url_reader.py (line 27).
            extraction_prompt:
                `core parameter` The prompt to use for the extraction.
            mode:
                The extraction mode to use.
                Options are: default, raw-html, markdown
            only_include_tags:
                Only include tags, classes and ids
                from the page in the final output.
                Example: ['script', '.ad', '#footer']
            only_main_content:
                Only return the main content of the page
                excluding headers, navs, footers, etc.
            remove_tags: Tags, classes and ids to remove from the page.
                         Example: ['script', '.ad', '#footer']
            absolute_paths:
                Replace all paths with absolute paths.
            screenshot:
                Include a screenshot of the top
                of the page that you are scraping.
            wait_for:
                Wait x amount of milliseconds
                for the page to load to fetch content.
            timeout: Timeout in milliseconds for the request.
            kwargs: Other options to pass to the request.

        Returns:
            The scraped content in the specified format.

        Raises:
            RuntimeError: If the scrape fails.
        """
        page_options = {
            "includeHtml": True,
            "includeRawHtml": True,
            "onlyIncludeTags": []
            if isinstance(only_include_tags, type(None))
            else only_include_tags,
            "onlyMainContent": only_main_content,
            "removeTags": []
            if isinstance(remove_tags, type(None))
            else remove_tags,
            "replaceAllPathsWithAbsolutePaths": absolute_paths,
            "screenshot": screenshot,
            "waitFor": wait_for,
        }
        extractor_options = {
            "mode": mode.value,
            "extractionPrompt": extraction_prompt,
            'extractionSchema': extraction_schema,
        }
        params = {
            "url": url,
            "pageOptions": page_options,
            "extractorOptions": extractor_options,
            "timeout": timeout,
            "otherOptions": kwargs,
        }
        try:
            return self._app.scrape_url(url, params).get("llm_extraction")
        except Exception as e:
            raise RuntimeError(
                f"Failed to use LLM to scrape {url}. Error: {e!s}"
            )
