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
Simple client example for CAMEL OpenAI-compatible server.

Start the server first:
    python example_openai_server.py

Then run this client:
    python simple_client_example.py
"""

import openai

# Configure client to use CAMEL server
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy-key",  # Any string works
)


def main():
    print("🚀 Testing CAMEL OpenAI-compatible server...")

    # Basic chat
    print("\n1. Basic Chat:")
    response = client.chat.completions.create(
        model="camel-model",
        messages=[{"role": "user", "content": "Hello! Tell me a fun fact."}],
    )
    print(f"Response: {response.choices[0].message.content}")

    # With system message
    print("\n2. With System Message:")
    response = client.chat.completions.create(
        model="camel-model",
        messages=[
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "Explain what is 2+2 in a fun way."},
        ],
    )
    print(f"Response: {response.choices[0].message.content}")

    # Streaming
    print("\n3. Streaming Response:")
    response = client.chat.completions.create(
        model="camel-model",
        messages=[{"role": "user", "content": "Count from 1 to 5 slowly."}],
        stream=True,
    )

    print("Streaming: ", end="")
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()

"""
🚀 Testing CAMEL OpenAI-compatible server...

1. Basic Chat:
Response: Sure! Did you know that honey never spoils? Archaeologists have 
found pots of honey in ancient Egyptian tombs that are over 3,000 years old 
and still perfectly edible! Honey's long shelf life is due to its low moisture 
content and acidic pH, which create an inhospitable environment for bacteria 
and microorganisms.

2. With System Message:
Response: Sure! Imagine you have two playful puppies. One is wagging its tail 
on the left, and the other is bouncing around on the right. Now, if you add 
one more puppy who jumps in to join the fun, you'll have a total of three 
puppies! But wait, let's bring in one more adorable puppy who can't resist the 
excitement. 

So now, how many puppies do you have? You started with two, then you added one 
more (three), and added another one—ta-da! That gives you 2 + 2 = 4 happy 
puppies bouncing around! 

That's how math works—like a puppy party, where you just keep adding more joy! 
🐶🎉

3. Streaming Response:
Streaming: Sure! Here we go:

1...  
2...  
3...  
4...  
5...  

Nice and slow! That's counting from 1 to 5! 

✅ All tests completed!
"""
