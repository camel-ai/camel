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
import argparse

from synthetic_datagen.agent_systems.single_agent import SingleAgent
from synthetic_datagen.evolve_instruct.evolve_instruct_generator import (
    EvolveInstructGenerator,
)
from synthetic_datagen.evolve_instruct.evolve_instruct_spec import (
    EvolveInstructSpec,
)
from synthetic_datagen.pipeline import ChatGPTPipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument("--seed_file", type=str, default="")
    parser.add_argument("--column_names", nargs='+', default="instruction")
    parser.add_argument("--num_rows", type=int, default=5)
    parser.add_argument("--min_len_chars", type=int, default=32)
    parser.add_argument("--max_len_chars", type=int, default=2048)
    parser.add_argument("--openai_model", type=str, default="gpt-3.5-turbo")

    args = parser.parse_args()
    spec = EvolveInstructSpec()
    spec.agent_system = SingleAgent()
    llm_pipeline = ChatGPTPipeline(args.openai_model)

    generator = EvolveInstructGenerator(
        llm_pipeline=llm_pipeline,
        seed_data=args.seed_file,
        column_names=args.column_names,
        num_rows=args.num_rows,
        min_len_chars=args.min_len_chars,
        max_len_chars=args.max_len_chars,
        verbose=True,
    )
    generator.run()
