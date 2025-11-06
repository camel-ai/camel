---
title: "Loaders"
icon: loader
---

<Card title="What are Loaders?" icon="loader">
  CAMEL’s Loaders provide flexible ways to ingest and process all kinds of data
  structured files, unstructured text, web content, and even OCR from images.
  They power your agent’s ability to interact with the outside world. itionally,
  several data readers were added, including `Apify Reader`, `Chunkr Reader`,
  `Firecrawl Reader`, `Jina_url Reader`, and `Mistral Reader`, which enable
  retrieval of external data for improved data integration and analysis.
</Card>
## Types

<AccordionGroup>

{" "}
<Accordion title="Base IO" icon="file">
  Handles core file input/output for formats like PDF, DOCX, HTML, and more.<br></br>
  Lets you represent, read, and process structured files.
</Accordion>

{" "}
<Accordion title="Unstructured IO" icon="puzzle">
  Powerful ETL for parsing, cleaning, extracting, chunking, and staging
  unstructured data.<br></br>
  Perfect for RAG pipelines and pre-processing.
</Accordion>

{" "}
<Accordion title="Apify Reader" icon="robot">
  Integrates with Apify to automate web workflows and scraping.<br></br>
  Supports authentication, actor management, and dataset operations via API.
</Accordion>

{" "}
<Accordion title="Chunkr Reader" icon="scissors">
  Connects to the Chunkr API for document chunking, segmentation, and OCR.<br></br>
  Handles everything from simple docs to scanned PDFs.
</Accordion>

{" "}
<Accordion title="Firecrawl Reader" icon="fire">
  Converts entire websites into LLM-ready markdown using the Firecrawl API.<br></br>
  Useful for quickly ingesting web content as clean text.
</Accordion>

{" "}
<Accordion title="JinaURL Reader" icon="globe">
  Uses Jina AI’s URL reading service to cleanly extract web content.<br></br>
  Designed for LLM-friendly extraction from any URL.
</Accordion>

{" "}
<Accordion title="MarkitDown Reader" icon="note">
  Lightweight tool to convert files (HTML, DOCX, PDF, etc.) into Markdown.<br></br>
  Ideal for prepping documents for LLM ingestion or analysis.
</Accordion>

{" "}
<Accordion title="Mistral Reader" icon="book-open-reader">
  Integrates Mistral AI’s OCR service for extracting text from images and PDFs.
  <br></br>
  Supports both local and remote file processing for various formats.
</Accordion>

</AccordionGroup>

## Get Started

<Card title="Using Base IO" icon="file">
This module is designed to read files of various formats, extract their contents, and represent them as `File` objects, each tailored to handle a specific file type.

<CodeGroup>
```python base_io_example.py
from io import BytesIO
from camel.loaders import create_file_from_raw_bytes

# Read a pdf file from disk

with open("test.pdf", "rb") as file:
file_content = file.read()

# Use the create_file function to create an object based on the file extension

file_obj = create_file_from_raw_bytes(file_content, "test.pdf")

# Once you have the File object, you can access its content

print(file_obj.docs[0]["page_content"])

````
</CodeGroup>
</Card>

---

<Card title="Using Unstructured IO" icon="puzzle">
To get started with the <code>Unstructured IO</code> module, just import and initialize it. You can parse, clean, extract, chunk, and stage data from files or URLs. Here’s how you use it step by step:

<br />

<strong>1. Parse unstructured data from a file or URL:</strong>
<CodeGroup>
```python unstructured_io_parse.py
from camel.loaders import UnstructuredIO

uio = UnstructuredIO()
example_url = (
    "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
    "philadelphia-eagles-spt-intl/index.html"
)
elements = uio.parse_file_or_url(example_url)
print(("\n\n".join([str(el) for el in elements])))
````

```markdown parsed_elements.md
> > > The Empire State Building was lit in green and white to celebrate the Philadelphia Eagles’ victory in the NFC Championship game on Sunday – a decision that’s sparked a bit of a backlash in the Big Apple.
> > > The Eagles advanced to the Super Bowl for the first time since 2018 after defeating the San Francisco 49ers 31-7, and the Empire State Building later tweeted how it was marking the occasion.
> > > Fly @Eagles Fly! We’re going Green and White in honor of the Eagles NFC Championship Victory. pic.twitter.com/RNiwbCIkt7— Empire State Building (@EmpireStateBldg)
> > > January 29, 2023...
```

