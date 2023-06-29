# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import List

from camel.agents import FuncAgent
from camel.generators import SystemMessageGenerator
from camel.messages import UserChatMessage
from camel.typing import ModelType, RoleType


def add(a, b):
    """
    Adds Two Numbers

    Args
    ----------
    a : integer
        number to be added
    b : integer
        number to be added

    Returns
    -------
    integer
        sum
    """
    return a + b

def sub(a, b):
    """
    Subs Two Numbers

    Args
    ----------
    a : integer
        number to be subbed
    b : integer
        number to be subbed

    Returns
    -------
    int
        sub
    """
    return a - b

def mul(a, b):
    """
    Muls Two Numbers

    Args
    ----------
    a : integer
        number to be muled
    b : integer
        number to be muled

    Returns
    -------
    int
        mul
    """
    return a * b

def main():
    # Create an embodied agent
    role_name = "Student"
    
    functions = [add, sub, mul]

    func_agent = FuncAgent(
        role_name, 
        functions,
        verbose=True,
    )

    user_msg = UserChatMessage(
        role_name=role_name,
        content=("Caculate the result of: 2 * 2 + 4"),
    )
    output_message, func_call, info = func_agent.step(user_msg)

    executed = "true" if func_call else "false"
    print(f"Function is executed or not? {executed}")
    print(f"Final output:\n {output_message[0].content}")

if __name__ == "__main__":
    main()
