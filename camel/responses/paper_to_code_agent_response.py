from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict
from camel.responses import ChatAgentResponse


class PaperToCodeAgentResponse(BaseModel):

    action_phase: Optional[str] = Field(
        default=None,
        description="The phase of the action producing this response.",
    )
    content: List[ChatAgentResponse] = Field(
        default_factory=list,
        description="General textual content of the response.",
    )
    terminated: bool = Field(
        default=False,
        description="Indicates if the current task or sub-task is terminated.",
    )

    # Pydantic V2 model configuration using ConfigDict
    # This ensures compatibility with Pydantic V2 and allows for future
    # model-specific configurations.
    model_config = ConfigDict(
        validate_assignment=True,  # Example: enables validation on assignment
        # json_schema_extra can be added here if needed for OpenAPI schemas
        # For example:
        # json_schema_extra={
        #     "example": {
        #         "action_phase": "code_generation",
        #         "content": "Generated Python code for data analysis.",
        #         "code": "import pandas as pd\n\ndf = pd.read_csv('data.csv')",
        #         "generated_files": ["analysis_script.py"],
        #         "terminated": False,
        #         "info": {"execution_time_ms": 1200}
        #     }
        # }
    )
