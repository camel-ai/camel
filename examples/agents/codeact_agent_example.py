#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script demonstrating the use of CodeActAgent in Camel.
"""
import sys
sys.path.insert(0, '/Users/suntao/Documents/GitHub/camel2')

import os

from camel.agents import CodeActAgent
from camel.toolkits import FunctionTool,MathToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType,ModelType

tool_list = [*MathToolkit().get_tools()]
    
model = ModelFactory.create(
model_platform=ModelPlatformType.OPENAI,
model_type=ModelType.GPT_4_1,
api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize the agent
agent = CodeActAgent(
    model=model,
    tools=tool_list,
)

# Run a conversation with the agent
math_task = "2133分别对1、2、3、4、5、6、7、8求积各是多少？"

response = agent.step(math_task)

print(response)


