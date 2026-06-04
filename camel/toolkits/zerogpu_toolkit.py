# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import json
from typing import Any, Dict, List, Optional, Union
import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import (
    MCPServer,
    api_keys_required
)

logger = get_logger(__name__)

@MCPServer()
class ZeroGPUToolkit(BaseToolkit):
    r"""A toolkit for interacting with ZeroGPU-hosted models.

    This toolkit provides access to a variety of lightweight AI models
    deployed on the ZeroGPU platform for tasks such as:

    - Text generation
    - Translation
    - Summarization
    - Intent detection
    - PII extraction and redaction
    - IAB content classification (ad tech)
    - Email filtering

    Each method wraps a specific ZeroGPU model and exposes it as a tool
    compatible with CAMEL agents.
    """

    @api_keys_required([
        ("api_key", "ZEROGPU_API_KEY"),
        ("project_id", "ZEROGPU_PROJECT_ID"),
    ])
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)

        self.api_key = api_key
        self.project_id = project_id
        self.base_url = base_url or "https://api.zerogpu.ai"

        # validation
        if not self.api_key.startswith("zgpu-"):
            raise ValueError("Invalid ZeroGPU API key format (must start with 'zgpu-')")

    def chat(self, text: str, system: Optional[str] = None) -> str:
        """Chat using LFM Instruct model.
        
        Args:
            text (str): The input text.
            system (Optional[str], optional): The system prompt. Defaults to None.

        Returns:
            str: The response text.
        """

        input_data = (
            [{"role": "system", "content": system}, {"role": "user", "content": text}]
            if system
            else text
        )

        payload = {
            "input": input_data,
            "model": "LFM2.5-1.2B-Instruct",
        }

        response = self._post(payload)

        if "error" in response:
            return f"Error: {response['error']}"

        return self._extract_text(response)

    def chat_thinking(self, text: str, system: Optional[str] = None) -> str:
        """Chat using LFM Thinking model.
        
        Args:
            text (str): The input text.
            system (Optional[str], optional): The system prompt. Defaults to None.

        Returns:
            str: The response text.
        """

        input_data = (
            [{"role": "system", "content": system}, {"role": "user", "content": text}]
            if system
            else text
        )

        payload = {
            "input": input_data,
            "model": "LFM2.5-1.2B-Thinking",
        }

        response = self._post(payload)

        if "error" in response:
            return f"Error: {response['error']}"

        return self._extract_text(response)

    def summarize(
        self,
        text: str
    ) -> str:
        r"""Summarize the input text.

            Args:
                text (str): The text to summarize.

            Returns:
                str: The summarized text.
        """

        payload = {
            "input": text,
            "model": "llama-3.1-8b-instruct-fast",
        }

        response = self._post(payload)

        if "error" in response:
            return f"Error: {response['error']}"

        return self._extract_text(response)
    
    def classify_iab(self, text: str) -> Dict[str, Any]:
        """Classify text into IAB categories.

        Args:
            text (str): The text to classify.

        Returns:
            Dict[str, Any]: The classification results.
        """

        payload = {
            "input": text,
            "model": "zlm-v1-iab-classify-edge",
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse model output", "raw": content}
    
    def classify_iab_enriched(self, text: str) -> Dict[str, Any]:
        """Classify text into IAB categories.

        Args:
            text (str): The text to classify.

        Returns:
            Dict[str, Any]: The classification results.
        """

        payload = {
            "input": text,
            "model": "zlm-v1-iab-classify-edge-enriched",
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse model output", "raw": content}
    
    def classify_zero_shot(
        self,
        text: str,
        labels: List[str]
    ) -> Dict[str, Any]:
        r"""Classify the input text into IAB categories with predefined labels.

        Args:
            text (str): The text to classify.
            labels (List[str]): The list of labels to use for classification.

        Returns:
            Dict[str, Any]: The classification results.
        """

        payload = {
            "input": text,
            "model": "deberta-v3-small",
            "categories": labels,
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse model output", "raw": content}
        
    def classify_structured(
        self,
        text: str,
        schema_definition: Dict[str, List[str]],
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Structured classification using schema.
        
        Args:
            text (str): The text to classify.
            schema_definition (Dict[str, List[str]]): The schema for structured classification.
            threshold (Optional[float], optional): The threshold for classification. Defaults to None.

        Returns:
            Dict[str, Any]: The classification results.
        """

        metadata = {
            "task": "structured-classification",
            "schema": schema_definition,
        }

        if threshold is not None:
            metadata["threshold"] = threshold

        payload = {
            "input": text,
            "model": "gliner2-base-v1",
            "metadata": metadata,
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse", "raw": content}
        
    def extract_entities(
        self,
        text: str,
        labels: List[str],
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Extract entities based on labels.
        
        Args:
            text (str): The text to extract entities from.
            labels (List[str]): The list of labels to use for entity extraction.
            threshold (Optional[float], optional): The threshold for entity extraction. Defaults to None.

        Returns:
            Dict[str, Any]: The entity extraction results.
        """

        metadata = {
            "task": "entity-extraction",
            "labels": labels,
        }

        if threshold is not None:
            metadata["threshold"] = threshold

        payload = {
            "input": text,
            "model": "gliner2-base-v1",
            "metadata": metadata,
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse", "raw": content}
        
    def extract_json(
        self,
        text: str,
        schema: Dict[str, List[str]],
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Extract structured JSON based on schema.
        
        Args:
            text (str): The text to extract JSON from.
            schema (Dict[str, List[str]]): The schema for JSON extraction.
            threshold (Optional[float], optional): The threshold for JSON extraction. Defaults to None.

        Returns:
            Dict[str, Any]: The JSON extraction results.
        """

        metadata = {
            "task": "json-extraction",
            "schema": schema,
        }

        if threshold is not None:
            metadata["threshold"] = threshold

        payload = {
            "input": text,
            "model": "gliner2-base-v1",
            "metadata": metadata,
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse", "raw": content}
              
    def extract_pii(
        self,
        text: str,
        threshold: float = 0.5,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract PII entities from text.
        
        Args:
            text (str): The text to extract PII from.
            threshold (float, optional): The threshold for PII extraction. Defaults to 0.5.
            categories (Optional[List[str]], optional): The list of PII categories to extract. Defaults to None.

        Returns:
            Dict[str, Any]: The PII extraction results.
        """

        metadata = {
            "usecase": "extract-pii",
            "threshold": threshold,
        }

        if categories:
            metadata["categories"] = categories

        payload = {
            "input": text,
            "model": "gliner-multi-pii-v1",
            "metadata": metadata,
        }

        response = self._post(payload)

        if "error" in response:
            return {"error": response["error"]}

        content = self._extract_text(response)

        try:
            return json.loads(content)
        except Exception:
            return {"error": "Failed to parse model output", "raw": content}
        
    def redact_pii(
        self,
        text: str,
        mask: str = "label"
    ) -> str:
        """Redact PII from text.
        
        Args:
            text (str): The text to redact PII from.
            mask (str, optional): The mask to use for PII redaction. Defaults to "label".

        Returns:
            str: The redacted text.
        """

        payload = {
            "input": text,
            "model": "gliner-multi-pii-v1",
            "metadata": {
                "usecase": "redact",
                "mask": mask,
            },
        }

        response = self._post(payload)

        if "error" in response:
            return f"Error: {response['error']}"

        content = self._extract_text(response)

        try:
            parsed = json.loads(content)
            return parsed.get("redacted_text", "")
        except Exception:
            return content

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r"""Send a POST request to the ZeroGPU API.
        
        Args:
            payload (Dict[str, Any]): The request payload.
        
        Returns:
            Dict[str, Any]: The response from the API.
        """

        logger.debug(f"ZeroGPU request payload: {payload}")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Project-Id": self.project_id,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/responses",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code in (401, 403):
                return {"error": "Authentication failed"}
            elif response.status_code == 429:
                return {"error": "Rate limit exceeded"}
            elif response.status_code >= 500:
                return {"error": "Server error"}
            elif response.status_code != 200:
                return {"error": f"Request failed: {response.text}"}

            return response.json()

        except Exception as e:
            return {"error": str(e)}
        
    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.chat),
            FunctionTool(self.chat_thinking),
            FunctionTool(self.summarize),
            FunctionTool(self.classify_iab),
            FunctionTool(self.classify_iab_enriched),
            FunctionTool(self.classify_zero_shot),
            FunctionTool(self.classify_structured),
            FunctionTool(self.extract_entities),
            FunctionTool(self.extract_json),
            FunctionTool(self.extract_pii),
            FunctionTool(self.redact_pii),
        ]

    def _extract_text(self, response: Dict[str, Any]) -> str:
        r"""Extract the text from the API response.
        
        Args:
            response (Dict[str, Any]): The API response.
        
        Returns:
            str: The extracted text.
        """
        try:
            return response["output"][0]["content"][0]["text"]
        except Exception:
            return ""