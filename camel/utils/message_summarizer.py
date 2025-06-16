import json
from typing import List, Optional, Union
from pydantic import BaseModel

from camel.messages import BaseMessage
from camel.agents import ChatAgent
from camel.types import ModelType
from camel.utils.response_format import model_from_json_schema


class SummarySchema(BaseModel):
    """Schema for structured message summaries.
    
    Attributes:
        roles (List[str]): The roles involved in the conversation
        key_entities (List[str]): Important entities/concepts discussed
        decisions (List[str]): Key decisions or conclusions reached
        task_progress (str): Summary of progress made on the main task
        context (str): Additional relevant contextual information
    """
    roles: List[str]
    key_entities: List[str] 
    decisions: List[str]
    task_progress: str
    context: str


class MessageSummarizer:
    """Utility class for generating structured summaries of chat messages.
    
    Args:
        model (Union[str, ModelType], optional): The model to use for summarization.
            Defaults to ModelType.DEFAULT.
    """
    
    def __init__(
        self,
        model: Optional[Union[str, ModelType]] = None,
    ):
        self.model = model or ModelType.GPT_4O_MINI
        self.agent = ChatAgent(
            system_message="""You are a skilled conversation summarizer. 
            Your task is to analyze chat messages and create structured summaries that capture:
            - The key roles involved
            - Important entities and concepts discussed
            - Key decisions or conclusions reached
            - Progress made on the main task
            - Relevant contextual information
            
            Provide summaries that are concise while preserving critical information.""",
            model=self.model
        )

    def summarize(self, messages: List[BaseMessage]) -> SummarySchema:
        """Generate a structured summary of the provided messages.
        
        Args:
            messages (List[BaseMessage]): List of messages to summarize
            
        Returns:
            SummarySchema: Structured summary of the conversation
            
        Raises:
            ValueError: If the model's response cannot be parsed as valid JSON
        """
        # When messages is empty
        if len(messages) == 0:
            return SummarySchema(
                roles=[],
                key_entities=[],
                decisions=[],
                task_progress="",
                context=""
            )
        
        # Define the expected response schema
        response_schema = {
            "type": "object",
            "required": ["roles", "key_entities", "decisions", "task_progress", "context"],
            "properties": {
                "roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of roles involved in the conversation"
                },
                "key_entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of important entities/concepts discussed"
                },
                "decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key decisions or conclusions reached"
                },
                "task_progress": {
                    "type": "string",
                    "description": "Summary of progress made on the main task"
                },
                "context": {
                    "type": "string",
                    "description": "Additional relevant contextual information"
                }
            }
        }
        
        # Create a Pydantic model from the schema
        ResponseModel = model_from_json_schema("ResponseModel", response_schema)

        # Construct prompt from messages
        message_text = "\n".join(
            f"{msg.role_name}: {msg.content}" for msg in messages
        )
        prompt = f"""Please analyze these messages and provide a structured summary:

{message_text}

Your response must be a JSON object with these fields:
- roles: list of roles involved
- key_entities: list of important entities/concepts
- decisions: list of key decisions made
- task_progress: summary of progress on main task
- context: additional relevant context"""

        # Get structured summary from model with forced JSON response
        response = self.agent.step(
            prompt,
            response_format=ResponseModel
        )
        try:
            # The response should already be validated by the model
            # return SummarySchema(**response.msg.content)
            content = response.msg.content
            if isinstance(content, str):
                content = json.loads(content)
            return SummarySchema(**content)
        except Exception as e:
            raise ValueError(f"Response validation failed: {str(e)}")
