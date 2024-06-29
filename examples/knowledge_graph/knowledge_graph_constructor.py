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

from camel.agents import KnowledgeGraphAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import OpenAIModel
from camel.types import ModelType

parser = argparse.ArgumentParser(
    description="Arguments for knowledge graph constructor.",
)
parser.add_argument(
    "--text",
    type=str,
    help="Text data or path to a file for knowledge graph constructor.",
    required=False,
    default=None,
)
parser.add_argument(
    "--path_or_url",
    type=str,
    help="Path to a file or a URL for knowledge graph constructor.",
    required=False,
    default=None,
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for knowledge graph constructor.",
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
    "--parse_graph_elements",
    help="Whether to parse the graph elements.",
    action="store_true",
)
parser.add_argument(
    "--output_path",
    type=str,
    help=(
        "Output path for LLM knowledge graph constructor. "
        "If not specified, results will be printed out."
    ),
    required=False,
    default=None,
)

args = parser.parse_args()


def construct(
    text: str | None,
    path_or_url: str | None,
    model_type: ModelType,
    temperature: float,
    parse_graph_elements: bool,
    output_path: str | None,
) -> None:
    model_config = ChatGPTConfig(temperature=temperature)
    model = OpenAIModel(
        model_type=model_type, model_config_dict=model_config.__dict__
    )
    kg_agent = KnowledgeGraphAgent(model=model)

    if text is not None:
        element = text
    elif path_or_url is not None:
        from camel.loaders import UnstructuredIO

        uio = UnstructuredIO()
        element = uio.parse_file_or_url(path_or_url)[0]
    else:
        raise ValueError("Either text or path_or_url should be specified")

    # Let KnowledgeGraph Agent extract node and relationship information
    out = kg_agent.run(element, parse_graph_elements=parse_graph_elements)

    if not output_path:
        print(out)
    else:
        with open(output_path, "w") as f:
            f.write(str(out))


def main() -> None:
    construct(
        args.text,
        args.path_or_url,
        ModelType(args.model_type),
        args.temperature,
        args.parse_graph_elements,
        args.output_path,
    )


if __name__ == "__main__":
    main()

"""
===============================================================================
Nodes:

Node(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'})
Node(id='community', type='Concept', properties={'agent_generated'})
Node(id='study', type='Concept', properties={'agent_generated'})
Node(id='autonomous agents', type='Concept', properties={'agent_generated'})
Node(id='communicative agents', type='Concept', properties={'agent_generated'})

Relationships:

Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='community', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='study', type='Concept'), type='FocusOn', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='autonomous agents', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='communicative agents', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
===============================================================================
"""

"""
===============================================================================
GraphElement(nodes=[Node(id='CAMEL-AI.org', type='Organization', properties=
{'agent_generated'}), Node(id='community', type='Concept', properties=
{'agent_generated'}), Node(id='study', type='Concept', properties=
{'agent_generated'}), Node(id='autonomous agents', type='Concept', properties=
{'agent_generated'}), Node(id='communicative agents', type='Concept', 
properties={'agent_generated'})], relationships=[Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='community', type='Concept', properties={'agent_generated'}), 
type='FocusOn', properties={"'agent_generated'"}), Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='study', type='Concept', properties={'agent_generated'}), 
type='FocusOn', properties={"'agent_generated'"}), Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='autonomous agents', type='Concept', properties=
{'agent_generated'}), type='FocusOn', properties={"'agent_generated'"}), 
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization', properties=
{'agent_generated'}), obj=Node(id='communicative agents', type='Concept', 
properties={'agent_generated'}), type='FocusOn', properties=
{"'agent_generated'"})], source=<unstructured.documents.elements.Text object 
at 0x7fd050e7bd90>)
===============================================================================
"""
