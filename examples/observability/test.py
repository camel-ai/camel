import os
from datetime import datetime

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType
from camel.utils import get_langfuse_status
from camel.utils.langfuse import (
    configure_langfuse,
    is_langfuse_available,
    set_current_agent_session_id,
)

# Model configuration (can be set via environment variables or modified here)
MODEL_URL = os.environ.get("MODEL_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-chat")
API_KEY = os.environ.get("API_KEY", "sk-264dff897d964a5a834f6d1afa446351")

# Langfuse configuration
LANGFUSE_ENABLED = os.environ.get("LANGFUSE_ENABLED", "true").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.environ.get(
    "LANGFUSE_PUBLIC_KEY", "pk-lf-4131c68a-f15d-491f-9e14-fa24825ea886"
)
LANGFUSE_SECRET_KEY = os.environ.get(
    "LANGFUSE_SECRET_KEY", "sk-lf-06b28471-168c-43f2-a492-95b5a4954265"
)
LANGFUSE_HOST = os.environ.get(
    "LANGFUSE_HOST",
    os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
)

# Create timestamp for this session
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Configure Langfuse if enabled
if LANGFUSE_ENABLED:
    configure_langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
        enabled=True,
    )

    langfuse_session_id = f"langfuse-example-session-{SESSION_TIMESTAMP}"
    set_current_agent_session_id(langfuse_session_id)

    status = get_langfuse_status()
    if is_langfuse_available():
        print(f"[Langfuse] Tracing enabled | Session: {langfuse_session_id}")
    else:
        print(
            f"[Langfuse] Tracing requested but not available. Status: {status}"
        )

math_toolkit = [*MathToolkit().get_tools()]

# Create deepseek model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type=MODEL_NAME,
    url=MODEL_URL,
    api_key=API_KEY,
    model_config_dict={
        "temperature": 0.7,
        "max_tokens": 2048,
    },
)

# Define system message
sys_msg = "You are a helpful AI assistant, skilled at answering questions."

# Create agent
camel_agent = ChatAgent(
    system_message=sys_msg, model=model, tools=math_toolkit
)

# User message
user_msg = "Calculate the square root after adding 222991 and 1111"

print("\n" + "=" * 80)
print("Langfuse Status:")
print("=" * 80)
print(get_langfuse_status())
print("=" * 80 + "\n")

response = camel_agent.step(user_msg)
print(response.msgs[0].content)