</CodeGroup>

<br />

<strong>2. Clean unstructured text data:</strong>
<CodeGroup>
  ```python unstructured_io_clean.py example_dirty_text = ("\x93Some dirty text
  â€™ with extra spaces and – dashes.") options = [ ('replace_unicode_quotes',{" "}
  {}), ('clean_dashes', {}), ('clean_non_ascii_chars', {}),
  ('clean_extra_whitespace', {}), ] cleaned_text =
  uio.clean_text_data(text=example_dirty_text, clean_options=options)
  print(cleaned_text) ``` ```markdown cleaned_text.md >>> Some dirty text with
  extra spaces and dashes. ```
</CodeGroup>

<br />

<strong>3. Extract data from text (for example, emails):</strong>
<CodeGroup>
```python unstructured_io_extract.py
example_email_text = "Contact me at example@email.com."

extracted_text = uio.extract_data_from_text(
text=example_email_text,
extract_type="extract_email_address"
)
print(extracted_text)

````
```markdown extracted_email.md
>>> ['example@email.com']
````

</CodeGroup>

<br />

<strong>4. Chunk content by title:</strong>
<CodeGroup>
```python unstructured_io_chunk.py
chunks = uio.chunk_elements(elements=elements, chunk_type="chunk_by_title")

for chunk in chunks:
print(chunk)
print("\n" + "-" \* 80)

````
```markdown chunked_content.md
>>> The Empire State Building was lit in green and white to celebrate the Philadelphia Eagles’ victory in the NFC Championship game on Sunday – a decision that’s sparked a bit of a backlash in the Big Apple.
>>> --------------------------------------------------------------------------------
>>> Fly @Eagles Fly! We’re going Green and White in honor of the Eagles NFC Championship Victory. pic.twitter.com/RNiwbCIkt7— Empire State Building (@EmpireStateBldg)
>>> --------------------------------------------------------------------------------
>>> January 29, 2023
````

</CodeGroup>

<br />

<strong>5. Stage elements for use with other platforms:</strong>
<CodeGroup>
```python unstructured_io_stage.py
staged_element = uio.stage_elements(elements=elements, stage_type="stage_for_baseplate")
print(staged_element)
```
```markdown staged_elements.md
>>> {'rows': [{'data': {'type': 'UncategorizedText', 'element_id': 'e78902d05b0cb1e4c38fc7a79db450d5', 'text': 'CNN\n        \xa0—'}, 'metadata': {'filetype': 'text/html', 'languages': ['eng'], 'page_number': 1, 'url': 'https://www.cnn.com/2023/01/30/sport/empire-state-building-green-philadelphia-eagles-spt-intl/index.html', 'emphasized_text_contents': ['CNN'], 'emphasized_text_tags': ['span']}}, ...
```
</CodeGroup>

<br />
This guide gets you started with <code>Unstructured IO</code>. For more, see the <a href="https://docs.unstructured.io" target="_blank">Unstructured IO Documentation</a>.
</Card>

---

<Card title="Using Apify Reader" icon="robot">
Initialize the Apify client, set up the required actors and parameters, and run the actor.

<CodeGroup>
```python apify_reader.py
from camel.loaders import Apify

apify = Apify()

run_input = {
"startUrls": [{"url": "https://www.camel-ai.org/"}],
"maxCrawlDepth": 0,
"maxCrawlPages": 1,
}
actor_result = apify.run_actor(
actor_id="apify/website-content-crawler", run_input=run_input
)
dataset_result = apify.get_dataset_items(
dataset_id=actor_result["defaultDatasetId"]
)
print(dataset_result)

````
```markdown apify_output.md
>>>[{'url': 'https://www.camel-ai.org/', 'crawl': {'loadedUrl': 'https://www.camel-ai.org/', ...}, 'metadata': {'canonicalUrl': 'https://www.camel-ai.org/', ...}, ... }]
````

</CodeGroup>
</Card>

---

<Card title="Using Firecrawl Reader" icon="fire">
Firecrawl Reader provides a simple way to turn any website into LLM-ready markdown format. Here’s how you can use it step by step:

