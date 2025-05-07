#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script demonstrating the use of CodeAgent in Camel.
"""
import sys
sys.path.insert(0, '/Users/suntao/Documents/GitHub/camel2')

import argparse
import os

from camel.agents import CodeAgent
from camel.toolkits import FunctionTool
from camel.models import ModelFactory
from camel.types import ModelPlatformType

def add(a: float, b: float) -> float:
    r"""Adds two numbers.

    Args:
        a (float): The first number to be added.
        b (float): The second number to be added.

    Returns:
        float: The sum of the two numbers.
    """
    raise Exception("故意设置错误,来模仿工具调用失败")


def multiply(a: float, b: float, decimal_places: int = 2) -> float:
    r"""Multiplies two numbers.

    Args:
        a (float): The multiplier in the multiplication.
        b (float): The multiplicand in the multiplication.
        decimal_places (int, optional): The number of decimal
            places to round to. Defaults to 2.

    Returns:
        float: The product of the two numbers.
    """
    return round(a * b, decimal_places)

tool_list = [FunctionTool(add), FunctionTool(multiply)]
    
model = ModelFactory.create(
model_platform=ModelPlatformType.OPENAI,
model_type="gpt-4o",
api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize the agent
agent = CodeAgent(
    model=model,
    tools=tool_list,
)

# Run a conversation with the agent
math_task = "19987 + 2133 之后再平方是多少？"

response = agent.step(math_task)

print(response)


