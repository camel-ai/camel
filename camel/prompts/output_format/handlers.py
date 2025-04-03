# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Optional, Set

from camel.prompts.output_format.base import (
    OutputFormat,
    OutputFormatHandler
)
from camel.prompts.output_format.extractors import (
    DirectExtractor,
    JsonDirectExtractor,
    JsonCodeBlockExtractor
)
from camel.prompts.output_format.validators import (
    JsonRequiredKeysValidator,
)
from camel.types.enums import OutputFormatType


class DefaultOutputFormatHandler(OutputFormatHandler):
    """Default output format handler that directly returns the input text."""
    
    def __init__(
        self, 
        **kwargs
    ) -> None:
        """Initialize the default output format handler.
        
        Args:
            output_format (Optional[OutputFormat]): Output format. If None, TEXT type is used.
            **kwargs: Additional parameters, ignored
        """
        super().__init__(OutputFormat(OutputFormatType.TEXT),
                         extractors=[DirectExtractor()], 
                         validators=[])

class JsonOutputFormatHandler(OutputFormatHandler):
    """JSON output format handler."""
    
    def __init__(
        self,
        required_keys: Optional[Set[str]] = None,
        **kwargs
    ) -> None:
        """Initialize the JSON output format handler.
        
        Args:
            required_keys (Optional[Set[str]]): Set of required keys
            **kwargs: Additional parameters, ignored
        """
        self.required_keys = required_keys
        super().__init__(OutputFormat(OutputFormatType.JSON), 
                         extractors=[JsonDirectExtractor(),JsonCodeBlockExtractor()], 
                         validators=[JsonRequiredKeysValidator(required_keys)])
