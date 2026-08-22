# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PlivoToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Requires PLIVO_AUTH_ID and PLIVO_AUTH_TOKEN in the environment.
    # Replace the numbers below with your Plivo sender and a destination.
    sender = "+14150000001"
    receiver = "+14150000002"

    plivo_toolkit = PlivoToolkit()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a communications assistant. Use the "
        "PlivoToolkit to send SMS, place voice calls, send and check OTP "
        "verification codes, and look up phone numbers.",
        model=model,
        tools=plivo_toolkit.get_tools(),
    )

    # Example 1: Send an SMS
    response = agent.step(
        f"Send an SMS from {sender} to {receiver} saying "
        "'Your CAMEL AI demo is live.'"
    )
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='send_sms', args={'from_number':
    '+14150000001', 'to_number': '+14150000002', 'message': 'Your CAMEL AI
    demo is live.'}, result={'message': 'message(s) queued', 'message_uuid':
    ['2b6a4787-f164-4f64-b76f-9c7abc15e2d2'], 'api_id':
    '34054724-2e46-4a55-b2c5-b94da622e533'}, tool_call_id='call_JiaCT0Xj')]
    ===============================================================================
    '''

    # Example 2: Look up a phone number
    response = agent.step(f"Look up the carrier and line type for {receiver}.")
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='lookup_number', args={'number':
    '+14150000002'}, result={'phone_number': '+14150000002', 'country':
    {'name': 'United States', 'iso2': 'US', 'iso3': 'USA'}, 'carrier':
    {'name': 'Verizon Wireless', 'type': 'mobile', 'ported': 'false'}},
    tool_call_id='call_vejYALdp')]
    ===============================================================================
    '''

    # Example 3: Send a verification OTP, then check the code
    response = agent.step(f"Send a verification OTP to {receiver}.")
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='send_otp', args={'recipient':
    '+14150000002', 'channel': 'sms'}, result={'session_uuid':
    '4f2d9b70-8c1a-4d33-9f6e-2a7c1b0e5d84', 'api_request_id':
    '1c9e33aa-2f45-4b1d-8a0c-77e2f9d61b52'}, tool_call_id='call_Kp2mVr8Q')]
    ===============================================================================
    '''
    response = agent.step(
        "Verify the code 123456 for that verification session."
    )
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='verify_otp', args={'session_uuid':
    '4f2d9b70-8c1a-4d33-9f6e-2a7c1b0e5d84', 'otp': '123456'}, result=
    {'verified': True, 'message': 'session validated successfully'},
    tool_call_id='call_Zx4nLb1T')]
    ===============================================================================
    '''

    # Example 4: Place a voice call
    response = agent.step(
        f"Place a call from {sender} to {receiver} using the answer URL "
        "https://s3.amazonaws.com/static.plivo.com/answer.xml with "
        "answer_method GET."
    )
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='make_call', args={'from_number':
    '+14150000001', 'to_number': '+14150000002', 'answer_url':
    'https://s3.amazonaws.com/static.plivo.com/answer.xml', 'answer_method':
    'GET'}, result={'message': 'call queued', 'request_uuid':
    '0a423c29-94ec-42d6-81bb-e8a0d08e0885', 'api_id':
    'ad34ba9f-24c8-4053-9575-9f8db4618fcd'}, tool_call_id='call_Qee6bOLP')]
    ===============================================================================
    '''


if __name__ == "__main__":
    main()
