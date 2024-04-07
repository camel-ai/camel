from typing import SupportsFloat
from llfbench.envs.env_wrappers import TerminalFreeWrapper, EnvCompatibility
from llfbench.envs.llf_env import LLFWrapper, Feedback
from llfbench.envs.poem.formal_poems import Haiku, Tanka, LineSyllableConstrainedPoem, SyllableConstrainedPoem
from llfbench.envs.poem.prompts import *

class PoemGymWrapper(LLFWrapper):

    INSTRUCTION_TYPES = ('b')
    FEEDBACK_TYPES = ('r', 'hp', 'hn', 'fp', 'fn')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(TerminalFreeWrapper(EnvCompatibility(env)), instruction_type, feedback_type)

    @property
    def reward_range(self):
        return (0.0, 1.0)

    def _reset(self, *, seed=None, options=None):  # TODO types of instructions
        instruction, info = self.env.reset(seed=seed, options=options)
        info['success'] = False
        if type(self._poem_env) == Haiku:
            instruction = self.reformat(instruction, haiku_b_instruction)
        elif type(self._poem_env) == Tanka:
            instruction = self.reformat(instruction, tanka_b_instruction)
        elif type(self._poem_env) == LineSyllableConstrainedPoem:
            instruction = self.reformat(instruction, line_syllable_constrained_poem_b_instruction)
        elif type(self._poem_env) == SyllableConstrainedPoem:
            instruction = self.reformat(instruction, syllable_constrained_poem_b_instruction)
        return dict(instruction=instruction, observation=None, feedback=None), info

    def _step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        didactic_feedback = info['feedback']
        del info['feedback']
        del info['original_feedback']

        paraphrased_feedback = Feedback()
        for feedback_type in self._feedback_type:
            feedback = didactic_feedback[feedback_type]
            if feedback_type == 'r':
                feedback = self.reformat(feedback, r_feedback_pos)
                feedback = self.reformat(feedback, r_feedback_neg)
            elif feedback_type == 'hn':
                feedback = self.reformat(feedback, line_number_hn_feedback)
                feedback = self.reformat(feedback, syllable_hn_feedback)
            elif feedback_type == 'hp':
                feedback = self.reformat(feedback, syllable_hp_feedback)
            elif feedback_type == 'fp':
                feedback = self.reformat(feedback, line_number_fp_feedback)
                feedback = self.reformat(feedback, syllable_fp_feedback_1)
                feedback = self.reformat(feedback, syllable_fp_feedback_2)
            elif feedback_type == 'fn':
                feedback = self.reformat(feedback, line_number_fn_feedback)
            else:
                raise ValueError(f'Unknown feedback type: {feedback_type}')
            paraphrased_feedback[feedback_type] = feedback

        observation = dict(instruction=None, observation=None, feedback=paraphrased_feedback)

        return observation, reward, terminated, truncated, info

    def fix_sentence_capitalization(self, sentence):
        sentences = sentence.split(". ")
        fixed_sentences = [s[0].capitalize() + s[1:] if s else '' for s in sentences]
        fixed_sentence = ". ".join(fixed_sentences)
        return fixed_sentence

    def _verbalize_feedback(self, feedback_dict: Feedback) -> str:
        """ Implement this in the subclass to get the desired feedback string.
        """

        feedback = []
        for k, v in feedback_dict.asdict().items():
            if v is not None:
                line = self.fix_sentence_capitalization(f'{str(v)}')
                feedback.append(line)
        return ' '.join(feedback)

    @property
    def _poem_env(self):
        return self.env.env.env