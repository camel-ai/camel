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
import re
from typing import Any, Dict, Optional, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import ModelType, RoleType


class InsightAgent(ChatAgent):
    r"""An agent that aims to generate insights from a provided text.
    Args:
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="Role Assigner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
        )
        super().__init__(system_message, model, model_config)

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def run(
        self,
        context_text: Union[str, TextPrompt],
        reference_text: Optional[Union[str, TextPrompt]] = None,
        insights_instruction: Optional[Union[str, TextPrompt]] = None,
    ) -> Dict[str, Dict[str, Optional[str]]]:
        r"""Generate role names based on the input task prompt.

        Args:
            context_text (Union[str, TextPrompt]): The context text to
                generate insights from.
            reference_text (Optional[Union[str, TextPrompt]], optional):
                The reference text for generating insights. (default:
                :obj:`None`)
            insights_instruction (Optional[Union[str, TextPrompt]], optional):
                The instruction for generating insights. (default: :obj:`None`)

        Returns:
            Dict[str, Dict[str, Optional[str]]]: The generated insights from
                the input context text.
        """
        self.reset()

        insights_instruction_prompt = \
            TextPrompt("{insights_instruction} Based on the CONTEXT TEXT " +
                       "provided, generate a comprehensive set of distinct " +
                       "insights following the \"RULES OF INSIGHTS " +
                       "GENERATION\" and use the \"ANSWER TEMPLATE\" to " +
                       "structure your response. Extract as many meaningful " +
                       "insights as the context allows. Your answer MUST "
                       "strictly adhere to the structure of ANSWER " +
                       "TEMPLATE, ONLY fill in  the BLANKs, and DO NOT " +
                       "alter or modify any other part of the template.\n")
        context_text_prompt = TextPrompt(
            "===== CONTEXT TEXT =====\n{context_text}\n\n")
        insights_prompt = (
            "===== RULES OF INSIGHTS GENERATION =====\n" +
            "According to the following rules, summary the unknowns in your " +
            "answer from the CONTEXT " + "TEXT:\n" +
            "1. Text/Code Decomposition (Breaking it Down):\n" +
            "- Topic/Functionality Segmentation: Divide the text into main " +
            "topics or themes. What is more, multiple topics or themes are " +
            "possible.\n" +
            "- Entity/Code Environment Recognition: Identify names, places, " +
            "dates, or specific technical terms that might be associated " +
            "with events or innovations post-2022.\n" +
            "- Extract Details: Within these main topics or themes, identify "
            + "key facts, statements, or claims that are made.\n" +
            "2. Question Generation (Identifying Potential " + "Unknowns):\n" +
            "For each identified entity or detail from the decomposition:\n" +
            "- Cross-Referencing: Check against your knowledge base up to " +
            "2022. If it's a known entity or detail, move on. If not:\n" +
            "    a. Contextual Understanding: Even if the entity is " +
            "unknown, understanding the context can be vital. For instance, " +
            "even if I don't know a specific person named in 2023, if the " +
            "text mentions they are an astronaut, I can craft my questions " +
            "based on that role.\n" +
            "    b. Formulate/Code Questions: Generate specific questions " +
            "targeting the UNKNOWN. Questions can vary in nature:\n" +
            "        i. Factual: \"Who/What is [unknown entity/code]?\"\n" +
            "        ii. Conceptual: \"How does the [unknown " +
            "technology/code] work?\"\n" +
            "        iii. Historical: \"When was [unknown event/code] first " +
            "introduced?\"\n" +
            "        iv. Implication-based: \"What is the significance of " +
            "[unknown event/code] in related domain knowledge?\"\n" +
            "    c. Iterative Feedback: Depending on the user's responses " +
            "to these questions, you can generate follow-up questions for " +
            "deeper understanding.\n\n")
        insight_template = ("Insight <NUM>:\n" +
                            "- Topic Segmentation:\n<BLLANK or N/A>\n" +
                            "- Entity Recognition:\n<BLANK or N/A>\n" +
                            "- Extract Details:\n<BLANK or N/A>\n" +
                            "- Contextual Understanding:\n<BLANK or N/A>\n" +
                            "- Iterative Feedback:\n<BLANK or N/A>\n" +
                            "- Formulate Questions:\n<BLANK or N/A>\n" +
                            "- Answer to \"Formulate Questions\" using " +
                            "CONTEXT TEXT:\n<BLANK or N/A>\n")
        answer_template_prompt = TextPrompt(
            "===== ANSWER TEMPLATE =====\n" +
            "You need to generate multiple insights, and " +
            "there are several insights in total:\n" +
            "\n".join(insight_template for _ in range(2)))
        insights_generation_prompt = insights_instruction_prompt + \
            context_text_prompt + insights_prompt + answer_template_prompt
        insights_generation = insights_generation_prompt.format(
            insights_instruction=insights_instruction or "",
            context_text=context_text)

        insights_generation_msg = BaseMessage.make_user_message(
            role_name="NovaDive&QuestXplorer", content=insights_generation)

        response = self.step(input_message=insights_generation_msg)

        if response.terminated:
            raise RuntimeError("Insights generation failed.")
        msg = response.msg  # type: BaseMessage

        # Replace the "N/A", "None", "NONE" with None
        def handle_none_values_in_msg(value):
            if value in ["N/A", "None", "NONE"]:
                return None
            return value.strip() if value else None

        # Parse the insights from the response
        insights_pattern = (
            r"Insight (\d+):(?:\s+- Topic Segmentation:\s*((?:.|\n)+?)"
            r"(?=\s+- Entity Recognition|\Z))?" +
            r"(?:\s+- Entity Recognition:\s*((?:.|\n)+?)"
            r"(?=\s+- Extract Details|\Z))?" +
            r"(?:\s+- Extract Details:\s*((?:.|\n)+?)"
            r"(?=\s+- Contextual Understanding|\Z))?" +
            r"(?:\s+- Contextual Understanding:\s*((?:.|\n)+?)"
            r"(?=\s+- Iterative Feedback|\Z))?" +
            r"(?:\s+- Iterative Feedback:\s*((?:.|\n)+?)"
            r"(?=\s+- Formulate Questions|\Z))?" +
            r"(?:\s+- Formulate Questions:\s*((?:.|\n)+?)"
            r"(?=\s+- Answer to \"Formulate Questions\" using CONTEXT "
            r"TEXT|\Z))?(?:\s+- Answer to \"Formulate Questions\" using "
            r"CONTEXT TEXT:\s*((?:.|\n)+?)(?=\n*Insight \d+|\Z))?")

        insights_matches = re.findall(insights_pattern, msg.content, re.DOTALL)

        insights_json = {}
        for match in insights_matches:
            (insight_num, topic, entity, extract, context, feedback, question,
             answer) = match
            insights_json[f"insight {insight_num}"] = {
                "topic segmentation": handle_none_values_in_msg(topic),
                "entity recognition": handle_none_values_in_msg(entity),
                "extract details": handle_none_values_in_msg(extract),
                "contextual understanding": handle_none_values_in_msg(context),
                "iterative feedback": handle_none_values_in_msg(feedback),
                "formulate questions": handle_none_values_in_msg(question),
                "answer to formulate questions":
                handle_none_values_in_msg(answer)
            }

        return insights_json
