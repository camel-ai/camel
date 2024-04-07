from typing import SupportsFloat
import gym as old_gym
import numpy as np
from llfbench.envs.env_wrappers import TerminalFreeWrapper, RandomActionOrderWrapper, EnvCompatibility
from llfbench.envs.llf_env import LLFWrapper, Feedback
from llfbench.envs.bandits.prompts import *


class BanditGymWrapper(LLFWrapper):

    """ This is a wrapper for gym_bandits. """

    INSTRUCTION_TYPES = ('b', 'p', 'c')
    FEEDBACK_TYPES = ('r', 'hp', 'hn', 'fp', 'fn')

    def __init__(self, env, instruction_type, feedback_type):
        env = TerminalFreeWrapper(RandomActionOrderWrapper(EnvCompatibility(env)))
        super().__init__(env, instruction_type, feedback_type)

    @property
    def reward_range(self):
        return (-100, 100)

    def _reset(self, seed=None, options=None):
        options = options or {}
        self._bandit_env.__init__(**options)  # gym_bandits implement the reset at the init for some reason.
        self.seed(seed)
        self.env.reset()  # bandit env has no observation
        docstring =  self._bandit_env.__doc__
        n_actions = self.env.action_space.n
        instruction = docstring +'\n' + self.format(b_instruction, low=0, high=n_actions-1)
        if self.instruction_type=='p':  # Give info of a bad action.
            bad_action = np.random.choice(np.delete(np.arange(self.env.action_space.n), self._best_arm))
            instruction += '\n'+self.format(p_instruction, bad_action=bad_action, reward=self._expected_reward(bad_action))
        if self.instruction_type=='c':
            instruction += '\n'+self.format(c_instruction, best_arm=self._best_arm)
        return dict(instruction=instruction, observation=None, feedback=None), {'success':False}

    def _step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        feedback = Feedback()
        feedback_type = self._feedback_type

        if 'r' in feedback_type:  # reward feedback
            feedback.r = self.format(r_feedback, reward=reward)  # base reward feedback
        if 'hp' in feedback_type:  # hindsight positive: explaination on why something is correct
            if action == self._best_arm:
                feedback.hp = self.format(hp_feedback)
        if 'hn' in feedback_type:  # hindsight negative: explaination on why something is incorrect
            if action != self._best_arm:
                feedback.hn = self.format(hn_feedback)
        assert feedback.hn is None or feedback.hp is None, 'Cannot have both hp and hn feedback'
        if 'fp' in feedback_type:  # future positive: suggestion of things to do
            feedback.fp = self.format(fp_feedback, best_arm=self._best_arm, reward=self._expected_reward(self._best_arm))
        if 'fn' in feedback_type:  # future negative: suggestion of things to avoid
            bad_action = np.random.choice(np.delete(np.arange(self.env.action_space.n), self._best_arm))
            feedback.fn = self.format(fn_feedback, bad_action=bad_action, reward=self._expected_reward(bad_action))
        observation = dict(instruction=None, observation=None, feedback=feedback)

        info['success'] = action==self._best_arm

        return observation, float(reward), terminated, truncated, info

    @property
    def _bandit_env(self): # This is hardcoded for gym_bandits
        env = self.env
        while True:
            if hasattr(env, 'env'):
                env = env.env
            else:
                assert isinstance(env, old_gym.Env)
                break
        return env # this is the raw env

    def seed(self, seed=None):  # This to fix the seeding issue for gym_bandits
        self._bandit_env._seed(seed)

    @property
    def __reward_fun(self):
        # NOTE: This is based on the internal action space before
        # RandomActionOrderWrapper. Use it with caution.
        if not isinstance(self.r_dist[0], list):
            r_dist = self.env.r_dist
        else:
            r_dist = np.array([mean for mean, scale in self.env.r_dist])
        return np.array(self.env.p_dist) * np.array(r_dist)

    def _expected_reward(self, idx):  # external action space
        idx = self.internal_action(idx)
        return self.__reward_fun[idx]

    @property
    def _best_arm(self):  # external action space
        idx = self.__reward_fun.argmax()
        return self.external_action(idx)
