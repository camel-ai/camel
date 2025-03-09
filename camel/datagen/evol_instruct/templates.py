# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

from dataclasses import dataclass


# flake8: noqa
@dataclass(frozen=True)
class EvolInstructTemplates:
    """
    Contains templates for EvolInstruct prompt transformations.
    
    References:
      - WizardLM: Empowering Large Language Models to Follow Complex Instructions
        https://arxiv.org/pdf/2304.12244
      - eva: Evolving Alignment via Asymmetric Self-Play
        https://arxiv.org/abs/2411.00062
    """
    
    # High-level instructions on in-depth/in-breadth evolving
    INST_IN_DEPTH = (
        "Please act as an expert Prompt Rewriter.\n"
        "Your objective is to rewrite a given prompt into a more complex version "
        "to make those large language models (e.g., gemini) a bit harder to handle.\n"
        "But the rewritten prompt must be reasonable and must be understood and responded by humans.\n"
        "Your rewriting cannot omit the non-text parts such as the table and code in #Given Prompt#, if there is any."
        "You should try your best not to make the #Rewritten Prompt# become verbose, "
        "The #Rewritten Prompt# should be roughly the similar length or a little bit more than that of #Given Prompt#.\n"
        "The #Rewritten Prompt# must sound like a real human user's prompt; DON'T make it like sound machine-generated."
        "Specifically, you SHOULD complicate the given prompt using the following method: "
        "\n{method}\n" 
        "The rewritten prompt should reflect meaningful changes across its structure, "
        "ensuring the entire sentence feels sufficiently different from the original. "
        "Again, make sure the rewritten prompt presents a more CHALLENGING TASK."
        "Respond with your rewritten prompt directly. "
        "#Given Prompt#:\n{prompt}\n"
        "#Rewritten Prompt#:\n"
    ).lstrip()

    INST_IN_BREADTH = (
        "Please act as an expert Prompt Creator.\n"
        "Your objective is to generate a brand-new prompt based on the #Given Prompt#. "
        "The purpose of this task is to promote diversity and generality of training prompts for language models, "
        "helping it practice with varied challenges and perspectives.\n"
        "The LENGTH and complexity of the #Created Prompt# should be similar to that of the #Given Prompt#.\n"
        "The #Created Prompt# must be reasonable, interpretable, and solvable by humans.\n"
        "The #Created Prompt# must sound like a real human user's prompt; DON'T make it sound like machine-generated."
        "Follow the method described below to guide your creation:\n"
        "{method}\n"
        "The created prompt should reflect meaningful changes across its structure, "
        "ensuring the entire sentence feels sufficiently different from the original. "
        "Respond with your created prompt directly.\n"
        "#Given Prompt#:\n{prompt}\n"
        "#Created Prompt#:\n"
    ).lstrip()

    # Sub-method instructions (following the eva paper setting, which sligtly differs from WizardLM)
    IN_BREADTH_KEYS = ['persona', 'shift-in', 'shift-out', 'mix', 'abstract'] 
    IN_DEPTH_KEYS = ['constraints', 'deepening', 'concretizing', 'reasoning', 'expansion']

    EVOL_METHODS = {
        "persona": (
            "Reframe the #Given Prompt# as if written by a user with a completely different persona, background, or expertise. "
            "Adjust the tone, style, phrasing, or anything you feel proper to reflect this change. "
            "The changes should make the prompt feel like it was authored by someone entirely new."
        ),

        "shift-in": (
            "Shift the high-level idea of the #Given Prompt# to explore a different subdomain or context within the same domain. "
            "Ensure the new topic still challenges the model to reason or provide knowledge relevant to the domain."
        ),

        "shift-out": (
            "Shift the high-level idea of the #Given Prompt# to a completely different topic in a different setting. "
            "The new topic may challenge the model with similar reasoning or contextual understanding but in a novel way."
        ),

        "mix": (
            "Combine the high-level concept of the #Given Prompt# with elements from a different domain. "
            "Introduce novel scenarios or contexts to create diversity while maintaining relevance to the original idea."
        ),

        "abstract": (
            "Turn the #Given Prompt# into a more abstract or generalized version, removing specific details while preserving its intent. "
            "Ensure the new prompt encourages broader, principle-driven reasoning."
        ),

        "constraints": (
            "Add one or more significant constraints or requirements into the '#Given Prompt#'. "
            "The added constraints must meaningfully alter how the model would respond. "
            "For example, specify additional rules, contexts, or limitations that demand creative adjustments to the response."
        ),

        "deepening": (
            "If the #Given Prompt# contains inquiries about certain issues, increase the depth and breadth of the inquiry. "
            "Make the question require a more detailed, multi-layered, or comprehensive response. "
            "For instance, break the problem into sub-problems or require connections between unrelated concepts."
        ),

        "concretizing": (
            "Replace general concepts in the #Given Prompt# with more specific and detailed concepts. "
            "Ensure that the change makes the problem more defined and concrete, leaving less room for ambiguity. "
            "For example, replace 'a device' with 'a wearable fitness tracker with GPS'."
        ),

        "reasoning": (
            "Add one or more reasoning steps into the '#Given Prompt#'. "
            "Explicitly rewrite it to demand multi-step reasoning or justify intermediate steps in the solution. "
            "For instance, if the original prompt is a simple query, make the response require a step-by-step breakdown of logic or calculations."
        ),

        "expansion": (
            "Expand the #Given Prompt# by including additional perspectives, domains, or layers of complexity. "
            "For example, if the original prompt focuses on a single scenario, add related scenarios or ask the model to compare different situations."
        )
    }
