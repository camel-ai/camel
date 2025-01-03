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

from typing import Any, Callable, List, Literal, Type, Union

from pydantic import BaseModel

from .base import BaseConverter


class OutlinesConverter(BaseConverter):
    r"""OutlinesConverter is a class that converts a string or a function
    into a BaseModel schema.

    Args:
        model_type (str, optional): The model type to be used.
        platform (str, optional): The platform to be used.
            1. transformers
            2. mamba
            3. vllm
            4. llamacpp
            5. mlx
            (default: "transformers")
        **kwargs: The keyword arguments to be used. See the outlines
            documentation for more details. See
            https://dottxt-ai.github.io/outlines/latest/reference/models/models/
    """

    def __init__(
        self,
        model_type: str,
        platform: Literal[
            "vllm", "transformers", "mamba", "llamacpp", "mlx"
        ] = "transformers",
        **kwargs: Any,
    ):
        self.model_type = model_type
        from outlines import models

        match platform:
            case "vllm":
                self._outlines_model = models.vllm(model_type, **kwargs)
            case "transformers":
                self._outlines_model = models.transformers(
                    model_type, **kwargs
                )
            case "mamba":
                self._outlines_model = models.mamba(model_type, **kwargs)
            case "llamacpp":
                self._outlines_model = models.llamacpp(model_type, **kwargs)
            case "mlx":
                self._outlines_model = models.mlxlm(model_type, **kwargs)
            case _:
                raise ValueError(f"Unsupported platform: {platform}")

    def convert_regex(self, content: str, regex_pattern: str) -> str:
        r"""Convert the content to the specified regex pattern.

        Args:
            content (str): The content to be converted.
            regex_pattern (str): The regex pattern to be used.

        Returns:
            str: The converted content.
        """
        import outlines

        regex_generator = outlines.generate.regex(
            self._outlines_model, regex_pattern
        )
        return regex_generator(content)

    def convert_json(
        self,
        content: str,
        output_schema: Union[str, Callable],
    ) -> dict:
        r"""Convert the content to the specified JSON schema given by
        output_schema.

        Args:
            content (str): The content to be converted.
            output_schema (Union[str, Callable]): The expected format of the
                response.

        Returns:
            dict: The converted content in JSON format.
        """
        import outlines

        json_generator = outlines.generate.json(
            self._outlines_model, output_schema
        )
        return json_generator(content)

    def convert_pydantic(
        self,
        content: str,
        output_schema: Type[BaseModel],
    ) -> BaseModel:
        r"""Convert the content to the specified Pydantic schema.

        Args:
            content (str): The content to be converted.
            output_schema (Type[BaseModel]): The expected format of the
                response.

        Returns:
            BaseModel: The converted content in pydantic model format.
        """
        import outlines

        json_generator = outlines.generate.json(
            self._outlines_model, output_schema
        )
        return json_generator(content)

    def convert_type(self, content: str, type_name: type) -> str:
        r"""Convert the content to the specified type.

        The following types are currently available:
            1. int
            2. float
            3. bool
            4. datetime.date
            5. datetime.time
            6. datetime.datetime
            7. custom types (https://dottxt-ai.github.io/outlines/latest/reference/generation/types/)

        Args:
            content (str): The content to be converted.
            type_name (type): The type to be used.

        Returns:
            str: The converted content.
        """
        import outlines

        type_generator = outlines.generate.format(
            self._outlines_model, type_name
        )
        return type_generator(content)

    def convert_choice(self, content: str, choices: List[str]) -> str:
        r"""Convert the content to the specified choice.

        Args:
            content (str): The content to be converted.
            choices (List[str]): The choices to be used.

        Returns:
            str: The converted content.
        """
        import outlines

        choices_generator = outlines.generate.choice(
            self._outlines_model, choices
        )
        return choices_generator(content)

    def convert_grammar(self, content: str, grammar: str) -> str:
        r"""Convert the content to the specified grammar.

        Args:
            content (str): The content to be converted.
            grammar (str): The grammar to be used.

        Returns:
            str: The converted content.
        """
        import outlines

        grammar_generator = outlines.generate.cfg(
            self._outlines_model, grammar
        )
        return grammar_generator(content)

    def convert(  # type: ignore[override]
        self,
        content: str,
        type: Literal["regex", "json", "type", "choice", "grammar"],
        **kwargs,
    ) -> Any:
        r"""Formats the input content into the expected BaseModel.

        Args:
            type (Literal["regex", "json", "type", "choice", "grammar"]):
                The type of conversion to perform. Options are:
                    - "regex": Match the content against a regex pattern.
                    - "pydantic": Convert the content into a pydantic model.
                    - "json": Convert the content into a JSON based on a
                      schema.
                    - "type": Convert the content into a specified type.
                    - "choice": Match the content against a list of valid
                      choices.
                    - "grammar": Convert the content using a specified grammar.
            content (str): The content to be formatted.
            **kwargs: Additional keyword arguments specific to the conversion
                type.

            - For "regex":
                regex_pattern (str): The regex pattern to use for matching.

            - For "pydantic":
                output_schema (Type[BaseModel]): The schema to validate and
                    format the pydantic model.

            - For "json":
                output_schema (Union[str, Callable]): The schema to validate
                    and format the JSON object.

            - For "type":
                type_name (str): The target type name for the conversion.

            - For "choice":
                choices (List[str]): A list of valid choices to match against.

            - For "grammar":
                grammar (str): The grammar definition to use for content
                    conversion.
        """
        match type:
            case "regex":
                return self.convert_regex(content, kwargs.get("regex_pattern"))  # type: ignore[arg-type]
            case "pydantic":
                return self.convert_pydantic(
                    content, kwargs.get("output_schema")
                )  # type: ignore[arg-type]
            case "json":
                return self.convert_json(content, kwargs.get("output_schema"))  # type: ignore[arg-type]
            case "type":
                return self.convert_type(content, kwargs.get("type_name"))  # type: ignore[arg-type]
            case "choice":
                return self.convert_choice(content, kwargs.get("choices"))  # type: ignore[arg-type]
            case "grammar":
                return self.convert_grammar(content, kwargs.get("grammar"))  # type: ignore[arg-type]
            case _:
                raise ValueError("Unsupported output schema type")
