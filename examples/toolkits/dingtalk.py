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

import json
import os
from unittest.mock import MagicMock, patch

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import DingtalkToolkit
from camel.types import ModelPlatformType, ModelType


def print_tool_calls(tool_calls):
    """Helper function to print tool calls with formatted JSON arguments."""
    for i, tool_call in enumerate(tool_calls, 1):
        print(f"  {i}. {tool_call.tool_name}")
        print("     Args:")

        # Print each argument with proper formatting
        for key, value in tool_call.args.items():
            if isinstance(value, str) and ('\\n' in value or '\n' in value):
                # Handle multiline strings specially
                print(f"       {key}: |")
                # Replace escaped newlines and split into lines
                lines = value.replace('\\n', '\n').split('\n')
                for line in lines:
                    print(f"         {line}")
            else:
                # Regular single-line values
                formatted_value = json.dumps(value, ensure_ascii=False)
                print(f"       {key}: {formatted_value}")
        print()


def main():
    # Set up mock environment variables for testing
    os.environ["DINGTALK_APP_KEY"] = "mock_app_key"
    os.environ["DINGTALK_APP_SECRET"] = "mock_app_secret"
    os.environ["DINGTALK_WEBHOOK_URL"] = (
        "https://oapi.dingtalk.com/robot/send?access_token=mock_webhook_token"
    )
    os.environ["DINGTALK_WEBHOOK_SECRET"] = "mock_webhook_secret"

    # Mock the DingtalkToolkit methods to return realistic responses
    with (
        patch(
            'camel.toolkits.dingtalk._get_dingtalk_access_token'
        ) as mock_token,
        patch(
            'camel.toolkits.dingtalk._make_dingtalk_request'
        ) as mock_request,
        patch('camel.toolkits.dingtalk.requests.post') as mock_post,
    ):
        # Mock access token
        mock_token.return_value = "mock_access_token_12345"

        # Mock API responses
        mock_request.side_effect = [
            # get_department_list response
            {
                'errcode': 0,
                'department': [
                    {'id': 1, 'name': '技术部', 'parentid': 0},
                    {'id': 2, 'name': '产品部', 'parentid': 0},
                    {'id': 3, 'name': '运营部', 'parentid': 0},
                ],
            },
            # send_text_message response
            {'errcode': 0, 'task_id': '12345'},
            # get_user_info response
            {
                'errcode': 0,
                'userid': 'test_userid',
                'name': '测试用户',
                'department': [1, 2],
                'position': '高级工程师',
                'mobile': '138****1234',
                'email': 'test@company.com',
            },
            # send_markdown_message response
            {'errcode': 0, 'task_id': '12346'},
            # search_users_by_name response
            {
                'errcode': 0,
                'userlist': [
                    {
                        'userid': 'test_userid',
                        'name': '测试用户',
                        'department': [1],
                    },
                    {
                        'userid': 'test_user2',
                        'name': '测试用户2',
                        'department': [2],
                    },
                    {
                        'userid': 'test_user3',
                        'name': '测试用户3',
                        'department': [3],
                    },
                ],
            },
            # send_text_message response (second call)
            {'errcode': 0, 'task_id': '12347'},
        ]

        # Mock webhook responses
        mock_webhook_response = MagicMock()
        mock_webhook_response.json.return_value = {'errcode': 0}
        mock_post.return_value = mock_webhook_response

        print("🚀 Running Dingtalk Toolkit Examples with Mocked Responses")
        print("=" * 60)

        # Initialize Dingtalk toolkit
        dingtalk_toolkit = DingtalkToolkit()

        # Create model
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Create agent with Dingtalk toolkit
        agent = ChatAgent(
            system_message=(
                "You are a Dingtalk enterprise communication assistant. "
                "Help manage Dingtalk operations and send messages to users."
            ),
            model=model,
            tools=dingtalk_toolkit.get_tools(),
        )

        # Example 1: Get department list and send a text message
        print("\n1️⃣ Example 1: Get departments and send welcome message")
        response = agent.step(
            "Get the list of departments, then send a welcome message to user "
            "'test_userid' saying 'Welcome to our Dingtalk integration!'"
        )
        print("Text Message Response:", response.msg.content)
        print("Tool calls:")
        print_tool_calls(response.info['tool_calls'])
        print()

        # Example 2: Get user information and send markdown message
        print("\n2️⃣ Example 2: Get user info and send markdown message")
        response = agent.step(
            "Get detailed information about user 'test_userid', then send a "
            "markdown message with their details formatted nicely."
        )
        print("User Info and Markdown Response:", response.msg.content)
        print("Tool calls:")
        print_tool_calls(response.info['tool_calls'])
        print()

        # Example 3: Search users and send webhook notification
        print("\n3️⃣ Example 3: Search users and send webhook notification")
        response = agent.step(
            "Search for users with name containing 'test', then send a "
            "webhook "
            "message to notify about the search results."
        )
        print("User Search and Webhook Response:", response.msg.content)
        print("Tool calls:")
        print_tool_calls(response.info['tool_calls'])
        print()

        # Example 4: Send different message types
        print("\n4️⃣ Example 4: Send multiple message types")
        response = agent.step(
            "Send a text message to user 'test_userid' with content "
            "'Hello from CAMEL!', then send a webhook message with markdown "
            "format showing system status."
        )
        print("Multiple Message Types Response:", response.msg.content)
        print("Tool calls:")
        print_tool_calls(response.info['tool_calls'])
        print()

        print("=" * 60)
        print("✅ All examples completed with mocked responses!")
        print("\n📋 Copy the responses above to update the example file.")


