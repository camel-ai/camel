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
import logging

from tqdm import tqdm

from ..agent_systems.base_agent_system import SyntheticDatum
from ..self_instruct.self_instruct_spec import SelfInstructSpec
from .generate_utils import load_jsonl

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self, spec: SelfInstructSpec):
        self.agent_system = spec.eval_agent_system
        self.synthetic_data_file = spec.curated_data_out_file

    def evaluate(self):
        synthetic_data = load_jsonl(self.synthetic_data_file)
        scores = []
        for synthetic_datum_json in tqdm(synthetic_data):
            synthetic_datum = SyntheticDatum(
                instruction=synthetic_datum_json["instruction"],
                input=synthetic_datum_json["input"],
                output=synthetic_datum_json["output"],
            )
            response = self.agent_system.run_eval(synthetic_datum)
            scores.append(response | synthetic_datum_json)

        return scores
