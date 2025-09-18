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
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ResendToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Initialize ResendToolkit
    resend_toolkit = ResendToolkit()

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create agent with ResendToolkit
    agent = ChatAgent(
        system_message="You are an email assistant. "
        "Help send emails using the ResendToolkit.The sender email is "
        "onboarding@resend.dev",
        model=model,
        tools=resend_toolkit.get_tools(),
    )

    # Example 1: Send a simple HTML email
    print("=" * 50)
    print("Example 1: HTML Email")
    print("=" * 50)
    response = agent.step(
        "Send an email to user@example.com with subject 'Welcome to CAMEL AI' "
        "and HTML content '<h1>Welcome!</h1><p>Thank you for joining "
        "CAMEL AI.</p>' from onboarding@resend.dev"
    )
    print(response.msg.content)

    # Example 2: Send email with CC
    print("\n" + "=" * 50)
    print("Example 2: Email with CC")
    print("=" * 50)
    response = agent.step(
        "Send an email to user1@example.com with CC to user2@example.com "
        "with subject 'CAMEL AI Test Email' and text content "
        "'This is a test email from CAMEL AI ResendToolkit.' "
        "from onboarding@resend.dev"
    )
    print(response.msg.content)

    # Example 3: Send email with both HTML and text content
    print("\n" + "=" * 50)
    print("Example 3: Newsletter Email")
    print("=" * 50)
    response = agent.step(
        "Send an email to user@example.com with subject 'Weekly Newsletter' "
        "from onboarding@resend.dev with HTML content "
        "'<h2>Newsletter</h2><p>Here are this week updates.</p>' "
        "and plain text content 'Newsletter\n\nHere are this week updates.'"
    )
    print(response.msg.content)


if __name__ == "__main__":
    main()

"""
==================================================
Example 1: HTML Email
==================================================
Your email has been sent successfully.

Details:
- To: user@example.com
- From: onboarding@resend.dev
- Subject: Welcome to CAMEL AI
- Content type: HTML
- Email ID: 92fd****b683

==================================================
Example 2: Email with CC
==================================================
Your email has been sent successfully.

Details:
- To: user1@example.com
- CC: user2@example.com
- From: onboarding@resend.dev
- Subject: CAMEL AI Test Email
- Content type: Text
- Email ID: b0e3****0211

==================================================
Example 3: Newsletter Email
==================================================
Your email has been sent successfully.

Details:
- To: user@example.com
- From: onboarding@resend.dev
- Subject: Weekly Newsletter
- Content types: HTML and Plain Text
- Email ID: 9bd0****86b1
"""
