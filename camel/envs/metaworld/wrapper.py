from typing import Dict, SupportsFloat, Union
import numpy as np
from llfbench.envs.llf_env import LLFWrapper, Feedback
from llfbench.envs.metaworld.prompts import *
from llfbench.envs.metaworld.gains import P_GAINS
import metaworld
import importlib
import json
from textwrap import dedent, indent
from metaworld.policies.policy import move
from metaworld.policies.action import Action
from metaworld.policies import SawyerDrawerOpenV1Policy, SawyerDrawerOpenV2Policy, SawyerReachV2Policy

class MetaworldWrapper(LLFWrapper):

    """ This is wrapper for gym_bandits. """

    INSTRUCTION_TYPES = ('b') #('b', 'p', 'c')
    FEEDBACK_TYPES = ('r', 'hp', 'hn', 'fp')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(env, instruction_type, feedback_type)
        # load the scripted policy
        if self.env.env_name=='peg-insert-side-v2':
            module = importlib.import_module(f"metaworld.policies.sawyer_peg_insertion_side_v2_policy")
            self._policy = getattr(module, f"SawyerPegInsertionSideV2Policy")()
        else:
            module = importlib.import_module(f"metaworld.policies.sawyer_{self.env.env_name.replace('-','_')}_policy")
            self._policy = getattr(module, f"Sawyer{self.env.env_name.title().replace('-','')}Policy")()
        self.p_control_time_out = 20 # timeout of the position tracking (for convergnece of P controller)
        self.p_control_threshold = 1e-4 # the threshold for declaring goal reaching (for convergnece of P controller)
        self._current_observation = None

    @property
    def reward_range(self):
        return (0,10)

    @property
    def mw_env(self):
        return self.env.env

    @property
    def mw_policy(self):
        return self._policy

    @property
    def current_observation(self):  # external interface
        """ This is a cache of the latest (raw) observation. """
        return self._current_observation

    @property
    def _current_pos(self):
        """ Curret position of the hand. """
        return self.mw_policy._parse_obs(self.current_observation)['hand_pos']

    @property
    def expert_action(self):
        """ Compute the desired xyz position and grab effort from the MW scripted policy.

            We want to compute the desired xyz position and grab effort instead of
            the low level action, so we cannot call directly
            self.mw_policy.get_aciton
        """
        # Get the desired xyz position from the MW scripted policy
        if type(self.mw_policy) in [SawyerDrawerOpenV1Policy, SawyerDrawerOpenV2Policy]:
            o_d = self.mw_policy._parse_obs(self.current_observation)
            # NOTE this policy looks different from the others because it must
            # modify its p constant part-way through the task
            pos_curr = o_d["hand_pos"]
            pos_drwr = o_d["drwr_pos"]
            # align end effector's Z axis with drawer handle's Z axis
            if np.linalg.norm(pos_curr[:2] - pos_drwr[:2]) > 0.06:
                desired_xyz = pos_drwr + np.array([0.0, 0.0, 0.3])
            # drop down to touch drawer handle
            elif abs(pos_curr[2] - pos_drwr[2]) > 0.04:
                desired_xyz = pos_drwr
            # push toward a point just behind the drawer handle
            # also increase p value to apply more force
            else:
                desired_xyz = pos_drwr + np.array([0.0, -0.06, 0.0])
        elif type(self.mw_policy) == SawyerReachV2Policy:
            desired_xyz = self.mw_policy._parse_obs(self.current_observation)['goal_pos']
        else:
            if hasattr(self.mw_policy,'_desired_xyz'):
                compute_goal = self.mw_policy._desired_xyz
            elif hasattr(self.mw_policy,'_desired_pos'):
                compute_goal = self.mw_policy._desired_pos
            elif hasattr(self.mw_policy,'desired_pos'):
                compute_goal = self.mw_policy.desired_pos
            else:
                raise NotImplementedError
            desired_xyz = compute_goal(self.mw_policy._parse_obs(self.current_observation))
        # Get the desired grab effort from the MW scripted policy
        desired_grab = self.mw_policy.get_action(self.current_observation)[-1]  # TODO should be getting the goal
        return np.concatenate([desired_xyz, np.array([desired_grab])])

    def p_control(self, action):
        """ Compute the desired control based on a position target (action[:3])
        using P controller provided in Metaworld."""
        assert len(action)==4
        p_gain = P_GAINS[type(self.mw_policy)]
        if type(self.mw_policy) in [type(SawyerDrawerOpenV1Policy), type(SawyerDrawerOpenV2Policy)]:
            # This needs special cares. It's implemented differently.
            o_d = self.mw_policy._parse_obs(self.current_observation)
            pos_curr = o_d["hand_pos"]
            pos_drwr = o_d["drwr_pos"]
            # align end effector's Z axis with drawer handle's Z axis
            if np.linalg.norm(pos_curr[:2] - pos_drwr[:2]) > 0.06:
                p_gain = 4.0
            # drop down to touch drawer handle
            elif abs(pos_curr[2] - pos_drwr[2]) > 0.04:
                p_gain = 4.0
            # push toward a point just behind the drawer handle
            # also increase p value to apply more force
            else:
                p_gain= 50.0

        control = Action({"delta_pos": np.arange(3), "grab_effort": 3})
        control["delta_pos"] = move(self._current_pos, to_xyz=action[:3], p=p_gain)
        control["grab_effort"] = action[3]
        return control.array

    def _step(self, action):
        # Run P controller until convergence or timeout
        # action is viewed as the desired position + grab_effort
        previous_pos = self._current_pos  # the position of the hand before moving
        for _ in range(self.p_control_time_out):
            control = self.p_control(action)
            observation, reward, terminated, truncated, info = self.env.step(control)
            self._current_observation = observation
            desired_pos = action[:3]
            if np.abs(desired_pos - self._current_pos).max() < self.p_control_threshold:
                break

        feedback_type = self._feedback_type
        # Some pre-computation of the feedback
        expert_action = self.expert_action
        moving_away = np.linalg.norm(expert_action[:3]-previous_pos) < np.linalg.norm(expert_action[:3]-self._current_pos)
        if expert_action[3] > 0.5 and action[3] < 0.5:  # the gripper should be closed instead.
            gripper_feedback = self.format(close_gripper_feedback)
        elif expert_action[3] < 0.5 and action[3] > 0.5:  #the gripper should be open instead.
            gripper_feedback = self.format(open_gripper_feedback)
        else:
            gripper_feedback = None
        # Compute feedback
        feedback = Feedback()
        if 'r' in  feedback_type:
            feedback.r = self.format(r_feedback, reward=reward)
        if 'hp' in feedback_type:  # moved closer to the expert goal
            _feedback = self.format(hp_feedback) if not moving_away else None
            if gripper_feedback is not None:
                if _feedback is not None:
                    _feedback += 'But, ' + gripper_feedback[0].lower() + gripper_feedback[1:]
                else:
                    _feedback = gripper_feedback
            feedback.hp = _feedback
        if 'hn' in feedback_type:  # moved away from the expert goal
            # position feedback
            _feedback = self.format(hn_feedback) if moving_away else None
            # gripper feedback
            if gripper_feedback is not None:
                if _feedback is not None:
                    _feedback += 'Also, ' + gripper_feedback[0].lower() + gripper_feedback[1:]
                else:
                    _feedback = gripper_feedback
            feedback.hn = _feedback
        if 'fp' in feedback_type:  # suggest the expert goal
            feedback.fp = self.format(fp_feedback, expert_action=self.textualize_expert_action(expert_action))
        observation = self.textualize_observation(observation)
        info['success'] = bool(info['success'])

        return dict(instruction=None, observation=observation, feedback=feedback), float(reward), terminated, truncated, info

    def _reset(self, *, seed=None, options=None):
        self._current_observation, info = self.env.reset(seed=seed, options=options)
        observation = self.textualize_observation(self._current_observation)
        task = self.env.env_name.split('-')[0]
        instruction = self.format(mw_instruction, task=task)
        info['success'] = False
        return dict(instruction=instruction, observation=observation, feedback=None), info


    def textualize_expert_action(self, action):
        """ Parse action into text. """
        # The idea is to return something like
        # f"delta x: {action[0]:.2f}, delta y:{action[1]:.2f}, delta z:{action[2]:.2f}, gripper state:{action[3]:.1f}"
        # or another action text format if the action isn't a delta.
        # TODO should not be the raw action
        return np.array2string(action, precision=2)

    def textualize_observation(self, observation):
        """ Parse np.ndarray observation into text. """
        obs_dict = self.mw_policy._parse_obs(observation)
        # remove unused parts
        unused_keys = [k for k in obs_dict.keys() if 'unused' in k or 'extra_info' in k]
        for k in unused_keys:
            del obs_dict[k]
        # convert np.ndarray to list
        for k,v in obs_dict.items():
            if isinstance(v, np.ndarray):
                obs_dict[k] = np.array2string(v, precision=3)
            else: # it's a scalar
                obs_dict[k] = f"{v:.3f}"
        observation_text = json.dumps(obs_dict)
        return observation_text