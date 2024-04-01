# Introduction to `MultiModalPrompt` Class

## Overview

The `MultiModalPrompt` class streamlines the process of creating integrated prompts for multimodal agents. By bringing together text and other modalities, it establishes a unified structure for communication.

## Supported Modalities

As of now, the class recognizes the following modality:
- `CAMEL_IMAGE`

## Initialization

To initialize a `MultiModalPrompt` instance:

```python
from camel.prompts import MultiModalPrompt, TextPrompt

vqa_prompt = MultiModalPrompt(
    text_prompt=TextPrompt("Please answer the following question related to the provided image:\nQuestion: {Question}"),
    modalities=["CAMEL_IMAGE"]
)
```

**Arguments**:
- `text_prompt` (TextPrompt): The text-based template. It dictates the format of the text segment of the prompt.
- `modalities` (Union[List, Dict]): Either a list of modality names or a dictionary pairing modality names with their respective data. If the input is a dictionary, it should follow the pattern `{Modality Name: Modality Data}`.

## Methods

### `format(*args, **kwargs) -> 'MultiModalPrompt'`

This method concurrently formats both the text and multimodal components. Once formatted, the output is a new `MultiModalPrompt` instance.

```python
vqa_prompt = MultiModalPrompt(
    text_prompt=TextPrompt("Please anwser the following question about the given image:\nQuestion: {Question}"),
    modalities=["CAMEL_IMAGE"]
    )

question = "What animal is in the picture?"
image_path = "examples/multimodal/camel.jpg"

vqa_prompt = vqa_prompt.format(Question=question, CAMEL_IMAGE=image_path)
# the prompt is now an instance of MultiModalPrompt, initializing with all multimodal information, and can be used to generate model input when the to_model_format method is called
```

### `to_model_format(method=default_to_model_format) -> Any`

Transforms the prompt to a format understood by the multimodal model.

By default, this method returns the prompt as a dictionary. However, by specifying a different `model_format` method, the output can be adapted to various multimodal model requirements.

```python
def default_to_model_format(text_prompt, modalities_dict: Dict) -> Dict:
    r"""
    The default format is return the text and multimodal information in dict.
    This function should be implemented in the multimodal prompt class.

    Returns:
        dict: The input format that the multimodal model can understand.
    """

    return {"text": text_prompt, "multimodal_information": modalities_dict}

vqa_prompt = MultiModalPrompt(
        text_prompt=TextPrompt("Please anwser the following question about the given image:\nQuestion: {Question}"),
        modalities=["CAMEL_IMAGE"]
        )

question = "What animal is in the picture?"
image_path = "examples/multimodal/camel.jpg"

vqa_prompt = vqa_prompt.format(Question=question, CAMEL_IMAGE=image_path)


print(vqa_prompt.to_model_format(default_to_model_format))
# {'text': 'Please anwser the following question about the given image:\nQuestion: What animal is in the picture?', 'multimodal_information': {'CAMEL_IMAGE': 'examples/multimodal/camel.jpg'}}
```

## Usage Examples

We provide an example in `camel/examples/multimodal/formating_example.py` which you can directly run to see the output.

### 1. Single Image VQA (Visual Question Answering):

This example illustrates how to generate prompts for a Visual Question Answering task associated with a single image.

```python
from camel.prompts import MultiModalPrompt, TextPrompt

# Create a VQA prompt template
vqa_prompt = MultiModalPrompt(
    text_prompt=TextPrompt("Please answer the following question about the given image:\nQuestion: {Question}"),
    modalities=["CAMEL_IMAGE"]
)

# Define questions and their respective image paths
question1 = "What animal is in the picture?"
question2 = "What is the color of the animal?"
image1_path = "examples/multimodal/camel.jpg"
image2_path = "examples/multimodal/llama.jpg"

# Format and display the prompts
vqa_prompt1 = vqa_prompt.format(Question=question1, CAMEL_IMAGE=image1_path)
vqa_prompt2 = vqa_prompt.format(Question=question2, CAMEL_IMAGE=image2_path)

print("vqa_prompt1:", vqa_prompt1.to_model_format())
# {'text': 'Please anwser the following question about the given image:\nQuestion: What animal is in the picture?', 'multimodal_information': {'CAMEL_IMAGE': 'examples/multimodal/camel.jpg'}}
print("vqa_prompt2:", vqa_prompt2.to_model_format())
# {'text': 'Please anwser the following question about the given image:\nQuestion: What is the color of the animal?', 'multimodal_information': {'CAMEL_IMAGE': 'examples/multimodal/llama.jpg'}}
```

### 2. Multi-Image Question with a Custom Model Input:

This showcases the creation of a prompt involving multiple images for a single question. Furthermore, it illustrates how to adapt the prompt to a model-specific format.

```python
def multi_image_input_format(text_prompt, modalities_dict):
    """ 
    Label each image in the prompt with numbers.
    """
    if not isinstance(modalities_dict["CAMEL_IMAGE"], List):
        modalities_dict["CAMEL_IMAGE"] = [modalities_dict["CAMEL_IMAGE"]]

    for i, image in enumerate(modalities_dict["CAMEL_IMAGE"]):
        text_prompt = f"Image {i} is <Image{i}> [Image{i}]\n" + text_prompt

    return {"prompt": text_prompt, "image": modalities_dict["CAMEL_IMAGE"]}

# Define the multi-image question and format the prompt
question3 = "Are the animals from the two images the same?"
multi_image_prompt = vqa_prompt.format(Question=question3, CAMEL_IMAGE=[image1_path, image2_path])

# Display the multi-image prompt and its corresponding images
model_input = multi_image_prompt.to_model_format(multi_image_input_format)

print("Prompt:", model_input["prompt"])
'''
Image 1 is <Image1> [Image1]
Image 0 is <Image0> [Image0]
Please anwser the following question about the given image:
Question: Are the animals from the two images the same?
'''


print("Images:", model_input["image"])
'''
['examples/multimodal/camel.jpg', 'examples/multimodal/llama.jpg']
'''

```

## Application with different multimodal models


### LLAVA-1.5

- TODO: add examples of how to use the multimodal prompt with different multimodal models with simple VL tasks.
