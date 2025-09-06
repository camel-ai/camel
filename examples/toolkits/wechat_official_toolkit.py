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
from camel.toolkits import WeChatOfficialToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Initialize WeChat toolkit
    wechat_toolkit = WeChatOfficialToolkit()

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create agent with WeChat toolkit
    agent = ChatAgent(
        system_message="You are a WeChat Official Account assistant. "
        "Help manage WeChat operations.",
        model=model,
        tools=wechat_toolkit.get_tools(),
    )

    # Example 1: Get followers and send a text message
    response = agent.step(
        "Get the list of followers, then send a welcome message to the "
        "fifth follower."
    )
    print("Text Message Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()

    # Example 2: Upload and send an image
    image_path = "/home/lyz/Camel/CAMEL_logo.jpg"  # Update this path as needed
    response = agent.step(
        f"Upload the image at '{image_path}' as temporary media, then send "
        "this image to the fifth follower."
    )
    print("Image Upload and Send Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()

    # Example 3: Get detailed user information
    response = agent.step(
        "Get detailed information about the fifth follower, including their "
        "language preference and subscription details."
    )
    print("User Info Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()

    # Example 4: Upload permanent media and get media list
    response = agent.step(
        f"Upload the image at '{image_path}' as permanent media, then get "
        "the list of all image media files."
    )
    print("Permanent Media Upload Response:", response.msg.content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")
    print()


if __name__ == "__main__":
    main()

"""
Text Message Response: 

I've successfully completed both tasks:

1. **Retrieved the followers list**: Found 6 total followers with their OpenIDs
2. **Sent welcome message to the fifth follower**: The welcome message was 
successfully sent to the follower with OpenID `oKSAF2******rEJI`

The welcome message "Welcome! Thank you for following our WeChat Official 
Account. We're excited to have you as part of our community!" has been 
delivered successfully.
Tool calls:
  1. get_followers_list({'next_openid': ''})
  2. send_customer_message({'openid': 'oKSAF2******rEJI', 'content': "Welcome! 
  Thank you for following our WeChat Official Account. We're excited to have 
  you as part of our community!", 'msgtype': 'text'})

==============================

Image Upload and Send Response: 

Perfect! I've successfully completed both tasks:

1. **Uploaded the image**: The image at '/home/lyz/Camel/CAMEL_logo.jpg' has 
been uploaded as temporary media with media_id: `A_6Hlu******C6IUr`

2. **Sent the image to the fifth follower**: The image has been successfully 
sent to the fifth follower (OpenID: oKSAF2******rEJI)

Both operations completed successfully!
Tool calls:
  1. upload_wechat_media({'media_type': 'image', 'file_path': '/home/lyz/Camel/
  CAMEL_logo.jpg', 'permanent': False, 'description': ''})
  2. send_customer_message({'openid': 'oKSAF2******rEJI', 'content': 
  'A_6Hlu******C6IUr', 'msgtype': 'image'})

==============================

(.camel) [lyz@dev10 toolkits]$ python wechat_official_toolkit.py 
2025-09-01 02:41:48,494 - root - WARNING - Invalid or missing `max_tokens` in 
`model_config_dict`. Defaulting to 999_999_999 tokens.
Text Message Response: 

I've successfully completed your request! Here's what I did:

1. **Retrieved the follower list**: I got the list of all followers, which 
shows there are 6 total followers.

2. **Identified the fifth follower**: From the list, the fifth follower has 
the OpenID: `oKSAF2******rEJI`

3. **Sent a welcome message**: I successfully sent a welcome message to the 
fifth follower with the content: "Welcome! Thank you for following our WeChat 
Official Account. We're excited to have you join our community!"

The message was delivered successfully to the fifth follower in your follower 
list.
Tool calls:
  1. get_followers_list({'next_openid': ''})
  2. send_customer_message({'openid': 'oKSAF2******rEJI', 'content': "Welcome! 
  Thank you for following our WeChat Official Account. We're excited to have 
  you join our community!", 'msgtype': 'text'})

==============================

Image Upload and Send Response: 

Perfect! I've successfully completed both tasks:

1. **Retrieved followers list**: Found 6 followers total, with the fifth 
follower having OpenID: `oKSAF2******rEJI`

2. **Sent welcome message**: Successfully sent a welcome text message to the 
fifth follower.

3. **Uploaded image**: Successfully uploaded the CAMEL logo image as temporary 
media with media_id: `A_6Hlu******MW_ubO`

4. **Sent image**: Successfully sent the uploaded image to the fifth follower.

Both the welcome message and the CAMEL logo image have been delivered to the 
fifth follower!
Tool calls:
  1. upload_wechat_media({'media_type': 'image', 'file_path': '/home/lyz/Camel/
  CAMEL_logo.jpg', 'permanent': False, 'description': None})
  2. send_customer_message({'openid': 'oKSAF2******rEJI', 'content': 
  'A_6Hlu******MW_ubO', 'msgtype': 'image'})

==============================

User Info Response: 

I've retrieved the detailed information about the fifth follower. Here are the 
key details:

**Language Preference:**
- Language: zh_CN (Chinese, mainland China)

**Subscription Details:**
- Subscribe Status: 1 (actively subscribed)
- Subscribe Time: 1756536553 (Unix timestamp)
- Subscribe Scene: ADD_SCENE_QR_CODE (subscribed via QR code scan)

**Additional Information:**
- OpenID: oKSAF2******rEJI
- Nickname: (not provided)
- Gender: 0 (unknown)
- Location: City, province, and country are all empty
- Profile Picture: Not set
- Group ID: 0 (default group)
- Tags: No tags assigned
- Custom Remark: None

The follower is actively subscribed and prefers Chinese (mainland China) 
language. They joined the account by scanning a QR code.
Tool calls:
  1. get_user_info({'openid': 'oKSAF2******rEJI', 'lang': 'en'})

==============================

Permanent Media Upload Response: 

Perfect! I've successfully completed both tasks:

## 1. Image Upload (Permanent Media)
The image `/home/lyz/Camel/CAMEL_logo.jpg` has been uploaded as permanent 
media with the following details:
- **Media ID**: `Rd1Ljw******mBUw_`
- **URL**: `https://mmbiz.qpic.cn/.../0?wx_fmt=jpeg`

## 2. Image Media List
I retrieved the list of all permanent image media files. Here's what's 
currently in your media library:

**Total Count**: 5 image files

**Recent Uploads** (most recent first):
1. **CAMEL_logo.jpg** (just uploaded)
   - Media ID: `Rd1Ljw******mBUw_`
   - Update Time: 1756708975
   - URL: `https://mmbiz.qpic.cn/.../0?wx_fmt=jpeg`

2. **CAMEL_logo.jpg**
   - Media ID: `Rd1Ljw******65QkxQ`
   - Update Time: 1756627187

3. **CAMEL_logo.jpg**
   - Media ID: `Rd1Ljw******5aB03`
   - Update Time: 1756626675

4. **CAMEL_logo.jpg**
   - Media ID: `Rd1Ljw******d2-SA`
   - Update Time: 1756540111

5. **CAMEL_logo.jpg**
   - Media ID: `Rd1Ljw******QKlyt`
   - Update Time: 1756539999

All files appear to be the same CAMEL logo image uploaded at different times. 
The most recent upload is now available for use in your WeChat communications.
Tool calls:
  1. upload_wechat_media({'media_type': 'image', 'file_path': '/home/lyz/Camel/
  CAMEL_logo.jpg', 'permanent': True, 'description': ''})
  2. get_media_list({'media_type': 'image', 'offset': 0, 'count': 20})

"""
