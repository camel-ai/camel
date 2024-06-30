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
from __future__ import annotations

import argparse
import warnings

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.types.enums import RoleType, TaskType

warnings.filterwarnings("ignore")


parser = argparse.ArgumentParser(description="Arguments for translation.")
parser.add_argument(
    "--text",
    type=str,
    help="Text data or path to a file for translation.",
    required=False,
    default=None,
)
parser.add_argument(
    "--path_or_url",
    type=str,
    help="Path to a file or a URL for translation.",
    required=False,
    default=None,
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for translation.",
    required=False,
    default=ModelType.GPT_3_5_TURBO.value,
)
parser.add_argument(
    "--temperature",
    type=float,
    help="Model temperature.",
    required=False,
    default=1.0,
)
parser.add_argument(
    "--output_path",
    type=str,
    help=(
        "Output path for LLM translation. "
        "If not specified, results will be printed out."
    ),
    required=False,
    default=None,
)
parser.add_argument(
    '--language',
    type=str,
    help="Language to be translated to.",
    default="chinese",
)

args = parser.parse_args()


def translate(
    text: str | None,
    path_or_url: str | None,
    model_type: ModelType,
    temperature: float,
    language: str,
    output_path: str | None,
) -> None:
    if text is not None:
        input_text = text
    elif path_or_url is not None:
        from camel.loaders import UnstructuredIO

        uio = UnstructuredIO()
        elements = uio.parse_file_or_url(path_or_url)
        input_text = "\n".join([element.text for element in elements])
    else:
        raise ValueError("Either text or path_or_url should be specified")

    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.TRANSLATION)
    assistant_sys_msg = sys_msg_generator.from_dict(
        meta_dict=dict(language=language.capitalize()),
        role_tuple=('Language Translator', RoleType.ASSISTANT),
    )
    model_config = ChatGPTConfig(temperature=temperature)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_type,
        model_config_dict=model_config.__dict__,
    )
    assistant_agent = ChatAgent(
        system_message=assistant_sys_msg,
        model=model,
    )
    user_msg = BaseMessage.make_user_message(
        role_name="Language Translator",
        content=input_text,
    )
    assistant_response = assistant_agent.step(user_msg)
    assistant_msg = assistant_response.msg
    if not output_path:
        print(assistant_msg.content)
    else:
        with open(output_path, "w") as f:
            f.write(assistant_msg.content)


def main() -> None:
    translate(
        args.text,
        args.path_or_url,
        ModelType(args.model_type),
        args.temperature,
        args.language,
        args.output_path,
    )


if __name__ == "__main__":
    main()
