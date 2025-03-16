import json
from camel.agents import ChatAgent
from camel.models import BaseModelBackend
from typing import List, Dict, Union
from verifier import PhysicsVerifier, logger
from models import ResponseFormat, AnswerFormat

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  

REASON_AGENT_PROMPT = """
You are an expert in physics and symbolic computation using Python's Sympy library. When given a physics problem, follow these instructions:

1. **Understanding the Problem**: Carefully read and interpret the problem statement. Identify the underlying physics concepts and relevant equations.

2. **Reasoning and Explanation**: 
   - Provide a detailed, step-by-step explanation of your thought process.
   - Explain the physical principles, assumptions, and logical steps used to approach the problem.
   - Keep the explanation clear and thorough so that a human reviewer can follow the reasoning without referring to the code.

3. **Sympy Code Implementation**:
   - Write the Python code that uses the Sympy library to solve the problem.
   - Ensure that the code is well-commented to clarify each step.
   - The code should be fully self-contained and verifiable independently of the reasoning section.
   - **Be extremely careful with units: verify that any unit conversions or unit-related calculations are correct, and include units with any numerical output.**
   - **Ensure that the final computed result is stored in a variable named `result` (i.e., `result = <final_value>`).**
"""


class PhysicsCodeGenPipeline():
   """
   A pipeline for generating physics solutions using symbolic computation with Python's Sympy library.
   """
   def __init__(self, reason_model: BaseModelBackend, dataset: List[Dict], output_location: str, num: Union[int, None] = None):
      """
      Initialize the pipeline with the reason model and the dataset.

      Args:
          reason_model (BaseModelBackend): The model used for reasoning and code generation.
          dataset (dict): The dataset containing physics problems and solutions.
      """
      # Set limit
      if num is not None:
         self.dataset = dataset[:num]
      else:
         self.dataset = dataset

      # Initialize the reasoning agent
      self.reason_agent = ChatAgent(
         model=reason_model,
         system_message=REASON_AGENT_PROMPT
      )
      
      self.verifier = PhysicsVerifier()
      self.output_location = output_location
      self.generation_summary = {
         'total_samples': len(self.dataset),
         'successful_generations': 0,
         'failed_generations': 0
      }
      
   def verify(self, response: ResponseFormat, gt_answer: str):
      """
      A method to verify the correctness of the generated code using PythonVerifier.

      Args:
          response (ResponseFormat): The response format containing the reasoning and code sections.
          gt_answer (str): The ground truth answer to compare against.
      """
      output_match, unit_match = self.verifier.verify(response, gt_answer)
      return output_match, unit_match
      

   def run(self):
      """
      Run the pipeline on the dataset.
      """
      for sample in self.dataset:
         sample_id = sample['id']
         question = sample['question']
         gt_answer = sample['gt_answer']
         unit = sample['unit']
         full_answer = AnswerFormat(gt_answer=gt_answer, unit=unit) # Create the full answer format including both the numerical answer and unit

         llm_response = self.reason_agent.step(question, response_format=ResponseFormat)
         structured_response = llm_response.msgs[0].parsed

         logger.info(f'=====Verifying Question {sample_id}=====')
         verification_outcome = self.verify(structured_response, full_answer)
         if verification_outcome[0] and verification_outcome[1]:
            self.generation_summary['successful_generations'] += 1
         else:
            self.generation_summary['failed_generations'] += 1

         with open(self.output_location, 'a') as f:
            entry = {
               'sample_id': sample_id,
               'question': question,
               'response': structured_response.model_dump(),
               'gt_answer': gt_answer,
               'unit': unit,
               'metadata': sample['metadata'],
               'verification_outcome': {'output_match': verification_outcome[0], 'unit_match': verification_outcome[1]}
            }
            f.write(json.dumps(entry, indent=4) + '\n')
      
      logger.info(f"Generation Summary: {self.generation_summary}")