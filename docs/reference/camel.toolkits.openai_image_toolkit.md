<a id="camel.toolkits.openai_image_toolkit"></a>

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit"></a>

## OpenAIImageToolkit

```python
class OpenAIImageToolkit(BaseToolkit):
```

A class toolkit for image generation using OpenAI's
Image Generation API.

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    model: Optional[Literal['gpt-image-1', 'dall-e-3', 'dall-e-2']] = 'gpt-image-1',
    timeout: Optional[float] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    size: Optional[Literal['256x256', '512x512', '1024x1024', '1536x1024', '1024x1536', '1792x1024', '1024x1792', 'auto']] = '1024x1024',
    quality: Optional[Literal['auto', 'low', 'medium', 'high', 'standard', 'hd']] = 'standard',
    response_format: Optional[Literal['url', 'b64_json']] = 'b64_json',
    background: Optional[Literal['transparent', 'opaque', 'auto']] = 'auto',
    style: Optional[Literal['vivid', 'natural']] = None,
    working_directory: Optional[str] = 'image_save'
):
```

Initializes a new instance of the OpenAIImageToolkit class.

**Parameters:**

- **api_key** (Optional[str]): The API key for authenticating with the OpenAI service. (default: :obj:`None`)
- **url** (Optional[str]): The url to the OpenAI service. (default: :obj:`None`)
- **model** (Optional[str]): The model to use. (default: :obj:`"dall-e-3"`)
- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`) size (Optional[Literal["256x256", "512x512", "1024x1024", "1536x1024", "1024x1536", "1792x1024", "1024x1792", "auto"]]): The size of the image to generate. (default: :obj:`"1024x1024"`) quality (Optional[Literal["auto", "low", "medium", "high", "standard", "hd"]]):The quality of the image to generate. Different models support different values. (default: :obj:`"standard"`)
- **response_format** (`Optional[Literal["url", "b64_json"]]`): The format of the response.(default: :obj:`"b64_json"`)
- **background** (`Optional[Literal["transparent", "opaque", "auto"]]`): The background of the image.(default: :obj:`"auto"`)
- **style** (`Optional[Literal["vivid", "natural"]]`): The style of the image.(default: :obj:`None`)
- **working_directory** (Optional[str]): The path to save the generated image.(default: :obj:`"image_save"`)

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit.base64_to_image"></a>

### base64_to_image

```python
def base64_to_image(self, base64_string: str):
```

Converts a base64 encoded string into a PIL Image object.

**Parameters:**

- **base64_string** (str): The base64 encoded string of the image.

**Returns:**

  Optional[Image.Image]: The PIL Image object or None if conversion
fails.

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit._build_base_params"></a>

### _build_base_params

```python
def _build_base_params(self, prompt: str):
```

Build base parameters dict for OpenAI API calls.

**Parameters:**

- **prompt** (str): The text prompt for the image operation.

**Returns:**

  dict: Parameters dictionary with non-None values.

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit._handle_api_response"></a>

### _handle_api_response

```python
def _handle_api_response(
    self,
    response,
    image_name: str,
    operation: str
):
```

Handle API response from OpenAI image operations.

**Parameters:**

- **response**: The response object from OpenAI API.
- **image_name** (str): Name for the saved image file.
- **operation** (str): Operation type for success message ("generated").

**Returns:**

  str: Success message with image path/URL or error message.

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit.generate_image"></a>

### generate_image

```python
def generate_image(self, prompt: str, image_name: str = 'image'):
```

Generate an image using OpenAI's Image Generation models.
The generated image will be saved locally (for `__INLINE_CODE_0__` response
formats) or an image URL will be returned (for `__INLINE_CODE_1__` response
formats).

**Parameters:**

- **prompt** (str): The text prompt to generate the image.
- **image_name** (str): The name of the image to save. (default: :obj:`"image"`)

**Returns:**

  str: the content of the model response or format of the response.

<a id="camel.toolkits.openai_image_toolkit.OpenAIImageToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
