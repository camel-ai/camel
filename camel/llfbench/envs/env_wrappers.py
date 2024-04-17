import gymnasium as gym
import copy
import numpy as np
import random
import traceback
import string
import gym as old_gym
from typing import Any, Optional
from gymnasium.wrappers.compatibility import LegacyEnv


def space_compatibility(old_space: old_gym.Space) -> gym.Space:
    """Converts a gym space to a gymnasium space.

    Args:
        old_space (old_gym.Space): the space to convert

    Returns:
        gym.Space: the converted space
    """
    if isinstance(old_space, old_gym.spaces.Discrete):
        return gym.spaces.Discrete(old_space.n)
    elif isinstance(old_space, old_gym.spaces.Box):
        return gym.spaces.Box(low=old_space.low, high=old_space.high, dtype=old_space.dtype)
    elif isinstance(old_space, old_gym.spaces.MultiBinary):
        return gym.spaces.MultiBinary(n=old_space.n)
    elif isinstance(old_space, old_gym.spaces.MultiDiscrete):
        return gym.spaces.MultiDiscrete(nvec=old_space.nvec)
    elif isinstance(old_space, old_gym.spaces.Tuple):
        return gym.spaces.Tuple(tuple(space_compatibility(s) for s in old_space.spaces))
    elif isinstance(old_space, old_gym.spaces.Dict):
        return gym.spaces.Dict({k: space_compatibility(v) for k, v in old_space.spaces.items()})
    elif isinstance(old_space, old_gym.spaces.Text):
        if hasattr(old_space, 'charset'):
            charset = old_space.charset
        elif hasattr(old_space, '_char_set'):
            charset = old_space._char_set
        else:
            raise AttributeError(f"Cannot find charset for space {old_space}")
        return gym.spaces.Text(max_length=old_space.max_length, min_length=old_space.min_length, charset=charset)
    else:
        raise NotImplementedError(f"Unsupported space type {old_space}")


class EnvCompatibility(gym.wrappers.EnvCompatibility):
    """ This fixes the bugs that the original EnvCompatibility
        1. does not convert the observation and action space.
        2. does not pass the __getattr__ to the wrapped env.
    """
    def __init__(self, old_env: LegacyEnv, render_mode: Optional[str] = None):
        super().__init__(old_env, render_mode)
        self.observation_space = space_compatibility(self.observation_space)
        self.action_space = space_compatibility(self.action_space)

    def __getattr__(self, name: str) -> Any:  # The wrapped env should behave like the original env.
        return getattr(self.env, name)

    def __getstate__(self):
        return vars(self)

    def __setstate__(self, state):
        vars(self).update(state)

class TextWrapper(gym.Wrapper):
    # This is a wrapper that can be applied on top of LLFWrapper to turn into a text-based env.
    RMIN = 0.0  # TODO maybe get this from the env

    def _parse_action(self, action):
        # parse action from string to internal action space
        # TODO
        if isinstance(self.env.action_space, gym.spaces.Discrete):
            action = int(action)
        elif isinstance(self.env.action_space, gym.spaces.Box):
            locals_dict = {}
            exec("action = np.array({})".format(action), globals(), locals_dict)
            action = locals_dict['action']
        elif isinstance(self.env.action_space, gym.spaces.Text):
            pass
        else:
            raise NotImplementedError
        return action

    def _parse_observation(self, observation):
        # Maybe parse the observation dict to string?
        # TODO
        return observation

    def step(self, action):
        assert type(action) == str
        try:
            action = self._parse_action(action)
            observation, reward, done, tuncated, info =  self.env.step(action)
        except Exception as e:  # Treat the exception as feedback
            if e == NotImplementedError:
                raise NotImplementedError
            feedback = f"Cannot parse action {action}.\n{traceback.format_exc()}"
            observation = dict(instruction=None, observation=None, feedback=feedback)
            reward = self.RMIN
            done = False
            tuncated = False
            info = {'success':False}
        return self._parse_observation(observation), reward, done, tuncated, info


class TerminalFreeWrapper(gym.Wrapper):
    #  Set terminated and timeout to False always
    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        return observation, reward, False, False, info

class RandomActionOrderWrapper(gym.Wrapper):

    def __init__(self, env):
        assert isinstance(env.action_space, gym.spaces.Discrete)
        super().__init__(env)
        self.__action_table = None

    def reset(self, *, seed=None, options=None):
        self.__action_table = [i for i in range(self.env.action_space.n)]
        np.random.shuffle(self.__action_table)
        return self.env.reset(seed=seed, options=options)

    def step(self, action):
        action = self.internal_action(action)
        return self.env.step(action)

    def internal_action(self, action):
        # map action from the external action space to the internal action space
        return self.__action_table[action]

    def external_action(self, action):
        # map action from the internal action space to the external action space
        return self.__action_table.index(action)


class FullInformationWrapper(gym.Wrapper):
    """
        This wrapper assumes env supports pickle serialization.
    """
    def __init__(self, env):
        assert isinstance(env.action_space, gym.spaces.Discrete)
        super().__init__(env)

    def oracle_info(self):
        full_information = dict()
        for i in range(self.env.action_space.n):
            env = copy.deepcopy(self.env)
            observation, reward, terminal, info = env.step(i)
            full_information[i] = dict(
                observation=observation,
                reward=reward,
                terminal=terminal,
                feedback=info['feedback'],
            )
        return full_information

    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        info['oracle_info'] = self.oracle_info()
        return observation, reward, terminated, truncated, info
