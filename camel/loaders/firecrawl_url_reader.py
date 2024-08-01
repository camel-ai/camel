import json
import os
from typing import Optional, List, Dict, Any
import firecrawl
from camel.types.enums import FireCrawlSearchOption, FireCrawlReturnFormat, FireCrawlExtractionMode, FireCrawlSpeed


class FireCrawlURLReader:
    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        if api_key is None:
            raise Exception(
                "[FireCrawlURLReader] FIRECRAWL_API_KEY not set. Get API key here: "
                "https://www.firecrawl.dev/app/api-keys."
            )
        self._app = firecrawl.FirecrawlApp(api_key)

    def crawl(
            self,
            url: str,
            includes: Optional[List[str]] = None,
            excludes: Optional[List[str]] = None,
            generate_img_alt_text: bool = False,
            return_only_urls: bool = False,
            max_depth: int = 0,
            mode: FireCrawlSpeed = FireCrawlSpeed.DEFAULT,
            ignore_sitemap: bool = True,
            limit: int = 100,
            allow_backward_crawling: bool = False,
            allow_external_content_links: bool = False,
            return_format: FireCrawlReturnFormat = FireCrawlReturnFormat.MARKDOWN,
            only_include_tags: Optional[List[str]] = None,
            only_main_content: bool = False,
            remove_tags: Optional[list[str]] = None,
            replace_all_paths_with_absolute_paths: bool = False,
            screenshot: bool = False,
            wait_for: int = 0,
            **kwargs: Any
    ) -> str:
        """
        Crawls the given URL and its subpages and returns the content in the specified format.
        Args:
            url: the url to crawl
            includes:
            excludes:
            generate_img_alt_text:
            return_only_urls:
            max_depth:
            mode:
            ignore_sitemap:
            limit:
            allow_backward_crawling:
            allow_external_content_links:
            return_format:
            only_include_tags:
            only_main_content:
            remove_tags:
            replace_all_paths_with_absolute_paths:
            screenshot:
            wait_for:
            **kwargs:

        Returns:

        """
        params = {
            "url": "<string>",
            "crawlerOptions": {
                "includes": [] if includes is None else includes,
                "excludes": [] if excludes is None else excludes,
                "generateImgAltText": generate_img_alt_text,
                "returnOnlyUrls": return_only_urls,
                "maxDepth": max_depth,
                "mode": mode.value,
                "ignoreSitemap": ignore_sitemap,
                "limit": limit,
                "allowBackwardCrawling": allow_backward_crawling,
                "allowExternalContentLinks": allow_external_content_links
            },
            "pageOptions": {
                "includeHtml": True if return_format == FireCrawlReturnFormat.HTML.value else False,
                "includeRawHtml": True if return_format == FireCrawlReturnFormat.RAW_HTML.value else False,
                "onlyIncludeTags": [] if only_include_tags is None else only_include_tags,
                "onlyMainContent": only_main_content,
                "removeTags": [] if remove_tags is None else remove_tags,
                "replaceAllPathsWithAbsolutePaths": replace_all_paths_with_absolute_paths,
                "screenshot": screenshot,
                "waitFor": wait_for
            },
            "otherOptions": kwargs
        }
        crawl_result = self._app.crawl_url(url, params)
        return crawl_result

    def scrape(
            self,
            url: str,
            return_format: FireCrawlReturnFormat = FireCrawlReturnFormat.MARKDOWN,
            only_include_tags: Optional[List[str]] = None,
            only_main_content: bool = False,
            remove_tags: Optional[list[str]] = None,
            replace_all_paths_with_absolute_paths: bool = False,
            screenshot: bool = False,
            wait_for: int = 0,
            timeout: int = 100000,
            **kwargs: Any
    ) -> str:
        """
        Scrapes a single URL and returns the content in the specified format.

        Args:
            url: the url to scrape
            return_format: HTML, RAW_HTML, MARKDOWN, METADATA
            only_include_tags: Only include tags, classes and ids from the page in the final output.
                            Example: ['script', '.ad', '#footer']
            only_main_content: Only return the main content of the page excluding headers, navs, footers, etc.
            remove_tags: Tags, classes and ids to remove from the page.
                         Example: ['script', '.ad', '#footer']
            replace_all_paths_with_absolute_paths:
            screenshot: Include a screenshot of the top of the page that you are scraping.
            wait_for: Wait x amount of milliseconds for the page to load to fetch content.
            timeout: Timeout in milliseconds for the request.

        Returns:
            The scraped content in the specified format.

        """
        page_options = {
            "includeHtml": True if return_format == FireCrawlReturnFormat.HTML.value else False,
            "includeRawHtml": True if return_format == FireCrawlReturnFormat.RAW_HTML.value else False,
            "onlyIncludeTags": [] if only_include_tags is None else only_include_tags,
            "onlyMainContent": only_main_content,
            "removeTags": [] if remove_tags is None else remove_tags,
            "replaceAllPathsWithAbsolutePaths": replace_all_paths_with_absolute_paths,
            "screenshot": screenshot,
            "waitFor": wait_for
        }
        extractor_options = {
            "mode": "markdown",
            "extractionPrompt": "",
            "extractionSchema": {}
        }
        params = {
            "url": url,
            "pageOptions": page_options,
            "extractorOptions": extractor_options,
            "timeout": timeout,
            "otherOptions": kwargs
        }
        return self._app.scrape_url(url, params).get(return_format.value)

    def scrape_with_llm(
            self,
            url: str,
            mode: FireCrawlExtractionMode = FireCrawlExtractionMode.DEFAULT,
            extraction_prompt: str = "",
            extraction_schema: Optional[Dict[str, str]] = None,
            # return_format: FireCrawlReturnFormat = FireCrawlReturnFormat.MARKDOWN,
            only_include_tags: Optional[List[str]] = None,
            only_main_content: bool = False,
            remove_tags: Optional[list[str]] = None,
            replace_all_paths_with_absolute_paths: bool = False,
            screenshot: bool = False,
            wait_for: int = 0,
            timeout: int = 100000,
            **kwargs: Any
    ) -> dict:
        """
        Scrapes a single URL and returns the content in the specified format.

        Args:
            url: the url to scrape
            mode: The extraction mode to use. Options are: default, raw-html, markdown
            extraction_prompt: The prompt to use for the extraction.
            extraction_schema: The schema to use for the extraction.
            only_include_tags: Only include tags, classes and ids from the page in the final output.
                            Example: ['script', '.ad', '#footer']
            only_main_content: Only return the main content of the page excluding headers, navs, footers, etc.
            remove_tags: Tags, classes and ids to remove from the page.
                         Example: ['script', '.ad', '#footer']
            replace_all_paths_with_absolute_paths:
            screenshot: Include a screenshot of the top of the page that you are scraping.
            wait_for: Wait x amount of milliseconds for the page to load to fetch content.
            timeout: Timeout in milliseconds for the request.

        Returns:
            The scraped content in the specified format.

        """
        page_options = {
            "includeHtml": True,
            "includeRawHtml": True,
            "onlyIncludeTags": [] if only_include_tags is None else only_include_tags,
            "onlyMainContent": only_main_content,
            "removeTags": [] if remove_tags is None else remove_tags,
            "replaceAllPathsWithAbsolutePaths": replace_all_paths_with_absolute_paths,
            "screenshot": screenshot,
            "waitFor": wait_for
        }
        extractor_options = {
            "mode": "llm-extraction",
            "extractionPrompt": extraction_prompt,
            'extractionSchema': extraction_schema
        }
        params = {
            "url": url,
            "pageOptions": page_options,
            "extractorOptions": extractor_options,
            "timeout": timeout,
            "otherOptions": kwargs
        }
        return self._app.scrape_url(url, params).get("llm_extraction")
