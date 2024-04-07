import os
import sys
import random
import string
import gymnasium as gym

from llfbench.envs.alfworld.prompts import *
from llfbench.envs.llf_env import Feedback
from llfbench.envs.alfworld.alfworld_download import download_alfworld_data


class Alfworld(gym.Env):

    # Basic (b), partial (p), and complete (c)
    INSTRUCTION_TYPES = ('b')        # ('b', 'p', 'c')

    # Feedback type:
    # r: reward
    # hn: hindsight negative
    # hp: hindsight positive
    # fn: future negative
    # fp: future positive
    FEEDBACK_TYPES = ('r', 'hn', 'hp', 'fn', 'fp')

    def __init__(self, instruction_type, feedback_type):

        config_file = "llfbench/envs/alfworld/base_config.yaml"

        # Read AI2Thor data
        os.environ["ALFWORLD_DATA"] = "alfworld_data"

        if not os.path.exists(os.environ["ALFWORLD_DATA"]) or len(os.listdir(os.environ["ALFWORLD_DATA"])) == 0:
            print(f"Downloading Alfworld data to {os.environ['ALFWORLD_DATA']}")
            download_alfworld_data(data_dir=os.environ['ALFWORLD_DATA'])
        else:
            print(f"Alfworld data already exists in {os.environ['ALFWORLD_DATA']} "
                  f"If this is old or stale, then delete it and run the code again.")

        old_sys_argv = list(sys.argv)
        print(f"Reading file {config_file}")
        sys.argv = [old_sys_argv[0], config_file]

        import alfworld.agents.environment as environment
        import alfworld.agents.modules.generic as generic

        # load config
        self.config = generic.load_config()
        self.env_type = self.config['env']['type']  # 'AlfredTWEnv' or 'AlfredThorEnv' or 'AlfredHybrid'

        # setup environment
        self.env = getattr(environment, self.env_type)(self.config, train_eval='train')
        self.env = self.env.init_env(batch_size=1)

        self.format = None
        self.instruction_type = instruction_type
        self.feedback_type = feedback_type
        self.already_won = False

        self.action_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)

        self.horizon = self.config["rl"]["training"]["max_nb_steps_per_episode"]
        self.timestep = 0

        # Markers
        self.instruction = None
        self.last_infos = None

        sys.argv = old_sys_argv

    def seed(self, seed):
        self.env.seed(seed)

    def _generate_instruction(self, reset_obs):

        # Separate task and use it as instruction
        task = reset_obs.split("\n\n")[-1].strip()
        if not task.endswith("."):
            task = task + "."

        instruction = self.format(instructions, task=task)

        return instruction

    @staticmethod
    def _generate_observation(obs, admissible_commands, won):

        actions = ", ".join(admissible_commands)
        obs_command = f"{obs}. You are allowed to take the following actions: {actions}."

        if won:
            obs_command += " Congratulations on solving the task!"
        return obs_command

    @staticmethod
    def _get_expert_action(infos):

        if "expert_plan" in infos and len(infos["expert_plan"]) == 1 and len(infos["expert_plan"][0]) == 1:
            return infos["expert_plan"][0][0]
        else:
            return None

    def reset(self, *, seed=None, options=None):

        if seed is not None:
            self.seed(seed)

        # Obs is text and info is a dict with the following keys:
        #   'won', 'extra.gamefile', 'expert_type', 'admissible_commands', 'expert_plan'
        obs, infos = self.env.reset()

        # Extract single item from batch
        obs = obs[0]
        won = bool(infos["won"][0])
        self.timestep = 0

        self.last_infos = infos
        self.instruction = self._generate_instruction(reset_obs=obs)
        self.already_won = won

        # Create observation by combining current obs with admissible commands
        admissible_commands = infos["admissible_commands"][0]
        obs_command = self._generate_observation(obs=obs,
                                                 admissible_commands=admissible_commands,
                                                 won=won)

        info = {
            "success": won,
            "expert_action": self._get_expert_action(infos),
            "admissible_commands": admissible_commands
        }

        return dict(instruction=self.instruction,
                    observation=obs_command,
                    feedback=None), info

    def _generate_feedback(self, action, reward, info, past_info, feedback_type=None):

        if feedback_type is None:
            feedback_type = self.feedback_type

        feedback = Feedback()

        if "r" in feedback_type:
            feedback.r = self.format(reward_descp, reward=reward)

        if "hn" in feedback_type:

            past_admissible_actions = past_info["admissible_commands"][0]
            past_opt_action = self._get_expert_action(past_info)

            if self.already_won:
                feedback.hn = self.format(hn_no_op)
            elif past_opt_action is None:
                feedback.hn = self.format(no_feedback)
            else:
                bad_actions = list(past_admissible_actions)
                bad_actions.remove(past_opt_action)

                avoid_action = random.choice(bad_actions)

                if action == avoid_action:
                    feedback.hn = self.format(mistake_bad_action_descp, avoid_action=avoid_action)
                else:
                    feedback.hn = self.format(correct_bad_action_descp, avoid_action=avoid_action)

        if "hp" in feedback_type:

            past_opt_action = self._get_expert_action(past_info)

            if self.already_won:
                feedback.hp = self.format(hp_no_op)
            elif past_opt_action is None:
                feedback.hp = self.format(no_feedback)
            else:
                if past_opt_action == action.lower().strip():
                    feedback.hp = self.format(correct_good_action_descp, past_opt_action=past_opt_action)
                else:
                    feedback.hp = self.format(mistake_good_action_descp, past_opt_action=past_opt_action)

        if "fn" in feedback_type:

            admissible_actions = info["admissible_commands"][0]
            opt_action = self._get_expert_action(info)

            if self.already_won:
                feedback.fn = self.format(fn_no_op)
            elif opt_action is None:
                feedback.fn = self.format(no_feedback)
            else:
                bad_actions = list(admissible_actions)
                bad_actions.remove(opt_action)

                avoid_action = random.choice(bad_actions)

                feedback.fn = self.format(avoid_bad_action_descp, avoid_action=avoid_action)

        if "fp" in feedback_type:

            opt_action = self._get_expert_action(info)

            if self.already_won:
                feedback.fp = self.format(fp_no_op)
            elif opt_action is None:
                feedback.fp = self.format(no_feedback)
            else:
                feedback.fp = self.format(follow_opt_action_descp, opt_action=opt_action)

        return feedback

    def step(self, action):

        if self.last_infos is None:
            raise AssertionError("Found self.last_infos as None. You must reset before step.")

        if type(action) != str:
            raise TypeError(f"Expected action of type string but found {type(action)}.")

        action = action.lower().strip()

        # TODO: Parse the action to find the closest admissible_command
        # admissible_commands = list(self.last_infos['admissible_commands'][0])
        obs, rewards, dones, infos = self.env.step([action])

        self.timestep += 1

        # Extract single item from batch
        obs = obs[0]
        reward = rewards[0]
        done = dones[0]
        won = bool(infos["won"][0])

        if self.already_won:
            # This is done so that the agent cannot cheat by taking actions even after winning
            reward = 0

        terminated = done or won
        truncated = self.timestep >= self.horizon
        self.already_won = self.already_won or won

        # Create observation by combining current obs with admissible commands
        admissible_commands = infos["admissible_commands"][0]
        obs_command = self._generate_observation(obs=obs,
                                                 admissible_commands=admissible_commands,
                                                 won=won)

        # Feedback
        feedback = self._generate_feedback(action=action,
                                           reward=reward,
                                           info=infos,
                                           past_info=self.last_infos)

        info = {
            "feedback": feedback,
            "success": won,
            "expert_action": self._get_expert_action(infos),
            "admissible_commands": admissible_commands,
        }

        self.last_infos = infos

        next_packed_obs = dict(instruction=None,
                               observation=obs_command,
                               feedback=feedback)

        return next_packed_obs, reward, terminated, truncated, info