if __name__ == "__main__":
    main()

"""
============================================================

1️⃣ Example 1: Get departments and send welcome message
Text Message Response: I retrieved the department list and sent the welcome 
message.

Departments found:
- 1: 技术部
- 2: 产品部
- 3: 运营部

Message delivery:
- Sent "Welcome to our Dingtalk integration!" to user test_userid.
Tool calls:
  1. get_department_list
     Args:
       dept_id: null

  2. send_text_message
     Args:
       userid: "test_userid"
       content: "Welcome to our Dingtalk integration!"



2️⃣ Example 2: Get user info and send markdown message
User Info and Markdown Response: I fetched the user details and sent a 
formatted markdown message.

User details:
- Name: 测试用户
- UserID: test_userid
- Departments: 技术部, 产品部
- Position: 高级工程师
- Mobile: 138****1234
- Email: test@company.com

Message: "User Profile — 测试用户" sent successfully.
Tool calls:
  1. get_user_info
     Args:
       userid: "test_userid"

  2. send_markdown_message
     Args:
       userid: "test_userid"
       title: "User Profile — 测试用户"
       markdown_content: |
         ### 用户资料
         
         - **姓名**: 测试用户  
         - **用户ID**: test_userid  
         - **部门**: 技术部, 产品部  
         - **职位**: 高级工程师  
         - **手机**: 138****1234  
         - **邮箱**: test@company.com



3️⃣ Example 3: Search users and send webhook notification
User Search and Webhook Response: Search completed and webhook notification 
sent. Results:
- 测试用户 (test_userid) — 部门: 技术部
- 测试用户2 (test_user2) — 部门: 产品部
- 测试用户3 (test_user3) — 部门: 运营部
- Total: 3 users
Tool calls:
  1. search_users_by_name
     Args:
       name: "test"

  2. send_webhook_message
     Args:
       content: |
         # User search results for 'test'
         
         - 测试用户 (test_userid) — 部门: 技术部
         - 测试用户2 (test_user2) — 部门: 产品部
         - 测试用户3 (test_user3) — 部门: 运营部
         
         Total: 3 users found.
       msgtype: "markdown"
       title: "User Search Results"
       webhook_url: null
       webhook_secret: null



4️⃣ Example 4: Send multiple message types
Multiple Message Types Response: Done — text message to test_userid sent and 
webhook status message posted.
Tool calls:
  1. send_text_message
     Args:
       userid: "test_userid"
       content: "Hello from CAMEL!"

  2. send_webhook_message
     Args:
       content: |
         ### System Status
         
         - **Overall**: ✅ Operational
         - **Uptime**: 72 hours
         - **Services**:
           - API: ✅ Healthy
           - Messaging: ✅ Healthy
           - Database: ✅ Healthy
         
         _Last checked: just now_
       msgtype: "markdown"
       title: "System Status"
       webhook_url: null
       webhook_secret: null


============================================================
"""