<Steps>
  <Step title="Initialize the Firecrawl client and start a crawl">
    First, create a Firecrawl client and crawl a specific URL.

    <CodeGroup>
    ```python firecrawl_crawl.py
    from camel.loaders import Firecrawl

    firecrawl = Firecrawl()
    response = firecrawl.crawl(url="https://www.camel-ai.org/about")
    print(response["status"])  # Should print "completed" when done
    ```
    ```markdown crawl_status.md
    >>>completed
    ```
    </CodeGroup>
    When the status is <code>"completed"</code>, the content extraction is done and you can retrieve the results.

  </Step>

  <Step title="Retrieve the extracted markdown content">
    Once finished, access the LLM-ready markdown directly from the response:

    <CodeGroup>
    ```python firecrawl_markdown.py
    print(response["data"][0]["markdown"])
    ```
    ```markdown extracted_markdown.md
    >>>Camel-AI Team

    We are finding the
    scaling law of agent

    🐫 CAMEL is an open-source library designed for the study of autonomous and
    communicative agents. We believe that studying these agents on a large scale
    offers valuable insights into their behaviors, capabilities, and potential
    risks. To facilitate research in this field, we implement and support various
    types of agents, tasks, prompts, models, and simulated environments.

    **We are** always looking for more **contributors** and **collaborators**.
    Contact us to join forces via [Slack](https://join.slack.com/t/camel-kwr1314/
    shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA)
    or [Discord](https://discord.gg/CNcNpquyDc)...
    ```
    </CodeGroup>

  </Step>
</Steps>

<br />
That’s it. With just a couple of lines, you can turn any website into clean markdown, ready for LLM pipelines or further processing.
</Card>

---

<Card title="Using Chunkr Reader" icon="cuttlefish">
Chunkr Reader allows you to process PDFs (and other docs) in chunks, with built-in OCR and format control.  
Below is a basic usage pattern:

Initialize the `ChunkrReader` and `ChunkrReaderConfig`, set the file path and chunking options, then submit your task and fetch results:

```python
import asyncio
from camel.loaders import ChunkrReader, ChunkrReaderConfig

async def main():
    chunkr = ChunkrReader()

    config = ChunkrReaderConfig(
        chunk_processing=512,      # Example: target chunk length
        ocr_strategy="Auto",       # Example: OCR strategy
        high_resolution=False      # False for faster processing (old "Fast" model)
    )

    # Replace with your actual file path.
    file_path = "/path/to/your/document.pdf"
    try:
        task_id = await chunkr.submit_task(
            file_path=file_path,
            chunkr_config=config,
        )
        print(f"Task ID: {task_id}")

        # Poll and fetch the output.
        if task_id:
            task_output_json_str = await chunkr.get_task_output(task_id=task_id)
            if task_output_json_str:
                print("Task Output:")
                print(task_output_json_str)
            else:
                print(f"Failed to get output for task {task_id}, or task did not succeed/was cancelled.")
    except ValueError as e:
        print(f"An error occurred during task submission or retrieval: {e}")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}. Please check the path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("To run this example, replace '/path/to/your/document.pdf' with a real file path, ensure CHUNKR_API_KEY is set, and uncomment 'asyncio.run(main())'.")
    # asyncio.run(main()) # Uncomment to run the example
```

A successful task returns a chunked structure like this:

