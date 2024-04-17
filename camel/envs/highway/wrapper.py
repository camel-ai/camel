import numpy as np
import json
from llfbench.envs.llf_env import LLFWrapper, Feedback
from llfbench.envs.highway.prompts import *


class HighwayWrapper(LLFWrapper):

    """ This is a wrapper for highway-env. """

    INSTRUCTION_TYPES = ('b')
    FEEDBACK_TYPES = ('r', 'hp', 'hn')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(env, instruction_type, feedback_type)

    @property
    def reward_range(self):
        return ((self.env.config['collision_reward']-1)*self.env.config['controlled_vehicles'], 0.0)

    def _reset(self, seed=None, options=None):
        options = options or {}
        observation, info = self.env.reset(seed=seed, options=options)
        if 'action' in info:
            del info['action']
        info['success'] = bool(info['is_success'])
        text_observation = self.textualize_observation(observation)
        instruction = highway_instruction[0] +'\n' + self.format(b_instruction)
        return dict(instruction=instruction, observation=observation, feedback=None), info

    def _step(self, action):
        #processed_action = self.extract_action(action)
        observation, reward, terminated, truncated, info = self.env.step(action)
        reward = float(reward)
        feedback = Feedback()
        feedback_type = self._feedback_type
        if 'r' in feedback_type: # reward feedback
            feedback.r = self.format(r_feedback, reward=reward) # base reward feedback
        if 'hp' in feedback_type: # hindsight positive: explanation on why something is correct
            if reward >= -self.env.config["success_goal_reward"]:
                feedback.hp = self.format(hp_feedback)
        if 'hn' in feedback_type:  # hindsight negative: explanation on why something is incorrect
            crashed = any(vehicle.crashed for vehicle in self.env.controlled_vehicles)
            if crashed:
                feedback.hn = self.format(hn_feedback)
        text_observation = self.textualize_observation(observation)
        return_observation = dict(instruction=None, observation=observation, feedback=feedback)

        info["success"] = bool(info["is_success"])

        return return_observation, reward, terminated, truncated, info

    def textualize_observation(self, observation):
        text_observation = 'Desired goal:' + np.array2string(observation['desired_goal'], precision=3)
        #text_observation += '\nAchieved goal:' + np.array2string(observation['achieved_goal'], precision=3)
        text_observation += '\nObservation:' + np.array2string(observation['observation'], precision=3)
        return text_observation
