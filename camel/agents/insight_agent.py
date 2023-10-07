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
            role_name="Insight Agent",
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
            TextPrompt("{insights_instruction}\n Based on the CONTEXT TEXT " +
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
        insights_prompt = """===== RULES OF INSIGHTS GENERATION =====
According to the following rules, extract insights and details in your answer from the CONTEXT TEXT:
1. Text/Code Decomposition (Breaking it Down):
- Topic/Functionality Segmentation: Divide the text into main topics or themes. What is more, multiple topics or themes are possible.
- Entity/Code Environment Recognition: Identify names, places, dates, specific technical terms or contextual parameters that might be associated with events, innovations post-2022.
- Extract Details: Within these main topics or themes, identify key facts, statements, claims or contextual parameters. Please identify and write any detail(s) or term(s) from the CONTEXT TEXT that are either not present in your knowledge base, might be post-2022 developments, or can influence the nature of any task to be executed.
2. Question Generation (Identifying Potential Unknowns):
For each identified entity or detail from the decomposition:
- Cross-Referencing: Check against your knowledge base up to 2022. If it's a known entity or detail, move on. If not:
    a. Contextual Understanding: Even if the entity is unknown, understanding the context can be vital. For instance, even if I don't know a specific person named in 2023, if the text mentions they are an astronaut, I can craft my questions based on that role.
    b. Formulate/Code Questions: Generate specific questions targeting the unfamiliar or context-specific information. Questions can vary in nature:
        i. Factual: "Who/What is [unknown entity/infomation/code]?"
        ii. Conceptual: "How does the [unknown technology/code] work?"
        iii. Historical: "When was [unknown event/code] first introduced?"
        iv. Implication-based: "What is the significance of [unknown event/code] in related domain knowledge?"
    c. Iterative Feedback: Depending on the user's responses to these questions, you can generate follow-up questions for deeper understanding.
3. Generate as many insights as you find relevant from the CONTEXT TEXT, abhering to ANSWER TEMPLATE. In answer, use nouns and phrases to replace sentences.

"""  # noqa: E501

        insight_template = ("Insight <NUM>:\n" +
                            "- Topic Segmentation:\n<BLLANK or N/A>\n" +
                            "- Entity Recognition:\n<BLANK or N/A>\n" +
                            "- Extract Details:\n<BLANK or N/A>\n" +
                            "- Contextual Understanding:\n<BLANK or N/A>\n" +
                            "- Iterative Feedback:\n<BLANK or N/A>\n" +
                            "- Formulate Questions:\n<BLANK or N/A>\n" +
                            "- Answer to \"Formulate Questions\" using " +
                            "CONTEXT TEXT:\n<BLANK or N/A>\nEnd.\n")
        answer_template_prompt = TextPrompt(
            "===== ANSWER TEMPLATE =====\n" +
            "You need to generate multiple insights, and the number of " +
            "insights depend on the number of Topic/Functionality " +
            "Segmentation. So the total number of insights is <NUM>.\n" +
            "\n".join(insight_template for _ in range(2)))
        insights_generation_prompt = insights_instruction_prompt + \
            context_text_prompt + insights_prompt + answer_template_prompt
        insights_generation = insights_generation_prompt.format(
            insights_instruction=insights_instruction or "",
            context_text=context_text)

        insights_generation_msg = BaseMessage.make_user_message(
            role_name="Insight Agent", content=insights_generation)

        response = self.step(input_message=insights_generation_msg)

        if response.terminated:
            raise RuntimeError("Insights generation failed.")
        msg = response.msg  # type: BaseMessage

        # Replace the "N/A", "None", "NONE" with None
        def handle_none_values_in_msg(value):
            if value in ["N/A", "None", "NONE", "null", "NULL"]:
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
            r"CONTEXT TEXT:\s*((?:.|\n)+?)(?=\n*End.|\Z))?")

        insights_matches = re.findall(insights_pattern, msg.content, re.DOTALL)

        insights_json = {}
        for match in insights_matches:
            (insight_num, topic, entity, extract, context, feedback, question,
             answer) = match
            insights_json[f"insight {insight_num}"] = {
                "topic_segmentation": handle_none_values_in_msg(topic),
                "entity_recognition": handle_none_values_in_msg(entity),
                "extract_details": handle_none_values_in_msg(extract),
                "contextual_understanding": handle_none_values_in_msg(context),
                "iterative_feedback": handle_none_values_in_msg(feedback),
                "formulate_questions": handle_none_values_in_msg(question),
                "answer_to_formulate_questions":
                handle_none_values_in_msg(answer)
            }

        # Remove the insight if the topic segmentation/insight is None or empty
        remove_empty_insights_list = []
        for insight_idx, _ in insights_json.items():
            if insights_json[insight_idx]["topic_segmentation"] is None:
                remove_empty_insights_list.append(insight_idx)
        for insight_idx in remove_empty_insights_list:
            insights_json.pop(insight_idx)

        return insights_json

    def convert_json_to_str(self, insights_json: Dict[str, Dict[str,
                                                                str]]) -> str:
        r"""Convert the insights from json format to string format.

        Args:
            insights_json (Dict[str, Dict[str, str]]): The insights in json
                format.

        Returns:
            str: The insights in string format.
        """
        insights_str = ""
        for insight_idx, insight in insights_json.items():
            insights_str += f"{insight_idx}:\n"
            for key, value in insight.items():
                if value is not None:
                    insights_str += f"- {key}:\n{value}\n"
                else:
                    insights_str += f"- {key}:\nN/A\n"
        return insights_str
