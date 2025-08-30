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

"""
WeChat Official Account Toolkit Example

Before running this example, you need to:
1. Apply for a WeChat test account: https://mp.weixin.qq.com/debug/cgi-bin/sandboxinfo?action=showinfo&t=sandbox/index
2. Get your appID and appsecret from the test account dashboard
3. Set environment variables:
   export WECHAT_APP_ID="your_test_appid"
   export WECHAT_APP_SECRET="your_test_appsecret"
4. Add your server IP to the IP whitelist in the test account settings
5. Follow your test account with WeChat to get test users

Reference: https://mp.weixin.qq.com/debug/cgi-bin/sandboxinfo?action=showinfo&t=sandbox/index
"""

import os
import json
from camel.toolkits import WeChatOfficialToolkit


import os
import json

def pretty_print(title, data):
    print(f"\n--- {title} ---")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)

def main():
    wechat_toolkit = WeChatOfficialToolkit()

    followers_result = wechat_toolkit.get_followers_list()
    pretty_print("Followers", followers_result)

    try:
        test_openid = followers_result['data']['openid'][3]
        pretty_print("Using OpenID", test_openid)
    except Exception as e:
        pretty_print("OpenID Error", "No valid OpenID found")
        return

    message_result = wechat_toolkit.send_customer_message(
        openid=test_openid,
        content="Hello from CAMEL toolkit",
        msgtype="text"
    )
    pretty_print("Message Result", message_result)

    user_info = wechat_toolkit.get_user_info(openid=test_openid)
    pretty_print("User Info", user_info)

    image_path = "/home/lyz/Camel/CAMEL_logo.jpg"
    if os.path.exists(image_path):
        upload_result = wechat_toolkit.upload_permanent_media("image", image_path)
        pretty_print("Upload Result", upload_result)

    media_list = wechat_toolkit.get_media_list("image", 0, 5)
    pretty_print("Media List", media_list)

    tools = wechat_toolkit.get_tools()
    tool_names = [tool.func.__name__ for tool in tools]
    pretty_print("Available Tools", tool_names)

if __name__ == "__main__":
    main()

"""
--- Followers ---
{
  "total": 5,
  "count": 5,
  "data": {
    "openid": [
      "oKSAF2***azaQ",
      "oKSAF2***4698Q",
      "oKSAF2***BoPGM",
      "oKSAF2***EJI",
      "oKSAF2***ka4"
    ]
  },
  "next_openid": "oKSAF2***ka4"
}

--- Using OpenID ---
oKSAF2***EJI

--- Message Result ---
Message sent successfully to oKSAF2***EJI.

--- User Info ---
{
  "subscribe": 1,
  "openid": "oKSAF2***EJI",
  "nickname": "",
  "sex": 0,
  "language": "zh_CN",
  "city": "",
  "province": "",
  "country": "",
  "headimgurl": "",
  "subscribe_time": 1756536553,
  "remark": "",
  "groupid": 0,
  "tagid_list": [],
  "subscribe_scene": "ADD_SCENE_QR_CODE",
  "qr_scene": 0,
  "qr_scene_str": ""
}

--- Upload Result ---
{'media_id': 'Rd1LjwkraUucr8ffsfhZwz1CUklB9osYdM3iuAlawnC8kizsDQSjlETPrA7d2-SA', 'url': 'http://mmbiz.qpic.cn/sz_mmbiz_jpg/57M3u1KGvsib2HzKAdpKX7kiaPau4GHlR85LQ4KKjMuUd73YUTglMjFDmdfLohKzjaYibRSCtpxO5J3S8gqeWyCcA/0?wx_fmt=jpeg', 'item': []}

--- Media List ---
{'item': [{'media_id': 'Rd1LjwkraUucr8ffsfhZwz1CUklB9osYdM3iuAlawnC8kizsDQSjlETPrA7d2-SA', 'name': 'CAMEL_logo.jpg', 'update_time': 1756540111, 'url': 'https://mmbiz.qpic.cn/sz_mmbiz_jpg/57M3u1KGvsib2HzKAdpKX7kiaPau4GHlR85LQ4KKjMuUd73YUTglMjFDmdfLohKzjaYibRSCtpxO5J3S8gqeWyCcA/0?wx_fmt=jpeg', 'tags': []}, {'media_id': 'Rd1LjwkraUucr8ffsfhZw1tGqqtUxc26eqDsW-G5u2p0yFRjNR5Mc8Wb2rdQKlyt', 'name': 'CAMEL_logo.jpg', 'update_time': 1756539999, 'url': 'https://mmbiz.qpic.cn/sz_mmbiz_jpg/57M3u1KGvsib2HzKAdpKX7kiaPau4GHlR85LQ4KKjMuUd73YUTglMjFDmdfLohKzjaYibRSCtpxO5J3S8gqeWyCcA/0?wx_fmt=jpeg', 'tags': []}], 'total_count': 2, 'item_count': 2}

--- Available Tools ---
[
  "send_customer_message",
  "get_user_info",
  "get_followers_list",
  "upload_temporary_media",
  "upload_permanent_media",
  "get_media_list"
]

"""