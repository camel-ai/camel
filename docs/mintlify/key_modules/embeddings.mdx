---
title: "Embeddings"
icon: vector-square
---

<Card title="What Are Embeddings??" icon="file-vector">
  Embeddings transform text, images, and other media into dense numeric vectors
  that capture their underlying meaning. This makes it possible for machines to
  perform semantic search, similarity, recommendations, clustering, RAG, and
  more.
</Card>

<Card title="How Text & Image Embeddings Work" icon="question">
Text embeddings turn sentences or documents into high-dimensional vectors that capture meaning.  
Example:  
<ul>
  <li>“A young boy is playing soccer in a park.”</li>
  <li>“A child is kicking a football on a playground.”</li>
</ul>
These sentences get mapped to similar vectors, letting your AI recognize their meaning, regardless of wording.

Image embeddings use neural networks (like CNNs) or vision-language models to turn images into numeric vectors, capturing shapes, colors, and features. For example: A cat image → vector that is “close” to other cats and “far” from cars in vector space.

</Card>

## Supported Embedding Types

<CardGroup cols={2}>
  <Card title="OpenAIEmbedding" icon="cloud">
    Use OpenAI’s API to generate text embeddings.
    <br />
    <b>Requires:</b> OpenAI API Key.
  </Card>
  <Card title="MistralEmbedding" icon="wind">
    Use Mistral’s API for text embeddings.
    <br />
    <b>Requires:</b> Mistral API Key.
  </Card>
  <Card title="SentenceTransformerEncoder" icon="align-left">
    Local, open-source transformer models from the{" "}
    <a href="https://www.sbert.net" target="_blank">
      Sentence Transformers
    </a>{" "}
    library.
  </Card>
  <Card title="VisionLanguageEmbedding" icon="image">
    OpenAI’s vision models for image embeddings.
    <br />
    <b>Requires:</b> OpenAI API Key.
  </Card>
  <Card title="AzureOpenAI" icon="cloud">
    Text embeddings from OpenAI models on Azure.
    <br />
    <b>Requires:</b> Azure OpenAI API Key.
  </Card>
  <Card title="TogetherEmbedding" icon="users">
    Together AI’s hosted models for text embeddings.
    <br />
    <b>Requires:</b> Together AI API Key.
  </Card>
</CardGroup>

## Usage Examples

<Note>
  Make sure you have the right API key set (OpenAI, Mistral, Azure, or Together)
  for the embedding backend you want to use.
</Note>

<Card title="Text Embeddings with OpenAI" icon="cloud">
<CodeGroup>
```python openai_embed.py
from camel.embeddings import OpenAIEmbedding
from camel.types import EmbeddingModelType

openai_embedding = OpenAIEmbedding(model_type=EmbeddingModelType.TEXT_EMBEDDING_3_SMALL)
embeddings = openai_embedding.embed_list(["Hello, world!", "Another example"])

````
</CodeGroup>
</Card>

<Card title="Text Embeddings with Mistral" icon="wind">
<CodeGroup>
```python mistral_embed.py
from camel.embeddings import MistralEmbedding
from camel.types import EmbeddingModelType

mistral_embedding = MistralEmbedding(model_type=EmbeddingModelType.MISTRAL_EMBED)
embeddings = mistral_embedding.embed_list(["Hello, world!", "Another example"])
````

</CodeGroup>
</Card>

<Card title="Local Sentence Transformers" icon="align-left">
<CodeGroup>
```python sentence_transformer_embed.py
from camel.embeddings import SentenceTransformerEncoder

sentence_encoder = SentenceTransformerEncoder(model_name='intfloat/e5-large-v2')
embeddings = sentence_encoder.embed_list(["Hello, world!", "Another example"])

````
</CodeGroup>
</Card>

<Card title="Image Embeddings with Vision-Language Models" icon="image">
<CodeGroup>
```python image_embed.py
from camel.embeddings import VisionLanguageEmbedding
from PIL import Image
import requests

vlm_embedding = VisionLanguageEmbedding()
url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image = Image.open(requests.get(url, stream=True).raw)
test_images = [image, image]
embeddings = vlm_embedding.embed_list(test_images)
````

</CodeGroup>
</Card>

<Card title="Text Embeddings with Azure OpenAI" icon="cloud">
<CodeGroup>
```python azure_embed.py
from camel.embeddings import AzureEmbedding
from camel.types import EmbeddingModelType

azure_openai_embedding = AzureEmbedding(model_type=EmbeddingModelType.TEXT_EMBEDDING_ADA_2)
embeddings = azure_openai_embedding.embed_list(["Hello, world!", "Another example"])

````
</CodeGroup>
</Card>

<Card title="Text Embeddings with Together AI" icon="users">
<CodeGroup>
```python together_embed.py
from camel.embeddings import TogetherEmbedding

together_embedding = TogetherEmbedding(model_type="togethercomputer/m2-bert-80M-8k-retrieval")
embeddings = together_embedding.embed_list(["Hello, world!", "Another example"])
````

</CodeGroup>
</Card>

<Tip>
  Pick a text embedding that matches your language, latency, and privacy needs.
  For multimodal use cases, use image or vision-language embeddings.
</Tip>

<CardGroup cols={2}>
  <Card title="See Example Workflows" icon="rocket" href="/cookbooks/">
    Explore retrieval-augmented generation (RAG) and search recipes using
    embeddings.
  </Card>
  <Card
    title="All Supported Embedding APIs"
    icon="link"
    href="/reference/#embeddings"
  >
    Full API docs and all configuration options.
  </Card>
</CardGroup>
