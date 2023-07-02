# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
"""Class for a VectorStore-backed memory object."""

from typing import Any, Dict, List, Optional, Union

from camel.memory.base import BaseMemory
from camel.typing import Document
from camel.vectorstores.base import VectorStoreRetriever


@dataclass
class VectorStoreRetrieverMemory(BaseMemory):
    r"""Class for a VectorStore-backed memory object.

    Args:
        retriever (VectorStoreRetriever): VectorStoreRetriever object to connect to.
        memory_key (str): Key name to locate the memories in the result of
            load_memory_variables. (default: "history")
        input_key (Optional[str]): Key name to index the inputs to
            load_memory_variables. (default: None)
        return_docs (bool): Whether or not to return the result of querying
            the database directly. (default: False)
    """

    retriever: VectorStoreRetriever
    memory_key: str = "history"
    input_key: Optional[str] = None
    return_docs: bool = False

    @property
    def memory_variables(self) -> List[str]:
        r"""The list of keys emitted from the load_memory_variables method.

        Returns:
            list: The list of keys.
        """
        return [self.memory_key]

    def _get_prompt_input_key(self, inputs: Dict[str, Any]) -> str:
        r"""Get the input key for the prompt.

        Args:
            inputs (Dict[str, Any]): The inputs.

        Returns:
            str: The input key.
        """
        if self.input_key is None:
            return get_prompt_input_key(inputs, self.memory_variables)
        return self.input_key

    def load_memory_variables(
        self, inputs: Dict[str, Any]
    ) -> Dict[str, Union[List[Document], str]]:
        r"""Return history buffer.

        Args:
            inputs (Dict[str, Any]): The inputs.

        Returns:
            dict: The result of the function.
        """
        input_key = self._get_prompt_input_key(inputs)
        query = inputs[input_key]
        docs = self.retriever.get_relevant_documents(query)
        result: Union[List[Document], str]
        if not self.return_docs:
            result = "\n".join([doc.page_content for doc in docs])
        else:
            result = docs
        return {self.memory_key: result}

    def _form_documents(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> List[Document]:
        r"""Format context from this conversation to buffer.

        Args:
            inputs (Dict[str, Any]): The inputs.
            outputs (Dict[str, str]): The outputs.

        Returns:
            list: The list of documents.
        """
        # Each document should only include the current turn, not the chat history
        filtered_inputs = {k: v for k, v in inputs.items() if k != self.memory_key}
        texts = [
            f"{k}: {v}"
            for k, v in list(filtered_inputs.items()) + list(outputs.items())
        ]
        page_content = "\n".join(texts)
        return [Document(page_content=page_content)]

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        r"""Save context from this conversation to buffer.

        Args:
            inputs (Dict[str, Any]): The inputs.
            outputs (Dict[str, str]): The outputs.
        """
        documents = self._form_documents(inputs, outputs)
        self.retriever.add_documents(documents)

    def clear(self) -> None:
        r"""Nothing to clear."""
        pass
