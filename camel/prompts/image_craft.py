from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.types import RoleType


class ImageCraftPromptTemplateDict(TextPromptDict):
    ASSISTANT_PROMPT = TextPrompt(
        """You are tasked with creating an original image based on the provided descriptive captions. 
Please use your imagination and artistic capabilities to visualize and draw the scenes described below. 
Ensure that the elements and actions mentioned in the captions are accurately represented in your artwork. 
Remember to pay attention to the details and mood of the scenes to make the images engaging and true to the descriptions. """)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
        })
