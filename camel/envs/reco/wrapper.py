from llfbench.envs.env_wrappers import TerminalFreeWrapper, EnvCompatibility
from llfbench.envs.llf_env import LLFWrapper, Feedback
from llfbench.envs.reco.prompts import *
from llfbench.envs.reco.movie_rec import MovieRec

class MovieRecGymWrapper(LLFWrapper):
    INSTRUCTION_TYPES = ('b', 'c')  # , 'p', 'c')
    FEEDBACK_TYPES = ('r', 'hp', 'hn', 'fp', 'fn')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(TerminalFreeWrapper(EnvCompatibility(env)), instruction_type, feedback_type)

    def _reset(self, *, seed=None, options=None):
        instruction = self._movie_rec_env.docstring
        obs, info = self.env.reset(seed=seed, options=options)
        info['success'] = False
        instruction = self.reformat(instruction, movie_instruction, template=movie_instruction_template)

        # For movie rec
        # obs is different/randomly sampled from a pool already
        # since a user can make multiple queries

        return dict(instruction=instruction, observation=obs, feedback=None), info

    def _step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        didactic_feedback = info['feedback']
        del info['original_feedback']
        del info['feedback']

        attribute_list = ["hallucination", "type", "genre", "year", "child_friendly"]

        paraphrased_feedback = Feedback(r="", hp="", hn="", fp="", fn="")

        for attribute in attribute_list:
            if attribute not in didactic_feedback:
                continue

            for feedback_type in self._feedback_type:
                if didactic_feedback[attribute][feedback_type] is None:
                    continue

                if feedback_type == 'r':
                    r_pos_temp = eval(f"{attribute}_r_pos_template")
                    r_pos = eval(f"{attribute}_r_pos")
                    feedback = self.reformat(didactic_feedback[attribute][feedback_type], r_pos, template=r_pos_temp)

                    r_neg_temp = eval(f"{attribute}_r_neg_template")
                    r_neg = eval(f"{attribute}_r_neg")
                    feedback = self.reformat(feedback, r_neg, template=r_neg_temp)

                    paraphrased_feedback.r += feedback + '\n'

                else:
                    # if LLM suggestion is correct on the attribute, some feedback might not show up
                    # like, r is filled, but not hn
                    feedback_temp = eval(f"{attribute}_{feedback_type}_template")
                    feedback_prompts = eval(f"{attribute}_{feedback_type}")
                    feedback = self.reformat(didactic_feedback[attribute][feedback_type], feedback_prompts, template=feedback_temp)

                    paraphrased_feedback[feedback_type] += feedback + '\n'

        if 'no_rec' in didactic_feedback:
            feedback = self.reformat(didactic_feedback['no_rec'].r,
                                                no_rec_r_neg, template=no_rec_r_neg_template)
            paraphrased_feedback.r += feedback + '\n'

        # manually set things to None for consistency
        for ftype in ['r', 'hp', 'hn', 'fp', 'fn']:
            if paraphrased_feedback[ftype] == '':
                paraphrased_feedback[ftype] = None

        observation = dict(instruction=None, observation=observation, feedback=paraphrased_feedback)
        return observation, reward, terminated, truncated, info

    @property
    def _movie_rec_env(self):
        return self.env.env.env

    @property
    def reward_range(self):
        return self._movie_rec_env.reward_range