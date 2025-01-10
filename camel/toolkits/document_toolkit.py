from camel.loaders.unstructured_io import UnstructuredIO
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits import ImageToolkit, AudioToolkit, VideoToolkit
from typing import List, Dict, Any, Optional, Tuple
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelType
import openai
import requests
import mimetypes
from retry import retry
from camel.models import OpenAIModel
from PIL import Image
from io import BytesIO
from loguru import logger
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urlparse, urljoin
import os

import nest_asyncio
nest_asyncio.apply()


class DocumentToolkit(BaseToolkit):
    r"""A class representing a toolkit for asking question about document.

    This class provides method for processing docx, pdf, pptx, etc. It cannot process excel files.
    """
    def __init__(self, cache_dir: Optional[str] = None):
        self.uio = UnstructuredIO() 

        self.cache_dir = "tmp/"
        if cache_dir:
            self.cache_dir = cache_dir

        self.image_tool = ImageToolkit()
        self.audio_tool = AudioToolkit()
        self.video_tool = VideoToolkit()

    @retry(requests.RequestException)
    def ask_question_about_document(self, document_path: str, question: str) -> str:
        r"""Ask a question about a document, but it cannot process excel files.

        Args:
            document_path (str): The path to the document, either a local path or a URL.
            question (str): The question to ask.
        
        Returns:
            str: The answer to the question.
        """
        logger.debug(f"Calling ask_question_about_document with document_path=`{document_path}` and question=`{question}`")
        def async_to_sync(func, *args, **kwargs):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.create_task(func(*args, **kwargs)).result()
            else:
                return asyncio.run(func(*args, **kwargs))

        # breakpoint()
        # handle Image
        if any(document_path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            res = self.image_tool.ask_image_by_path(question, document_path)
            return res
        
        # handle audio
        if any(document_path.endswith(ext) for ext in ['.mp3', '.wav']):
            res = self.audio_tool.ask_audio_by_path(question, document_path)
            return res

        else:
            # preprocess document first

            status, info = self._preprocess_document(document_path)
            if status is False:
                return info
            logger.debug(f"Extracted document content length: {len(info)}")
            document_text = info
            # breakpoint()

            if len(document_text) < 10000:
                prompt = f"""
                Here are the document's content parsed by unstuctured io:
                ```
                {document_text}
                ```
                Now please answer the following question based on the document:
                {question}
                Give accurate answer and do not generate abundant text.
                If you cannot answer the question because the information is not in the document, please give your reason.
                """

                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for document relevant tasks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                LLM = OpenAIModel(model_type=ModelType.DEFAULT)
                resp = LLM.run(messages)
                return resp.choices[0].message.content
            
            else:
                # the document is too long, use RAG
                kwargs = {
                    "plain_text": document_text,
                    "question": question
                }

                res = self._graph_rag_query(**kwargs)

                return res

    
    def _graph_rag_query(self, plain_text: str, question: str) -> str:
        r"""Query a document using GraphRAG.

        Args:
            plain_text (str): The plain text of the document.
            question (str): The question to ask.
        
        Returns:
            str: The answer to the question.
        """
        from .graphrag import (
            text2vec_embedding,
            openai_embedding,
            gpt_4o_mini_complete,
            gpt_4o_complete,
            GraphRAG
        )

        graph_rag = GraphRAG(
            working_dir=f"./graphrag_cache/{self._get_formatted_time()}",
            enable_llm_cache=True,
            embedding_func=text2vec_embedding,
            best_model_func=gpt_4o_mini_complete,
            cheap_model_func=gpt_4o_mini_complete
        )
        # breakpoint()

        graph_rag.insert(plain_text)
        res = graph_rag.query(question)
        return res
    

    @retry((openai.APITimeoutError, openai.APIConnectionError))
    def _preprocess_document(self, document_path: str) -> Tuple[bool, str]:
        r"""Preprocess the document.

        Args:
            document_path (str): The path to the document, either a local path or a URL.
        
        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the document was successfully preprocessed and a message.
        """

        def _is_webpage(url: str) -> bool:
            r"""Judge whether the given URL is a webpage."""
            try:
                parsed_url = urlparse(url)
                is_url = all([parsed_url.scheme, parsed_url.netloc])
                if not is_url:
                    return False

                path = parsed_url.path
                file_type, _ = mimetypes.guess_type(path)
                
                if file_type:
                    return False
                
                response = requests.head(url, allow_redirects=True, timeout=10)
                content_type = response.headers.get("Content-Type", "").lower()
                
                if "text/html" in content_type:
                    return True
                else:
                    return False
            
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Error while checking the URL: {e}")


        if _is_webpage(document_path):
            extracted_text = self._extract_webpage_content(document_path)
            return True, extracted_text

        else:
            # may be local file or url contains files. Here we don't neet to consider image and audio data format
            # kwargs = {
            #     "extract_images_in_pdf": True
            # }

            # judge if url
            parsed_url = urlparse(document_path)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            if not is_url:
                if not os.path.exists(document_path):
                    return f"Document not found at path: {document_path}."

            kwargs = {}
            elements = self.uio.parse_file_or_url(document_path, **kwargs)
            if elements is None:
                return False, f"Could not parse the document at {document_path}. Please check the file type and the path, then try again."
            
            chunked_elements = self.uio.chunk_elements(elements, "chunk_by_title")

            # If the document contains images, use the image comprehension assistant
            all_texts = []
            LLM = OpenAIModel(model_type=ModelType.DEFAULT)

            for chunk in chunked_elements:
                if chunk.category == "image":
                    # ! Assuming chunk.data contains the byte content of the image
                    try:
                        import base64
                        image_data = chunk.data
                        image = Image.open(BytesIO(image_data))
                        image_path = os.path.join(self.cache_dir, f"{self.get_formatted_time()}.jpg")
                        image.save(image_path)

                        question = "What is in this image? Please describe the content of the image in detail."

                        resp = self.image_tool.ask_image_by_path(question, image_path)
                        
                        image_info = f"""<image_description>{resp}</image_description>"""
                        all_texts.append(image_info)
                    except Exception as e:
                        logger.error(f"Error processing the image: {e}")
                        continue

                else:
                    all_texts.append(chunk.text)

            all_plain_texts = " ".join(all_texts)
            # breakpoint()
            return True, all_plain_texts
            

    def _extract_webpage_content(self, url: str) -> str:
        r"""Extract webpage content and classify by type
        
        Args:
            url (str): The URL of the webpage to extract content from.
            
        Returns:
            str: The extracted content.
        """
        def is_valid_url(url):
            try:
                result = urlparse(url)
                return all([result.scheme, result.netloc])
            except:
                return False


        def _extract_title(soup):
            if soup.title:
                return soup.title.string.strip()
            return ""

        def _extract_text_content(soup):
            for script in soup(["script", "style"]):
                script.decompose()
            
            text_blocks = []
            for paragraph in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'i']):
                text = paragraph.get_text().strip()
                if text and len(text) > 2:
                    text_blocks.append(text)
            
            return text_blocks

        def _extract_images(soup, base_url):
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if is_valid_url(absolute_url):
                        images.append(absolute_url)
            return images

        def _extract_videos(soup):
            videos = []
            for video in soup.find_all('video'):
                src = video.get('src')
                if src and is_valid_url(src):
                    videos.append(src)

            for iframe in soup.find_all('iframe'):
                src = iframe.get('src')
                if src and ('youtube.com' in src or 'vimeo.com' in src):
                    videos.append(src)
            
            return videos

        def _extract_links(soup, base_url):
            links = []
            for a in soup.find_all('a'):
                href = a.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    if is_valid_url(absolute_url):
                        text = a.get_text().strip()
                        links.append({
                            "url": absolute_url,
                            "text": text if text else "No text"
                        })
            return links

        def _extract_metadata(soup):
            metadata = {}
            for meta in soup.find_all('meta'):
                name = meta.get('name', meta.get('property', ''))
                content = meta.get('content', '')
                if name and content:
                    metadata[name] = content
                    
            return metadata


        result = {
            "url": url,
            "title": "",
            "text_content": [],
            "images": [],
            "videos": [],
            "links": [],
            "metadata": {}
        }
        
        try:
            if "youtube.com" in url or "youtu.be" in url:
                return self._handle_youtube_url(url)
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')

            result["title"] = _extract_title(soup)
            result["text_content"] = _extract_text_content(soup)
            result["images"] = _extract_images(soup, url)
            result["videos"] = _extract_videos(soup)
            result["links"] = _extract_links(soup, url)
            result["metadata"] = _extract_metadata(soup)
            
        except Exception as e:
            result["error"] = str(e)
        
        result_text = str(result)
        
        return result_text


    def _download_file(self, url: str):
        r"""Download a file from a URL and save it to the cache directory."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status() 
            file_name = url.split("/")[-1]  

            file_path = os.path.join(self.cache_dir, file_name)

            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            return file_path

        except requests.exceptions.RequestException as e:
            print(f"Error downloading the file: {e}")


    def _get_formatted_time(self) -> str:
        import time
        return time.strftime("%m%d%H%M")


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_document),
        ]


# simple test cases for document_toolkit
if __name__ == "__main__":
    import pytest
    from camel.toolkits import DocumentToolkit

    @pytest.fixture
    def document_toolkit():
        return DocumentToolkit()


    def test_document_1(document_toolkit):

        document_path = "https://en.wikipedia.org/wiki/Mercedes_Sosa"
        question = "How many studio albums were published by Mercedes Sosa between 2000 and 2009 (included)? Please answer with only the number."

        res = document_toolkit.ask_question_about_document(document_path, question)
        assert res == "3"


    def test_document_2(document_toolkit):

        document_path = "https://www.bbc.co.uk/writers/documents/doctor-who-s9-ep11-heaven-sent-steven-moffat.pdf"
        question = "What is this location called in the official script for the episode? Give the setting exactly as it appears in the first scene heading."

        res = document_toolkit.ask_question_about_document(document_path, question)
        assert "THE CASTLE".lower() in res.lower()


    def test_document_3(document_toolkit):

        document_path = "https://en.wikipedia.org/wiki/Wikipedia:Featured_article_candidates/Giganotosaurus/archive1"
        question = "Who nominated the only Featured Article on English Wikipedia about a dinosaur that was promoted in November 2016?"

        res = document_toolkit.ask_question_about_document(document_path, question)
        assert "FunkMonk".lower() in res.lower()
