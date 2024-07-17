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
import json
import logging
import os
import time
import uuid
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from datasets import Dataset, DatasetDict, load_dataset
from synthetic_datagen.base_generator import BaseDataGenerator
from synthetic_datagen.evolve_instruct.evolve_instruct_spec import (
    EvolveInstructSpec,
)
from synthetic_datagen.utils.instance_generator import (
    InstanceGenerator,
)
from synthetic_datagen.utils.instruction_generator import (
    InstructionGenerator,
)

logger = logging.getLogger(__name__)


class Mutation(Enum):
    FRESH_START = 0
    ADD_CONSTRAINTS = 1
    DEEPEN = 2
    CONCRETIZE = 3
    INCREASE_REASONING = 4
    COMPLICATE = 5
    SWITCH_TOPIC = 6


class EvolveInstructGenerator(BaseDataGenerator):
    """
    A generator for evolve-instructed synthetic data.

    This class orchestrates the process of generating synthetic
    instructions and instances,
    as well as curating the generated data. It uses separate components
    for instruction
    generation, instance generation, and curation.

    Attributes:
        spec (EvolveInstructSpec): Specification object containing
        configuration details.
        instruction_generator (InstructionGenerator): Component for
        generating instructions.
        instance_generator (InstanceGenerator): Component for
        generating instances.

    """

    def __init__(self, spec: Optional[EvolveInstructSpec] = None):
        """
        Initialize the SelfInstructGenerator with the given specification.

        Args:
            spec (Optional[SelfInstructSpec]): Specification object
            for the generator. If not provided,
            a default SelfInstructSpec is used.
        """

        self.spec = spec or EvolveInstructSpec()
        self.instruction_generator = InstructionGenerator(self.spec)
        self.instance_generator = InstanceGenerator(self.spec)
        self.seed_text_list = []
        self.prompts = []
        self.final_prompts = []
        self.final_answers = []
        self.prompt_templates = dict()
        self.prompt_templates['base'] = ""
        write_in_korean = "Write in Korean."
        self.prompt_translate_into_korean = """
Translate #Given Prompt# to #New Prompt# in Korean."

#Given Prompt#:
<PROMPT>
"""

        self.prompt_templates[Mutation.FRESH_START] = (
            self.prompt_templates['base']
            + f"""Rewrite #Given Prompt# by switching the locale into \
            Korea and create #New Prompt#. {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.COMPLICATE] = (
            self.prompt_templates['base']
            + f"""Rewrite #Given Prompt# to make it slightly \
            more complicated, and create #New Prompt#. \
            {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.ADD_CONSTRAINTS] = (
            self.prompt_templates['base']
            + f"""Add a few more constraints or requirements \
                to #Given Prompt#, and create #New Prompt#. \
                {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.DEEPEN] = (
            self.prompt_templates['base']
            + f"""Slightly increase the depth and breadth \
                of #Given Prompt#, and create #New Prompt#. \
                {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.CONCRETIZE] = (
            self.prompt_templates['base']
            + f"""Make #Given Prompt# slightly more concrete, \
            and create #New Prompt#. {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.INCREASE_REASONING] = (
            self.prompt_templates['base']
            + f"""If #Given Prompt# can be solved with just a \
            few simple thinking processes, rewrite it to explicitly \
                request multi-step reasoning, and create #New Prompt#. \
                {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.SWITCH_TOPIC] = (
            self.prompt_templates['base']
            + f"""Rewrite #Given Prompt# by switching the topic, \
            keeping the domain and difficulty level similar, \
                and create #New Prompt#. {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

    def generate(self):
        """
        Generate synthetic instructions and instances.

        This method triggers the generation of synthetic instructions
        followed by
        the generation of synthetic instances based on those instructions.
        """
        self.create_seed_prompts()
        logging.info("Generating synthetic instructions...")
        self.create_prompts()
        logging.info("Generating synthetic instances...")
        self.create_answers()

    def evaluate(self):
        raise RuntimeError(
            "Evaluation not implemented for EvolveInstructGenerator yet "
            " - use an LLM to evaluate the quality of the generations."
        )

    def run(self):
        self.create_seed_prompts()
        self.create_prompts()
        self.create_answers()

        list_qa = []
        for i in range(len(self.final_prompts)):
            if len(self.final_answers[i]) > 10:
                list_qa.append(
                    {
                        'input': self.final_prompts[i],
                        'output': self.final_answers[i],
                    }
                )

        with open(
            f"{self.seed_data.replace('.jsonl', '')\
               .replace('json', '')}.%s.json"
            % str(uuid.uuid4())[:4],
            "wt",
        ) as f:
            f.write(json.dumps(list_qa, indent=2, ensure_ascii=False))

    def create_seed_prompts(self):
        """
        Turn self.seed_data into a list of strings of text
        self.source_text_list
        Each text string can represent as little as a word,
        or as much as document.
        Just has to be representative of some concept or body of text.

        :return: None
        """

        if isinstance(self.spec.seed_data, str) and os.path.exists(
            self.spec.seed_data
        ):
            data = load_dataset("json", data_files=self.spec.seed_data)
            self.seed_text_list = []
            for d in data['train']:
                s = ""
                if isinstance(self.spec.column_names, str):
                    s = d[self.spec.column_names]
                else:
                    for col in self.spec.column_names:
                        s += d[col] + "\n"
                self.seed_text_list.append(s.strip())
            assert self.seed_text_list, "data import failed, got empty list"

    def create_prompts(self):
        print("Creating %d prompts." % self.spec.num_rows)
        assert self.seed_text_list, "must have seed text list"
        t0 = time.time()
        self.prompts.clear()

        for _ in range(self.spec.num_rows):
            new_prompt = np.random.choice(self.seed_text_list)
            self.prompts.append(new_prompt)
        i = 0
        while self.mutate(i):
            print("Iteration: %d" % i)
            i += 1
        t1 = time.time()
        print(
            "Done creating %d prompts in %.4f seconds."
            % (len(self.final_prompts), t1 - t0)
        )
        print(self.final_prompts)

    def create_answers(self):
        print("Creating answers for %d prompts." % len(self.final_prompts))
        t0 = time.time()
        ds = self.convert_list_to_dataset(self.final_prompts)
        self.final_answers = self.llm_pipeline(ds['train'])
        t1 = time.time()
        print(
            "Done creating answers for %d prompts in %.4f seconds."
            % (ds['train'].num_rows, t1 - t0)
        )

    def convert_list_to_dataset(self, text_list):
        df = pd.DataFrame({'text': text_list})
        ds = DatasetDict()
        ds['train'] = Dataset.from_pandas(df)
        return ds

    def mutate(self, iteration):
        assert len(self.prompts) == self.spec.num_rows
        list_prompts = []
        mutations = []
        for i in range(self.spec.num_rows):
            mutation = np.random.choice(Mutation)
            mutations.append(mutation)
            # if mutation == Mutation.FRESH_START:
            #     mutation = Mutation.COMPLICATE
            before = self.prompts[i]
            prompt = self.prompt_templates[mutation].replace(
                "<PROMPT>", before
            )
            list_prompts.append(prompt)

        ds = self.convert_list_to_dataset(list_prompts)
        assert (
            ds['train'].num_rows
            == len(list_prompts)
            == self.spec.num_rows
            == len(self.prompts)
        )
        t0 = time.time()
        after = self.spec.llm_pipeline(ds['train'])
        assert len(after) == self.spec.num_rows
        t1 = time.time()
        print("HFPipeline took %.4f seconds" % (t1 - t0))

        for i in range(len(after)):
            after[i] = after[i].split("Prompt#:")[-1].strip()
            for pp in ['New Prompt:\n', 'New Prompt: ']:
                if after[i][: len(pp)] == pp:
                    after[i] = after[i][len(pp) :]
            after[i] = after[i].strip()
            use_new_prompt, why = self.change_approved(
                self.prompts[i], after[i]
            )
            if self.spec.verbose:
                print("===========================")
                print("Old Prompt: %s" % self.prompts[i])
                print("Mutation: %s" % mutations[i].name)
                print("New Prompt: %s" % after[i])
                print("===========================")

            if use_new_prompt:
                if (
                    self.spec.max_len_chars
                    >= len(after[i])
                    >= self.spec.min_len_chars
                ):
                    self.final_prompts.append(after[i])
                    print(
                        "Prompt was accepted, now have %d good prompts."
                        % len(self.final_prompts)
                    )
                    self.prompts[i] = np.random.choice(self.seed_text_list)
                    print("Creating new prompt.")
                else:
                    self.prompts[i] = after[i]
                    print("Prompt was successfully modified.")
            else:
                print("Mutation rejected, will try again. Reason: %s" % why)
            print("", flush=True)
        return len(self.final_prompts) < self.spec.num_rows

    def change_approved(self, before, after):
        if before == after:
            return False, "same"
        if after.count('\n') > after.count(" ") * 2:
            return False, "too many lines"
        if after.count('\n') == after.count("- ") > 10:
            return False, "too many items"
        if (
            self.prompt_templates['base']
            and self.prompt_templates['base'] in after
        ):
            return False, "prompt leaked 1"
        if "#New Prompt#" in after:
            return False, "prompt leaked 2"
        if "new prompt" in after.lower():
            return False, "prompt leaked 3"
        if "openai" in after.lower():
            return False, "AI"
        if "gpt" in after.lower() and "gpt" not in before.lower():
            return False, "AI"
        if (
            "죄송하지만" in after.lower()
            and "죄송" not in before.lower()
            and len(after) < len(before)
        ):
            return False, "sorry"
        if False:
            # too slow in general, not needed
            prompt = """Are the two following prompts equal to each other?
To be equal, they must meet two requirements:
1. Both prompts have the same constraints and requirements.
2. Both prompts have the same depth and breath of the inquiry.
First prompt: %s
Second prompt: %s
Answer with 'Equal' or 'Not Equal'. No need to explain the reason.""" % (
                before,
                after,
            )
            answer = self.llm_pipeline(prompt)
            if 'not equal' not in answer.lower():
                return False, "equal"
        return True, "ok"
