from typing import Any, List

import tiktoken

from camel.message import OpenAIMessage
from camel.typing import ModeType


def count_tokens_openai_chat_models(
        messages: List[OpenAIMessage],
        encoding: Any) -> int:
    num_tokens = 0
    for message in messages:
        # message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def num_tokens_from_messages(
        messages: List[OpenAIMessage],
        model: ModeType) -> int:
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model.value)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == ModeType.GPT_3_5_TURBO:
        return count_tokens_openai_chat_models(messages, encoding)
    elif model == ModeType.GPT_4:
        return count_tokens_openai_chat_models(messages, encoding)
    elif model == ModeType.GPT_4_32k:
        return count_tokens_openai_chat_models(messages, encoding)
    else:
        raise NotImplementedError(
            f"`num_tokens_from_messages`` is not presently implemented "
            f"for model {model}. "
            f"See https://github.com/openai/openai-python/blob/main/chatml.md "
            f"for information on how messages are converted to tokens."
            f"See https://platform.openai.com/docs/models/gpt-4"
            f"or https://platform.openai.com/docs/models/gpt-3-5"
            f"for information on openai chat models.")


def get_model_token_limit(model: ModeType) -> int:
    """Returns the maximum number of tokens for a given model."""
    if model == ModeType.GPT_3_5_TURBO:
        return 4096
    if model == ModeType.GPT_4:
        return 8192
    if model == ModeType.GPT_4_32k:
        return 32768
