# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ResendMCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    resend_mcp_toolkit = ResendMCPToolkit(
        api_key="your_resend_api_key_here",
        mcp_server_path="/path/to/mcp-send-email/build/index.js",
        sender_email="noreply@yourdomain.com",  # Optional: your verified domain
        reply_to_email="support@yourdomain.com",  # Optional: reply-to address
    )

    # connect to resend mcp
    await resend_mcp_toolkit.connect()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    chat_agent = ChatAgent(
        model=model,
        tools=resend_mcp_toolkit.get_tools(),
    )

    response = await chat_agent.astep(
        "Send an email to user@domain.com with subject 'camel' and message 'Hello! This is a greeting from CAMEL AI toolkit.' No CC, no BCC, send immediately.",
    )
    print(response.msg.content)

    # disconnect from resend mcp
    await resend_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

"""
==============================================================================
Perfect! Your email has been sent successfully. 

Here are the details:
- **Recipient**: 790221864@qq.com
- **Subject**: camel
- **Message**: Hello! This is a greeting from CAMEL AI toolkit.
- **Email ID**: bf63e8ae-c5bd-4b7e-a9a9-729e7c79d9f0

The email was scheduled to be sent in 1 minute (as the system requires future scheduling) and should arrive shortly.
==============================================================================
"""