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

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType


class InsightAgent(ChatAgent):
    r"""An agent that aims to generate insights from a provided text.
    Args:
        model_type (ModelType, optional): The type of model to use for the
            agent. (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="Insight Agent",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You generate insights from a provided text.",
        )
        super().__init__(system_message, model_type, model_config)

    def run(
        self,
        context_text: Union[str, TextPrompt],
        insights_instruction: Optional[Union[str, TextPrompt]] = None,
    ) -> Dict[str, Dict[str, str]]:
        r"""Generate role names based on the input task prompt.

        Args:
            context_text (Union[str, TextPrompt]): The context text to
                generate insights from.
            insights_instruction (Optional[Union[str, TextPrompt]], optional):
                The instruction for generating insights. (default: :obj:`None`)

        Returns:
            Dict[str, Dict[str, str]]: The generated insights from the context
                text.
        """
        self.reset()

        insights_instruction_prompt = \
            TextPrompt("Based on the CONTEXT TEXT " +
                       "provided, generate a comprehensive set of distinct " +
                       "insights following the \"RULES OF INSIGHTS " +
                       "GENERATION\" and use the \"ANSWER TEMPLATE\" to " +
                       "structure your response. Extract as many meaningful " +
                       "insights as the context allows. " +
                       "{insights_instruction}\nYour answer MUST strictly " +
                       "adhere to the structure of ANSWER TEMPLATE, ONLY " +
                       "fill in  the BLANKs, and DO NOT alter or modify any " +
                       "other part of the template.\n")
        context_text_prompt = TextPrompt(
            "===== CONTEXT TEXT =====\n{context_text}\n\n")
        insights_prompt = """===== INSIGHTS GENERATION WITH MATHEMATICAL CONTEXT =====
Understanding and generating insights from textual data can be represented by the model:
``L_I: A_I -> n_I * B_I``.
Where:
- $A_I$: The initial CONTEXT TEXT.
- $B_I$: The insights derived from the CONTEXT TEXT.
- $n_I$: The number of insights generated.
- $L_I$: The rules or methodology transforming the CONTEXT TEXT into insights.

===== RULES OF INSIGHTS GENERATION =====
According to the following rules, extract insights and details in your answer from the CONTEXT TEXT:
1. Text/Code Decomposition (Breaking it Down):
- Topic/Functionality Segmentation: Divide the CONTEXT TEXT (represented by $A_I$) into main topics or themes. What is more, multiple topics or themes are possible.
- Entity/Label/Code Environment Recognition:
    a. Identify and categorize entities such as the names, locations, dates, specific technical terms or contextual parameters that might be associated with events, innovations post-2023.
    b. The output of the entities/labels will be used as tags or labels for semantic similarity searches. The entities/labels may be the words, or phrases, each of them should contain valuable, high information entropy information, and should be independent.
    c. Ensure that the identified entities are formatted in a manner suitable for database indexing and retrieval. Organize the entities into categories, and combine the category with its instance into a continuous phrase, without using colons or other separators.
    d. Format these entities for database indexing: output the category rather than its instance/content into a continuous phrase. For example, instead of "Jan. 02", identify it as "Event time".
- Extract Details: Within these main topics or themes, identify facts, statements, claims, contextual parameters, numbers, etc.. Please identify and write any detail(s) or term(s) from the CONTEXT TEXT that are either not present in your knowledge base, might be post-2023 developments, or can influence the nature of any task to be executed.
2. Question Generation (Identifying Potential Unknowns):
For each identified entity or detail from the decomposition:
- Cross-Referencing: Check against your knowledge base up to 2023. If it's a known entity or detail, move on. If not:
    a. Contextual Understanding: Even if the entity is unknown, understanding the context can be vital. For instance, even if I don't know a specific person named in 2023, if the text mentions they are an astronaut, I can craft my questions based on that role.
    b. Formulate/Code Questions: Generate specific questions targeting the unfamiliar or context-specific information. Questions can vary in nature:
        i. Factual: "Who/What is [unknown entity/infomation/code]?"
        ii. Conceptual: "How does the [unknown technology/code] work?"
        iii. Historical: "When was [unknown event/code] first introduced?"
        iv. Implication-based: "What is the significance of [unknown event/code] in related domain knowledge?"
    c. Iterative Feedback: Depending on the user's responses to these questions, you can generate follow-up questions for deeper understanding.
