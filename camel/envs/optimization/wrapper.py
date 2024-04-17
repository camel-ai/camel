from llfbench.envs.env_wrappers import TerminalFreeWrapper, EnvCompatibility
from llfbench.envs.llf_env import LLFWrapper, Feedback
# from llfbench.envs.loss_landscape.loss_descent import
from llfbench.envs.optimization.prompts import *

"""
The original env produces support for both
- Directional feedback: 0,0.5,1
- Didactic feedback: 'r', 'hp', 'hn', 'fp', 'fn'

This wrapper will only produce didactic feedback
"""


class LossLandscapeGymWrapper(LLFWrapper):
    INSTRUCTION_TYPES = ('b')
    FEEDBACK_TYPES = ('r', 'hp', 'hn', 'fp', 'fn')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(TerminalFreeWrapper(EnvCompatibility(env)), instruction_type, feedback_type)

    def _reset(self, *, seed=None, options=None):  # TODO types of instructions
        instruction = self._loss_env.docstring
        obs, info = self.env.reset(seed=seed, options=options)
        info['success'] = False

        instruction = self.reformat(instruction, loss_b_instruction)
        return dict(instruction=instruction, observation=obs, feedback=None), info

    def _step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        didactic_feedback = info['feedback']
        del info['feedback']
        del info['original_feedback']

        assert 'success' in info

        paraphrased_feedback = Feedback()

        for feedback_type in self._feedback_type:
            if feedback_type == 'r':
                feedback = self.reformat(didactic_feedback[feedback_type], r_feedback_pos, template=r_feedback_pos_template)
                feedback = self.reformat(feedback, r_feedback_neg, template=r_feedback_neg_template)
                paraphrased_feedback.r = feedback
            elif feedback_type in didactic_feedback and didactic_feedback[feedback_type] != "":
                temp_dim1 = eval("{}_feedback_dim1_template".format(feedback_type))
                feedback = self.reformat(didactic_feedback[feedback_type],
                                         eval("{}_feedback_dim1".format(feedback_type)),
                                         template=temp_dim1)
                temp_dim2 = eval("{}_feedback_dim2_template".format(feedback_type))
                feedback = self.reformat(feedback,
                                         eval("{}_feedback_dim2".format(feedback_type)),
                                         template=temp_dim2)

                # this is to fix a capitalization issue in paraphrasing
                if '. Increasing' not in feedback:
                    feedback = feedback.replace("Increasing", 'increasing')
                elif '. Decreasing' not in feedback:
                    feedback = feedback.replace("Decreasing", 'decreasing')

                paraphrased_feedback[feedback_type] = feedback

        observation = dict(instruction=None, observation=observation, feedback=paraphrased_feedback)
        return observation, reward, terminated, truncated, info

    @property
    def _loss_env(self):
        return self.env.env.env

    @property
    def reward_range(self):
        return self._loss_env.reward_range