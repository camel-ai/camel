from textwrap import dedent, indent
import sys

from llfbench.agents.abstract_agent import Agent
from llfbench.agents.utils import extract_action, ReplayBuffer, print_color

def get_multiline_input(prompt="Enter text (press Enter twice to finish):\n"):
    lines = []
    while True:
        line = input(prompt)
        if not line:
            break  # Break the loop if the user enters an empty line
        lines.append(line)
    return '\n'.join(lines)

class UserAgent(Agent):

    NAME = "UserAgent"

    def __init__(self,
                 verbose=False,
                 buffer_size=1000,
                 ignore_observation=False,
                 prompt_template=None):
        """
            Args:
                verbose: whether to print out the prompt and response
                buffer_size: the size of the replay buffer
                ignore_observation: whether to ignore the observation (for bandit setting)
                prompt_template: A prompt template with two parameters if ignore_observation is True and 3 otherwise
        """
        super().__init__()
        self.verbose = verbose
        self.buffer = ReplayBuffer(buffer_size)
        self.ignore_observation = ignore_observation
        if prompt_template is not None:
            self.prompt_template = prompt_template
        else:
            if ignore_observation:
                self.prompt_template = dedent("""\
                    You're presented with the problem below:

                    Problem Description: {}

                    You have observed the following history of feedbacks:

                    {}

                    Choose your action according to the problem description and history of feedbacks.
                """)
            else:
                self.prompt_template = dedent("""
                    You're presented with the problem below:

                    Problem Description: {}

                    You have in the past taken the following path which consists of observations you saw, the actions
                    you took, and the feedback you got for those actions:

                    {}

                    You are currently observing the following {}.

                    Choose your action according to the problem description, your past history of actions, and your
                    current observation.
                """)

            self.prompt_template += dedent(f"""\
                The response should be in the following format, where <your action> is the final answer. You must follow this format!

                    Action: <your action>

                """)

    def reset(self, docstring):
        self.docstring = docstring
        self.buffer.reset()

    @property
    def world_info(self):

        if self.ignore_observation:

            if len(self.buffer) == 0:
                world_info = 'None'
            else:
                world_info = '\n'.join(
                    [indent(f'{self.action_name}: {item["action"]}\n\nFeedback: {item["feedback"]}\n\n\n','\t')
                     for item in self.buffer])
        else:
            # We present the observation and feedback as
            # you took action <action>
            # this resulted in <observation>
            # and you got a feedback of <feedback>

            if len(self.buffer) == 0:
                world_info = 'None'
            else:
                world_info = "\n".join([
                    f"Observation: {dp['observation']}\nAction: {dp['action']}\nFeedback: {dp['feedback']}\n"
                    for dp in self.buffer])

        return world_info

    def act(self, observation, feedback, **kwargs):

        # update with the latest feedback (ignored in the first call)
        self.buffer.update(feedback=feedback, next_observation=observation)
        world_info = self.world_info

        # create prompt
        if self.ignore_observation:
            user_prompt = self.prompt_template.format(self.docstring, world_info)
        else:
            user_prompt = self.prompt_template.format(self.docstring, world_info, observation)

        print(user_prompt)
        response = get_multiline_input()
        #response = input(user_prompt)

        action = response.split('Action:')[-1]

        if self.verbose:
            print_color(f'User:\n\n{user_prompt}\n', "blue")
            print_color(f'Agent:\n\n{response}\n', "green")
            print_color(f'Action:\n\n{action}\n', 'red')

        # update buffer and get world info
        self.buffer.append(observation=observation,
                           action=action,
                           feedback=None,
                           next_observation=None)
        return action