3. Insight Generation:
- Apply the rules or methodology represented by $L_I$ to transition from the initial CONTEXT TEXT ($A_I$) to a set of insights ($n_I$ * $B_I$), where $n_I$ indicates the number of insights obtained.
- Adhere to ANSWER TEMPLATE. In answer, use nouns and phrases to replace sentences.

"""  # noqa: E501

        insight_template = (
            "Insight <NUM>:\n" + "- Topic Segmentation:\n<BLLANK>\n" +
            "- Entity Recognition:\n[<BLANK>, <BLANK>] (include square "
            "brackets)\n- Extract Details:\n<BLANK>\n"
            "- Contextual Understanding:\n<BLANK or N/A>\n"
            "- Formulate Questions:\n<BLANK>\n"
            "- Answer to \"Formulate Questions\" using "
            "CONTEXT TEXT:\n<BLANK>\n"
            "- Iterative Feedback:\n<BLANK>\n")
        answer_template_prompt = TextPrompt(
            "===== ANSWER TEMPLATE =====\n" +
            "You need to generate multiple insights, and the number of " +
            "insights depend on the number of Topic/Functionality " +
            "Segmentation. So the total number of insights is <NUM>.\n" +
            f"{insight_template}\n")
        insights_generation_prompt = insights_instruction_prompt + \
            context_text_prompt + insights_prompt + answer_template_prompt
        insights_generation = insights_generation_prompt.format(
            insights_instruction=insights_instruction or "",
            context_text=context_text)

        insights_generation_msg = BaseMessage.make_user_message(
            role_name="Insight Agent", content=insights_generation)

        response = self.step(input_message=insights_generation_msg)

        if response.terminated:
            raise RuntimeError("Insights generation failed. Error:\n" +
                               f"{response.info}")
        msg = response.msg  # type: BaseMessage

        # Replace the "N/A", "None", "NONE" with None
        def handle_none_values_in_msg(value):
            if value.strip() in ["N/A", "None", "NONE", "null", "NULL"]:
                return None
            return value.strip() if value else None

        # Parse the insights from the response
        insights_pattern = (r"Insight (\d+):" +
                            r"(?:\s+- Topic Segmentation:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Entity Recognition:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Extract Details:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Contextual Understanding:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Formulate Questions:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Answer to \"Formulate Questions\" using "
                            r"CONTEXT TEXT:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?" +
                            r"(?:\s+- Iterative Feedback:\s*((?:.|\n)+?)"
                            r"(?=\s+- \w+ |\Z|Insight))?")

        insights_matches = re.findall(insights_pattern, msg.content, re.DOTALL)

        insights_json = {}
        for match in insights_matches:
            (idx, topic, entity, extract, context, question, answer,
             feedback) = match
            insights_json[f"insight {idx}"] = {
                "topic_segmentation": handle_none_values_in_msg(topic),
                "entity_recognition": handle_none_values_in_msg(entity),
                "extract_details": handle_none_values_in_msg(extract),
                "contextual_understanding": handle_none_values_in_msg(context),
                "formulate_questions": handle_none_values_in_msg(question),
                "answer_to_formulate_questions":
                handle_none_values_in_msg(answer),
                "iterative_feedback": handle_none_values_in_msg(feedback),
            }

            # Convert the value of entity_recognition from string to list
            if insights_json[f"insight {idx}"]["entity_recognition"]:
                entity_recognition_list = (
                    insights_json[f"insight {idx}"]
                    ["entity_recognition"].strip('[]').split(', '))
                # Use list comprehension to filter out strings of digits
                entity_recognition_list = [
                    er for er in entity_recognition_list if not er.isdigit()
                ]
                insights_json[f"insight {idx}"]["entity_recognition"] = \
                    entity_recognition_list

        # Remove the insight if the topic segmentation/insight is None or empty
        remove_empty_insights_list = []
        for insight_idx, _ in insights_json.items():
            if insights_json[insight_idx]["topic_segmentation"] is None:
                remove_empty_insights_list.append(insight_idx)
        for insight_idx in remove_empty_insights_list:
            insights_json.pop(insight_idx)

        return insights_json

    def transform_into_text(self, insights: Dict[str, Dict[str, str]],
                            answer_template: [str, TextPrompt]) -> str:
        r"""Transform the insights into text format.

        Args:
            insights (Dict[str, Dict[str, str]]): The insights from the
                context text, generated by the :meth:`run` method.
            answer_template (Union[str, TextPrompt]): The answer template for
                transforming the insights into text format by LLM. In the
                answer template, the <BLANK> is the placeholder for the
                generated answer (text).

        Returns:
            str: The organized text of the insights.
        """
        transform_into_text_prompt = """You are asked to generate the answer according to RULES OF TRANSFORMING INSIGHTS INTO TEXTUAL FORMAT.
Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify any other part of the template.
===== RULES OF TRANSFORMING INSIGHTS INTO TEXTUAL FORMAT =====
Your task is to transform a set of insights from textual data into a text format. The focus here is on ensuring that each insight is accurately transcribed into text, without necessarily creating a coherent narrative or maintaining logical flow between insights.