```markdown
> > > Task ID: 7becf001-6f07-4f63-bddf-5633df363bbb
> > > Task Output:
> > > { "task_id": "7becf001-6f07-4f63-bddf-5633df363bbb", "status": "Succeeded", "created_at": "2024-11-08T12:45:04.260765Z", "finished_at": "2024-11-08T12:45:48.942365Z", "expires_at": null, "message": "Task succeeded", "output": { "chunks": [ { "segments": [ { "segment_id": "d53ec931-3779-41be-a220-3fe4da2770c5", "bbox": { "left": 224.16666, "top": 370.0, "width": 2101.6665, "height": 64.166664 }, "page_number": 1, "page_width": 2550.0, "page_height": 3300.0, "content": "Large Language Model based Multi-Agents: A Survey of Progress and Challenges", "segment_type": "Title", "ocr": null, "image": "https://chunkmydocs-bucket-prod.storage.googleapis.com/.../d53ec931-3779-41be-a220-3fe4da2770c5.jpg?...", "html": "<h1>Large Language Model based Multi-Agents: A Survey of Progress and Challenges</h1>", "markdown": "# Large Language Model based Multi-Agents: A Survey of Progress and Challenges\n\n" } ], "chunk_length": 11 }, { "segments": [ { "segment_id": "7bb38fc7-c1b3-4153-a3cc-116c0b9caa0a", "bbox": { "left": 432.49997, "top": 474.16666, "width": 1659.9999, "height": 122.49999 }, "page_number": 1, "page_width": 2550.0, "page_height": 3300.0, "content": "Taicheng Guo 1 , Xiuying Chen 2 , Yaqi Wang 3 \u2217 , Ruidi Chang , Shichao Pei 4 , Nitesh V. Chawla 1 , Olaf Wiest 1 , Xiangliang Zhang 1 \u2020", "segment_type": "Text", "ocr": null, "image": "https://chunkmydocs-bucket-prod.storage.googleapis.com/.../7bb38fc7-c1b3-4153-a3cc-116c0b9caa0a.jpg?...", "html": "<p>Taicheng Guo 1 , Xiuying Chen 2 , Yaqi Wang 3 \u2217 , Ruidi Chang , Shichao Pei 4 , Nitesh V. Chawla 1 , Olaf Wiest 1 , Xiangliang Zhang 1 \u2020</p>", "markdown": "Taicheng Guo 1 , Xiuying Chen 2 , Yaqi Wang 3 \u2217 , Ruidi Chang , Shichao Pei 4 , Nitesh V. Chawla 1 , Olaf Wiest 1 , Xiangliang Zhang 1 \u2020\n\n" } ], "chunk_length": 100 } ] } }
```

</Card>

---

<Card title="Using Jina Reader" icon="link">
Jina Reader provides a convenient interface to extract clean, LLM-friendly content from any URL in a chosen format (like markdown):

```python
from camel.loaders import JinaURLReader
from camel.types.enums import JinaReturnFormat

jina_reader = JinaURLReader(return_format=JinaReturnFormat.MARKDOWN)
response = jina_reader.read_content("https://docs.camel-ai.org/")
print(response)
```

</Card>

---

<Card title="Using MarkitDown Reader" icon="notebook">
MarkitDown Reader lets you convert files (like HTML or docs) into LLM-ready markdown with a single line.

```python
from camel.loaders import MarkItDownLoader

loader = MarkItDownLoader()
response = loader.convert_file("demo.html")

print(response)
```

Example output:

```markdown
> > > Welcome to CAMEL’s documentation! — CAMEL 0.2.61 documentation

[Skip to main content](https://docs.camel-ai.org/#main-content)
...
```

</Card>

---

<Card title="Using Mistral Reader" icon="book-open-reader">
Mistral Reader offers OCR and text extraction from both PDFs and images, whether local or remote. Just specify the file path or URL:

```python
from camel.loaders import MistralReader

mistral_reader = MistralReader()

# Extract text from a PDF URL
url_ocr_response = mistral_reader.extract_text(
    file_path="https://arxiv.org/pdf/2201.04234", pages=[5]
)
print(url_ocr_response)
```

You can also extract from images or local files:

```python
# Extract text from an image URL
image_ocr_response = mistral_reader.extract_text(
    file_path="https://raw.githubusercontent.com/mistralai/cookbook/refs/heads/main/mistral/ocr/receipt.png",
    is_image=True,
)
print(image_ocr_response)
```

```python
# Extract text from a local PDF file
local_ocr_response = mistral_reader.extract_text("path/to/your/document.pdf")
print(local_ocr_response)
```

Response includes structured page data, markdown content, and usage details.

```markdown
> > > pages=[OCRPageObject(index=5, markdown='![img-0.jpeg](./images/img-0.jpeg)\n\nFigure 2: Scatter plot of predicted accuracy versus (true) OOD accuracy. Each point denotes a dif...',
> > > images=[OCRImageObject(id='img-0.jpeg', ...)], dimensions=OCRPageDimensions(...))] model='mistral-ocr-2505-completion' usage_info=...
```

</Card>
