# Loaders

## 1. Concept
CAMEL introduced two IO modules, `Base IO` and `Unstructured IO` which are designed for handling various file types and unstructured data processing.
Additionally, four new data readers were added, `Apify Reader`,`Chunkr Reader`, `Firecrawl Reader`, and `Jina_url Reader`, which enable retrieval of external data for improved data integration and analysis.

## 2. Types

### 2.1. Base IO
Base IO module is focused on fundamental input/output operations related to files. It includes functionalities for representing, reading, and processing different file formats.

### 2.2. Unstructured IO
Unstructured IO module deals with the handling, parsing, and processing of unstructured data. It provides tools for parsing files or URLs, cleaning data, extracting specific information, staging elements for different platforms, and chunking elements. The core of this module lies in its advanced ETL capabilities to manipulate unstructured data to make it usable for various applications like Retrieval-Augmented Generation(RAG).

### 2.3. Apify Reader
Apify Reader provides a Python interface to interact with the Apify platform for automating web workflows. It allows users to authenticate via an API key and offers methods to execute and manage actors (automated web tasks) and datasets on the platform.
It includes functionalities for client initialization, actor management, dataset operation.

### 2.4. Chunkr Reader
Chunkr Reader is a Python client for interacting with the Chunkr API, which processes documents and returns content in various formats. It includes functionalities for client intialization, task management, formating response.

### 2.5. Firecrawl Reader
Firecrawl Reader provides a Python interface to interact with the Firecrawl API, allowing users to turn websites into large language model (LLM)-ready markdown format.

### 2.6. Jina_url Reader
JinaURL Reader is a Python client for Jina AI's URL reading service, optimized to provide cleaner, LLM-friendly content from URLs. 

## 3. Get Started

### 3.1. Using `Base IO`

This module is designed to read files of various formats, extract their contents, and represent them as `File` objects, each tailored to handle a specific file type.

```python
from io import BytesIO
from camel.loaders import read_file

# Read a pdf file from disk
with open("test.pdf", "rb") as file:
    file_content = BytesIO(file.read())
    file_content.name = "test.pdf"

# Use the read_file function to create an object based on the file extension
file_obj = read_file(file_content)

# Once you have the File object, you can access its content
print(file_obj.docs[0]["page_content"])
```

### 3.2. Using `Unstructured IO`

To get started with the `Unstructured IO` module, you first need to import the module and initialize an instance of it. Once initialized, you can utilize this module to handle a variety of functionalities such as parsing, cleaning, extracting data, and integrating with cloud services like AWS S3 and Azure. Here's a basic guide to help you begin:

Utilize `parse_file_or_url` to load and parse unstructured data from a file or URL
```python
# Set example url
example_url = (
    "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
    "philadelphia-eagles-spt-intl/index.html")
elements = uio.parse_file_or_url(example_url)
print(("\n\n".join([str(el) for el in elements])))
```
```markdown
>>> The Empire State Building was lit in green and white to celebrate the Philadelphia Eagles’ victory in the NFC Championship game on Sunday – a decision that’s sparked a bit of a backlash in the Big Apple.

>>>  The Eagles advanced to the Super Bowl for the first time since 2018 after defeating the San Francisco 49ers 31-7, and the Empire State Building later tweeted how it was marking the occasion.

>>>  Fly @Eagles Fly! We’re going Green and White in honor of the Eagles NFC Championship Victory. pic.twitter.com/RNiwbCIkt7— Empire State Building (@EmpireStateBldg)

>>>  January 29, 2023...
```

Utilize `clean_text_data` to do various text cleaning operations
```python
# Set example dirty text
example_dirty_text = ("\x93Some dirty text â€™ with extra spaces and – dashes.")

# Set clean options   
options = [
    ('replace_unicode_quotes', {}),
    ('clean_dashes', {}),
    ('clean_non_ascii_chars', {}),
    ('clean_extra_whitespace', {}),
]

cleaned_text = uio.clean_text_data(text=example_dirty_text,clean_options=options)
print(cleaned_text)
```
```markdown
>>> Some dirty text with extra spaces and dashes.
```

Utilize `extract_data_from_text` to do text extraction operation
```python
# Set example email to extract
example_email_text = ("Contact me at example@email.com.")

extracted_text = uio.extract_data_from_text(text=example_email_text,
extract_type="extract_email_address")

print(extracted_text)
```
```markdown
>>> ['example@email.com']
```

Utilize `chunk_elements` to chunk the content
```python
chunks = uio.chunk_elements(elements=elements,chunk_type="chunk_by_title")

for chunk in chunks:
    print(chunk)
    print("\n" + "-" * 80)
```
```markdown
>>> The Empire State Building was lit in green and white to celebrate the Philadelphia Eagles’ victory in the NFC Championship game on Sunday – a decision that’s sparked a bit of a backlash in the Big Apple.

>>>  The Eagles advanced to the Super Bowl for the first time since 2018 after defeating the San Francisco 49ers 31-7, and the Empire State Building later tweeted how it was marking the occasion.

>>>  --------------------------------------------------------------------------------
>>>  Fly @Eagles Fly! We’re going Green and White in honor of the Eagles NFC Championship Victory. pic.twitter.com/RNiwbCIkt7— Empire State Building (@EmpireStateBldg)

>>>  --------------------------------------------------------------------------------
>>>  January 29, 2023
```