Here is how you should approach this task:
1. Reviewing Each Insight:
    - Examine each insight in the dictionary. Understand the content and context of each insight, focusing on the topic segmentation, entity recognition, and specific details provided.
2. Textual Representation:
    - For all insights, transcribe its details into text form. Ensure that the key points and important information are accurately represented.
    - Maintain the original structure and content of each insight. The goal is to reflect the insights as they are, without altering or omitting any important information.
    - If there are multiple insights, you should not transform the insights separately, but rather as a whole. The insights should be presented in a single text, rather than as separate insights.
3. Direct Transcription:
    - Keep the transcription direct and straightforward. The aim is to convert the insights into text, rather than to create a story or narrative.
    - If insights contain specific questions or queries, include them as part of the transcription, along with their respective answers if available.
4. Compiling the Text:
    - Compile all the transcribed insights into one document. While the insights may not flow into each other or form a cohesive text, ensure that each one is clearly distinguished and easily identifiable.
    - Use headers or bullet points to separate different insights for clarity.
    - The index of the insights should not appear in the final text.
5. Final Review:
    - Check the final text to ensure that all insights have been accurately and completely transcribed.

"""  # noqa: E501
        insights_prompt = TextPrompt("===== INSIGHTS =====\n{insights}\n\n")
        if answer_template is None or answer_template == "":
            answer_template_prompt = TextPrompt(
                "===== ANSWER TEMPLATE =====\n<BLANK>")
        else:
            answer_template_prompt = TextPrompt(
                f"===== ANSWER TEMPLATE =====\n{answer_template}\n")

        transformed_text_generation_prompt = transform_into_text_prompt + \
            insights_prompt + answer_template_prompt

        transformed_text_generation = \
            transformed_text_generation_prompt.format(
                insights=self.convert_json_to_str(insights))

        transformed_text_generation_msg = BaseMessage.make_user_message(
            role_name="Insight Synthesizer",
            content=transformed_text_generation)

        response = self.step(input_message=transformed_text_generation_msg)

        if response.terminated:
            raise RuntimeError(
                "Transforming insights into text failed. Error:\n" +
                f"{response.info}")
        msg = response.msg  # type: BaseMessage

        transformed_text = msg.content

        if transformed_text is None:
            raise RuntimeError("Transformed text is None.")

        return transformed_text

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
        return insights_str.strip("\n")
