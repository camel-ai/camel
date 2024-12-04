import json
import os
import random
from typing import Optional, List


from .templates import SelfInstructTemplates

from camel.agents import ChatAgent
from camel.synthetic_datagen.self_instruct.filter.instruction_filter import InstructionFilter


class SelfInstructPipeline:
    """
    A pipeline to generate and manage machine-generated instructions for tasks,
    combining human and machine task samples.

    Attributes:
        agent (ChatAgent): The agent used to interact and generate instructions.
        num_machine_instructions (int): Number of machine-generated instructions to generate.
        data_output_path (Optional[str]): Path to save the generated data.
        human_to_machine_ratio (tuple): Ratio of human to machine tasks used for instruction generation.
        filter (InstructionFilter): A filter to validate generated instructions.
        human_tasks (List[dict]): A list of tasks loaded from the seed file.
        machine_tasks (List[dict]): A list of machine-generated tasks.
    """
    def __init__(
            self,
            agent: ChatAgent,
            seed: Optional[str] = None,
            num_machine_instructions: int = 5,
            data_output_path: Optional[str] = '/data_output.json',
            human_to_machine_ratio: tuple = (6, 2),
            filter: Optional[InstructionFilter] = InstructionFilter(),
    ):
        self.agent = agent
        self.num_machine_instructions = num_machine_instructions
        self.data_output_path = data_output_path
        self.human_to_machine_ratio = human_to_machine_ratio
        self.filter = filter
        self.human_tasks = []
        self.machine_tasks = []  # stores tasks in the same format as the seed
        self.load_seed(seed)

    def load_seed(self, path: Optional[str]):
        """
        Load seed tasks from a file. Defaults to a predefined seed file if no path is provided.

        Args:
            path (Optional[str]): Path to the seed file.

        Raises:
            FileNotFoundError: If the seed file does not exist.
        """
        if path is None:
            path = '/seed/default_seed.json'

        if os.path.exists(path):
            with open(path, 'r') as f:
                self.human_tasks = json.load(f)
        else:
            raise FileNotFoundError(f"Seed file not found at path: {path}")

    def sample_human_tasks(self, count: int) -> List[dict]:
        """
        Sample a specified number of human tasks from the loaded seed.

        Args:
            count (int): Number of human tasks to sample.

        Returns:
            List[dict]: A list of sampled human tasks.
        """
        return random.sample(self.human_tasks, min(count, len(self.human_tasks)))

    def sample_machine_tasks(self, count: int) -> List[dict]:
        """
        Sample a specified number of machine tasks.

        Args:
            count (int): Number of machine tasks to sample.

        Returns:
            List[dict]: A list of sampled machine tasks, with placeholders if insufficient tasks are available.
        """
        available_machine_tasks = len(self.machine_tasks)
        if available_machine_tasks < count:
            sampled_tasks = self.machine_tasks.copy()
            placeholders_needed = count - available_machine_tasks
            sampled_tasks.extend(
                [{'instruction': ""} for _ in range(placeholders_needed)])
            return sampled_tasks

        return random.sample(self.machine_tasks, count)

    def generate_machine_instruction(self) -> str:
        """
        Generate a machine instruction using the agent.

        Combines human and machine tasks based on the configured ratio to create a prompt
        for instruction generation.

        Returns:
            str: A machine-generated instruction.
        """

        sampled_human_tasks = self.sample_human_tasks(self.human_to_machine_ratio[0])
        sampled_machine_tasks = self.sample_machine_tasks(self.human_to_machine_ratio[1])
        prompt = "Come up with a series of tasks:\n"

        for idx, task in enumerate(sampled_human_tasks, 1):
            prompt += f"Task {idx}: {task['instruction']}\n"

        current_task_number = len(sampled_human_tasks) + 1
        for idx, task in enumerate(sampled_machine_tasks, current_task_number):
            prompt += f"Task {idx}: {task['instruction']}\n"

        prompt += f"Task {len(sampled_human_tasks) + len(sampled_machine_tasks) + 1}:"


        response = self.agent.step(prompt)
        generated_tasks = response.msgs[0].content.split("\n")
        return generated_tasks[0]

    def identify_instruction(self, instruction: str) -> bool:
        """
        Determine if the given instruction is a classification task.

        Args:
            instruction (str): The instruction to classify.

        Returns:
            bool: True if the instruction is a classification task, otherwise False.
        """
        clf_prompt = SelfInstructTemplates.clf_template + f"Task: {instruction}\nIs it classification?"
        response = self.agent.step(clf_prompt)
        result = response.msgs[0].content.strip().lower()
        return result in ["yes", "true"]

    def generate_machine_instances(self):
        """
        Generate instances for each machine task based on its classification status.
        """
        for instruction in self.machine_tasks:
            instance = self.generate_machine_instance(
                instruction['instruction'],
                instruction['is_classification']
            )
            instruction['instances'] = instance
    def generate_machine_instance(
            self,
            instruction: str,
            classification: bool
    ) -> list[dict]:
        """
        Generate instances for a given instruction.

        Args:
            instruction (str): The instruction to create instances for.
            classification (bool): Whether the instruction is a classification task.

        Returns:
            List[dict]: A list of generated instances in input-output format.
        """
        if classification:
            prompt = SelfInstructTemplates.input_first_template_for_gen.format(instruction=instruction)
        else:
            prompt = SelfInstructTemplates.output_first_template_for_clf.format(instruction=instruction)

        response = self.agent.step(prompt)
        generated_text = response.msgs[0].content.strip()

        instances = []

        for line in generated_text.split("\n\n"):
            if line.strip():
                try:
                    input_text = ""
                    output_text = line.strip()

                    instance = {
                        "input": input_text,
                        "output": output_text
                    }
                    instances.append(instance)
                except Exception as e:
                    print(f"Error parsing instance: {e}")

        return instances


    def construct_data(self):
        """
        Save the machine-generated tasks to the specified output path in JSON format.
        """
        with open(self.data_output_path, 'w') as f:
            json.dump(self.machine_tasks, f, indent=4)

    def generate(self):
        """
        Execute the entire pipeline to generate machine instructions and instances.
        """
        while len(self.machine_tasks) < self.num_machine_instructions:
            instruction = self.generate_machine_instruction()
            if self.filter.filter(instruction):
                instruction_dict = {
                    "id" : f"machine_task_{len(self.machine_tasks) + 1}",
                    "instruction": instruction
                }
                self.machine_tasks.append(instruction_dict)
        self.generate_machine_instances()
        self.construct_data()





