# Copyright Sierra

import abc
import enum
from typing import Any, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType


def _build_chat_agent(
    model_name: str,
    provider: Optional[str],
    temperature: float,
) -> ChatAgent:
    platform = ModelPlatformType.from_name(
        provider or ModelPlatformType.DEFAULT.value
    )
    backend = ModelFactory.create(
        model_platform=platform,
        model_type=model_name,
        model_config_dict={"temperature": temperature},
    )
    return ChatAgent(model=backend)


def _usage_from_response(response: Any) -> float:
    usage = (
        response.info.get("usage")
        if isinstance(response.info, dict)
        else None
    )
    return float(usage.get("total_tokens", 0)) if usage else 0.0


class BaseUserSimulationEnv(abc.ABC):
    metadata = {}

    @abc.abstractmethod
    def reset(self, instruction: Optional[str] = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def step(self, content: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_total_cost(self) -> float:
        raise NotImplementedError


class HumanUserSimulationEnv(BaseUserSimulationEnv):
    def reset(self, instruction: str) -> str:
        return input(f"{instruction}\n")

    def step(self, content: str) -> str:
        return input(f"{content}\n")

    def get_total_cost(self) -> float:
        return 0.0


class LLMUserSimulationEnv(BaseUserSimulationEnv):
    def __init__(
        self,
        model: str,
        provider: Optional[str],
        temperature: float = 0.0,
    ) -> None:
        self.temperature = temperature
        self.agent = _build_chat_agent(model, provider, temperature)
        self.instruction: Optional[str] = None
        self.messages: List[Dict[str, str]] = []
        self.total_usage = 0.0

    def build_system_prompt(self, instruction: Optional[str]) -> str:
        instruction_display = (
            f"\n\nInstruction: {instruction}\n" if instruction else ""
        )
        return (
            f"You are a user interacting with an agent.{instruction_display}\n"
            "Rules:\n"
            "- Just generate one line at a time to simulate the user's "
            "message.\n"
            "- Do not give away all the instruction at once.\n"
            "- Do not hallucinate information that is not provided in the "
            "instruction.\n"
            "- If the instruction goal is satisfied, generate '###STOP###'.\n"
            "- Try to make the conversation as natural as possible,\n"
            "  and stick to the personalities in the instruction."
        )

    def reset(self, instruction: Optional[str] = None) -> str:
        self.instruction = instruction
        self.messages = []
        self.agent.reset()

        system_prompt = self.build_system_prompt(instruction)
        response = self.agent.step(
            BaseMessage.make_user_message(
                role_name="System",
                content=(
                    system_prompt
                    + "\n\nAgent: Hi! How can I help you today?\nUser:"
                ),
            )
        )
        self.total_usage += _usage_from_response(response)
        user_msg = response.msg.content.strip()
        self.messages.append({"role": "user", "content": user_msg})
        return user_msg

    def _conversation_prompt(self) -> str:
        transcript_lines: List[str] = []
        for message in self.messages:
            label = "User" if message["role"] == "user" else "Agent"
            transcript_lines.append(f"{label}: {message['content']}")
        transcript = "\n".join(transcript_lines)
        return f"""Previous conversation:
{transcript}

Generate the next user message. Remember:
- One line at a time
- Don't reveal all information at once
- Respond with '###STOP###' when goal is satisfied

User:"""

    def _invoke_agent(self, prompt: str) -> str:
        response = self.agent.step(
            BaseMessage.make_user_message(role_name="System", content=prompt)
        )
        self.total_usage += _usage_from_response(response)
        return response.msg.content.strip()

    def step(self, content: str) -> str:
        self.messages.append({"role": "assistant", "content": content})
        prompt = self._conversation_prompt()
        user_msg = self._invoke_agent(prompt)
        self.messages.append({"role": "user", "content": user_msg})
        return user_msg

    def get_total_cost(self) -> float:
        return self.total_usage


class ReactUserSimulationEnv(LLMUserSimulationEnv):
    def build_system_prompt(self, instruction: Optional[str]) -> str:
        instruction_display = (
            f"\n\nInstruction: {instruction}\n" if instruction else ""
        )
        return (
            f"You are a user interacting with an agent.{instruction_display}\n"
            "Rules:\n"
            "- First think (Thought), then provide the line to send "
            "(Action).\n"
            "- Format:\n"
            "Thought: <reasoning>\n"
            "Action: <message to agent>\n"
            "- Respond with '###STOP###' (as the Action) when finished."
        )

    def _invoke_agent(self, prompt: str) -> str:
        raw = super()._invoke_agent(prompt)
        if "Action:" in raw:
            return raw.split("Action:", 1)[-1].strip()
        if "###STOP###" in raw:
            return "###STOP###"
        return raw


class VerifyUserSimulationEnv(LLMUserSimulationEnv):
    def __init__(
        self,
        model: str,
        provider: Optional[str],
        max_attempts: int = 3,
        temperature: float = 0.0,
    ) -> None:
        super().__init__(
            model=model,
            provider=provider,
            temperature=temperature,
        )
        self.max_attempts = max_attempts
        self.verifier_agent = _build_chat_agent(
            model, provider, temperature=temperature
        )

    def _verify_candidate(self, candidate: str) -> bool:
        transcript = "\n".join(
            [
                f"{map_role_label(msg['role'])}: {msg['content']}"
                for msg in self.messages
            ]
        )
        prompt = f"""Instruction: {self.instruction or ''}

Transcript:
{transcript}

Candidate user response: {candidate}

Has the instruction goal been satisfied?
Answer YES or NO and explain briefly."""

        self.verifier_agent.reset()
        response = self.verifier_agent.step(
            BaseMessage.make_user_message(role_name="System", content=prompt)
        )
        self.total_usage += _usage_from_response(response)
        return "YES" in response.msg.content.upper()

    def step(self, content: str) -> str:
        self.messages.append({"role": "assistant", "content": content})
        prompt = self._conversation_prompt()
        last_candidate = ""
        for _ in range(self.max_attempts):
            candidate = self._invoke_agent(prompt)
            if self._verify_candidate(candidate):
                self.messages.append({"role": "user", "content": candidate})
                return candidate
            last_candidate = candidate
        self.messages.append({"role": "user", "content": last_candidate})
        return last_candidate


class ReflectionUserSimulationEnv(LLMUserSimulationEnv):
    def __init__(
        self,
        model: str,
        provider: Optional[str],
        temperature: float = 0.0,
    ) -> None:
        super().__init__(
            model=model,
            provider=provider,
            temperature=temperature,
        )
        self.reflection_agent = _build_chat_agent(
            model, provider, temperature=temperature
        )

    def _reflect(self, candidate: str) -> str:
        prompt = f"""Instruction: {self.instruction or ''}

You were about to say: \"{candidate}\"

Reflect:
1. Is this response clear and effective?
2. Does it help achieve your goal?
3. Should you modify it?

Final response:"""
        self.reflection_agent.reset()
        response = self.reflection_agent.step(
            BaseMessage.make_user_message(role_name="System", content=prompt)
        )
        self.total_usage += _usage_from_response(response)
        return response.msg.content.strip()

    def step(self, content: str) -> str:
        first_pass = super().step(content)
        if "###STOP###" in first_pass:
            return first_pass
        refined = self._reflect(first_pass)
        self.messages[-1] = {"role": "user", "content": refined}
        return refined


def map_role_label(role: str) -> str:
    if role == "user":
        return "Customer"
    if role == "assistant":
        return "Agent"
    return role.capitalize()


class UserStrategy(str, enum.Enum):
    HUMAN = "human"
    LLM = "llm"
    REACT = "react"
    VERIFY = "verify"
    REFLECTION = "reflection"


def load_user(
    user_strategy: Union[str, UserStrategy],
    model: Optional[str],
    provider: Optional[str],
    temperature: float = 0.0,
) -> BaseUserSimulationEnv:
    strategy = UserStrategy(user_strategy)
    if strategy is UserStrategy.HUMAN:
        return HumanUserSimulationEnv()

    if model is None:
        raise ValueError(
            "User simulation requires `user_model` to be specified."
        )

    if strategy is UserStrategy.LLM:
        return LLMUserSimulationEnv(
            model=model,
            provider=provider,
            temperature=temperature,
        )
    if strategy is UserStrategy.REACT:
        return ReactUserSimulationEnv(
            model=model,
            provider=provider,
            temperature=temperature,
        )
    if strategy is UserStrategy.VERIFY:
        return VerifyUserSimulationEnv(
            model=model,
            provider=provider,
            temperature=temperature,
        )
    if strategy is UserStrategy.REFLECTION:
        return ReflectionUserSimulationEnv(
            model=model,
            provider=provider,
            temperature=temperature,
        )

    raise ValueError(f"Unsupported user strategy: {user_strategy}")