Utilize `stage_elements` to do element staging
```python
staged_element = uio.stage_elements(elements=elements,stage_type="stage_for_baseplate")

print(staged_element)
```
```markdown
>>> {'rows': [{'data': {'type': 'UncategorizedText', 'element_id': 'e78902d05b0cb1e4c38fc7a79db450d5', 'text': 'CNN\n        \xa0—'}, 'metadata': {'filetype': 'text/html', 'languages': ['eng'], 'page_number': 1, 'url': 'https://www.cnn.com/2023/01/30/sport/empire-state-building-green-philadelphia-eagles-spt-intl/index.html', 'emphasized_text_contents': ['CNN'], 'emphasized_text_tags': ['span']}}, ...
```
This is a basic guide to get you started with the `Unstructured IO` module. For more advanced usage, refer to the specific method documentation and the [Unstructured IO Documentation](https://unstructured-io.github.io/unstructured/).

### 3.3. Using `Apify Reader`

Initialize the client, set up the required actors and parameters.
```python
apify = Apify()

run_input = {
    "startUrls": [{"url": "https://www.camel-ai.org/"}],
    "maxCrawlDepth": 0,
    "maxCrawlPages": 1,
}
actor_result = apify.run_actor(
    actor_id="apify/website-content-crawler", run_input=run_input
)
```

Retrieve the result database ID and access it using the get_dataset_items method.
```python
dataset_result = apify.get_dataset_items(
    dataset_id=actor_result["defaultDatasetId"]
)
```
```markdown
>>>[{'url': 'https://www.camel-ai.org/', 'crawl': {'loadedUrl': 'https://www.camel
-ai.org/', 'loadedTime': '2024-10-27T04:51:16.651Z', 'referrerUrl': 'https://ww
w.camel-ai.org/', 'depth': 0, 'httpStatusCode': 200}, 'metadata': {'canonicalUr
l': 'https://www.camel-ai.org/', 'title': 'CAMEL-AI', 'description': 'CAMEL-AI.
org is the 1st LLM multi-agent framework and an open-source community dedicated
 to finding the scaling law of agents.', 'author': None, 'keywords': None, 'lan
 guageCode': 'en', 'openGraph': [{'property': 'og:title', 'content': 'CAMEL-AI'
 }, {'property': 'og:description', 'content': 'CAMEL-AI.org is the 1st LLM mult
 i-agent framework and an open-source community dedicated to finding the scalin
 g law of agents.'}, {'property': 'twitter:title', 'content': 'CAMEL-AI'}, {'pr
 operty': 'twitter:description', 'content': 'CAMEL-AI.org is the 1st LLM multi-
 agent framework and an open-source community dedicated to finding the scaling 
 law of agents.'}, {'property': 'og:type', 'content': 'website'}], 'jsonLd': No
 ne, 'headers': {'date': 'Sun, 27 Oct 2024 04:50:18 GMT', 'content-type': 'text
 /html', 'cf-ray': '8d901082dae7efbe-PDX', 'cf-cache-status': 'HIT', 'age': '10
 81', 'content-encoding': 'gzip', 'last-modified': 'Sat, 26 Oct 2024 11:51:32 G
 MT', 'strict-transport-security': 'max-age=31536000', 'surrogate-control': 'ma
 x-age=432000', 'surrogate-key': 'www.camel-ai.org 6659a154491a54a40551bc78 pag
 eId:6686a2bcb7ece5fb40457491 668181a0a818ade34e653b24 6659a155491a54a40551bd7e
 ', 'x-lambda-id': 'd6c4424b-ac67-4c54-b52a-cb2a22ca09f0', 'vary': 'Accept-Enco
 ding', 'set-cookie': '__cf_bm=oX5EmZ2SNJDOBQXI8dL_reCYlCpp1FMzu40qCNxiopU-1730
 004618-1.0.1.1-3teEeqUoemzHWAeGCtlPJVqdmAbiFkyu3JxopKfQFFndSCi_Z56RR.UDjLGZiq.
 L_4LvAZYmNKxQ.k6VRhbA7g; path=/; expires=Sun, 27-Oct-24 05:20:18 GMT; domain=.
 cdn.webflow.com; HttpOnly; Secure; SameSite=None\n_cfuvid=om_8lj9jNMIh.HEIxEAq
 gszhEWaKlyS2kdXKwqGedSM-1730004618924-0.0.1.1-604800000; path=/; domain=.cdn.w
 ebflow.com; HttpOnly; Secure; SameSite=None', 'alt-svc': 'h3=":443"; ma=86400'
 , 'x-cluster-name': 'us-west-2-prod-hosting-red', 'x-firefox-spdy': 'h2'}}, 's
 creenshotUrl': None, 'text': 'Build Multi-Agent Systems for _\nFEATURES & Inte
 grations\nSeamless integrations with\npopular platforms \nScroll to explore ou
 r features & integrations.', 'markdown': '# Build Multi-Agent Systems for \\_
 \n\nFEATURES & Integrations\n\n## Seamless integrations with  \npopular platfo
 rms\n\nScroll to explore our features & integrations.'}]
```

### 3.4. Using `Firecrawl Reader`

Initialize the client and set the URL from which we want to retrieve information. When the status is "completed," the information retrieval is finished and ready for reading.
```python
firecrawl = Firecrawl()

response = firecrawl.crawl(url="https://www.camel-ai.org/about")
print(response["status"])
```
```markdown
>>>completed
```

Directly retrieve information from the returned results.
```python
print(response["data"][0]["markdown"])
```
```markdown
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