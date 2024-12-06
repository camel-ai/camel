from camel.agents import ChatAgent
from camel.agents.programmed_agent_instruction import (
    ProgrammedAgentInstructionResult,
    programmable_capability,
)
from camel.synthetic_datagen.source2synth.models import (
    ContextPrompt,
    MultiHopQA,
)
from camel.messages import BaseMessage


class MultiHopGeneratorAgent(ChatAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.system_message = """You are an expert at generating multi-hop 
        question-answer pairs.
        For each context, you should:
        1. Identify multiple related facts or pieces of information
        2. Create questions that require reasoning across these multiple pieces
        3. Ensure the reasoning chain is clear and logical
        4. Generate questions that require at least 2-3 steps of reasoning
        5. Include the reasoning steps in the answer

        Format your response as:
        Question: [Complex question requiring multiple reasoning steps]
        Reasoning Steps:
        1. [First reasoning step]
        2. [Second reasoning step]
        3. [Final reasoning step]
        Answer: [Final answer]
        Supporting Facts: [List of relevant text segments used]
        """

    @programmable_capability
    def generate_multi_hop_qa(
        self, context: str
    ) -> ProgrammedAgentInstructionResult[MultiHopQA]:
        context_prompt = ContextPrompt(
            main_context=context, related_contexts=None
        )

        user_message = BaseMessage.make_user_message(
            content=context_prompt.model_dump_json(), role_name="User"
        )
        response = self.step(
            input_message=user_message, response_format=MultiHopQA
        )
        value = MultiHopQA.model_validate_json(response.msgs[0].content)

        if response.msgs:
            return ProgrammedAgentInstructionResult(
                user_message=user_message,
                agent_message=response.msgs[0],
                value=value,
            )
        raise RuntimeError("No response from agent")
