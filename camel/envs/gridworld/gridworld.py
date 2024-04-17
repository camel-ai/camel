import sys
import random
import string
import gymnasium as gym

from collections import deque
from llfbench.envs.gridworld import prompts
from llfbench.envs.gridworld.room import Room
from llfbench.envs.gridworld.scene import Scene
from llfbench.envs.llf_env import Feedback


class Gridworld(gym.Env):

    # Basic (b), partial (p), and complete (c)
    INSTRUCTION_TYPES = ('b', 'p', 'c')

    # Feedback type:
    # r: reward
    # hn: hindsight negative
    # hp: hindsight positive
    # fn: future negative
    # fp: future positive
    FEEDBACK_TYPES = ('r', 'hn', 'hp', 'fn', 'fp')

    # feedback_level="gold"
    def __init__(self, num_rooms=20, horizon=20, fixed=True, instruction_type="c", feedback_type="hp", min_goal_dist=4):
        super(Gridworld, self).__init__()

        # Action space consists of 4 actions: North, South, East and West
        self.num_actions = 4
        self.action_space = gym.spaces.Discrete(self.num_actions)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.reward_range = (0, 1.0)

        self.format = None
        self.instruction_type = instruction_type
        self.feedback_type = feedback_type

        self.num_rooms = num_rooms
        self.horizon = horizon
        assert self.horizon >= 5, "Horizon must be at least 5 to allow agent to somewhat explore the world"
        self.min_goal_dist = min_goal_dist

        self.fixed = fixed

        # Counters that may have to be reset
        self.instruction = None
        self.current_timestep = 0.0
        self.current_scene = None
        self.current_room = None
        self.goal_prev_visited = False

    def seed(self, seed=None):
        random.seed(seed)

    def make_scene(self):

        # Process of creating a scene works as follows
        # We start by creating a room
        # We add between 1-4 edges, we create new rooms and add them to the queue

        scene = Scene()
        queue = deque()

        room = scene.create_random_empty_room(pos=(0, 0))
        queue.append(room)

        available_objects = list(Room.OBJECTS)

        while len(queue) > 0 and len(scene.rooms) < self.num_rooms:

            room = queue.popleft()

            # Sample a subset of edges from the list of available directions
            available_directions = [direction for direction in Scene.DIRECTIONS
                                    if direction not in scene.doors[room]]

            if len(available_directions) == 0:
                # All directions from this room has been connected
                continue

            num_dir = random.randint(1, len(available_directions) - 1)
            chosen_directions = random.sample(available_directions, k=num_dir)

            for i, dir_to in enumerate(chosen_directions):

                # TODO Connect the new room not just to where it spawned from but also other rooms to create a graph
                new_pos = scene.get_relative_pos(room, dir_to, length=1)
                ngbr_room = scene.create_random_empty_room(pos=new_pos)
                scene.add_door(room=room,
                               dir_to=dir_to,
                               other_room=ngbr_room)
                queue.append(ngbr_room)

                if len(scene.rooms) >= self.num_rooms:
                    break

        indices = list(range(0, scene.num_rooms()))
        random.shuffle(indices)

        for i in indices:
            if len(available_objects) > 0 and random.random() < 0.25:
                obj = random.choice(available_objects)
                room = scene.get_room(i)
                room.add_object(obj=obj)
                available_objects.remove(obj)

        # Add start room
        rooms = scene.get_rooms()

        goal_room = random.choice(rooms)
        goal_room.add_goal()
        scene.get_add_goal_room(goal_room=goal_room)

        # Do BFS
        scene.start_bfs(goal_room)

        # Add key in a room at least k steps away
        rooms = [ngbr_room for ngbr_room, path in scene.bfs_path.items()
                 if self.min_goal_dist < len(path) < self.horizon - 5 and ngbr_room != goal_room]

        if len(rooms) == 0:
            rooms = [ngbr_room for ngbr_room, path in scene.bfs_path.items() if ngbr_room != goal_room]

        start_room = random.choice(rooms)
        scene.get_add_start_room(start_room=start_room)

        return scene

    def make_room_obs(self, room):
        obs = room.describe_room() + self.current_scene.get_room_doors_description(room)
        return obs

    def reset(self, *, seed=None, options=None):

        if seed is not None:
            self.seed(seed)

        # Counters that may have to be reset
        self.current_timestep = 0.0

        self.current_scene = self.make_scene()

        self.current_room = self.current_scene.get_start_room()
        self.goal_prev_visited = (self.current_room == self.current_scene.goal_room)

        obs = self.make_room_obs(self.current_room)
        self.instruction = self.generate_instruction()

        gold_action = None if self.goal_prev_visited else self.current_scene.get_gold_action(self.current_room)
        gold_action_ix = None if gold_action is None else Scene.DIRECTIONS.index(gold_action)
        
        info = {
            "success": self.goal_prev_visited,
            "expert_action": gold_action_ix
        }

        return dict(instruction=self.instruction,
                    observation=obs,
                    feedback=None), info

    def generate_instruction(self):

        base_instruction = self.format(prompts.instructions)

        if self.instruction_type == "b":
            # Basic instruction
            instruction = base_instruction

        elif self.instruction_type == "p":
            # Partial instruction.
            instruction = base_instruction + " " + self.get_optimal_path_desc(partial=True)

        elif self.instruction_type == "c":
            # Complete instruction. Optimal policy can be achieved using just the instruction
            instruction = base_instruction + " " + self.get_optimal_path_desc(partial=False)
        else:
            raise AssertionError(f"Unhandled feedback_level {self.instruction_type}")

        return instruction

    def get_optimal_path_desc(self, partial=False):

        optimal_path = self.current_scene.get_optimal_path(self.current_room)

        if len(optimal_path) == 0:
            path_descps = ["Congratulations! You are already in the room with treasure."]
        else:
            path_descps = ["I will also provide you a path towards reaching your goal."]

        for ix, (direction, room) in enumerate(optimal_path):
            if ix == 0:
                path_descps.append(f"First, you follow {direction} direction, to reach the room {room.get_name()}.")
            elif ix == len(optimal_path) - 1:
                path_descps.append(f"Next, you follow {direction} direction, to reach the room {room.get_name()}.")
            else:
                path_descps.append(f"Finally, you follow {direction} direction, to reach the "
                                   f"room {room.get_name()} which has treasure.")

        if partial:
            r = 0.4 + random.random() * 0.2
            partial_len = int(len(path_descps) * r)
            opt_path_desc = " ".join(path_descps[:partial_len])
        else:
            opt_path_desc = " ".join(path_descps)
        return opt_path_desc

    def log_env(self, logger):
        self.current_scene.log_scene(logger)

    def step(self, action):

        old_gold_action = self.current_scene.get_gold_action(self.current_room)
        old_room = self.current_room.get_name()

        if 0 <= action < 4:
            new_room = self.current_scene.check_room_door(self.current_room, Scene.DIRECTIONS[action])
        else:
            raise AssertionError(f"Action must be in {{0, 1, 2, 3}} but found {action}")

        if new_room is not None:
            self.current_room = new_room
            next_obs = self.make_room_obs(self.current_room)
        else:
            next_obs = f"You remained in room {self.current_room.get_name()} " \
                       f"as there is no door in the direction {Scene.DIRECTIONS[action]}."

        # Compute the reward
        reward = 1.0 if self.current_room == self.current_scene.goal_room and not self.goal_prev_visited else 0.0

        feedback = self.generate_feedback(action=action,
                                          reward=reward,
                                          old_gold_action=old_gold_action,
                                          old_room=old_room)

        # Update the goal revisited
        self.goal_prev_visited = self.goal_prev_visited or (self.current_room == self.current_scene.goal_room)

        # Update the counter and compute done
        self.current_timestep += 1
        terminated = False
        truncated = self.current_timestep >= self.horizon

        gold_action = None if self.goal_prev_visited else self.current_scene.get_gold_action(self.current_room)
        gold_action_ix = None if gold_action is None else Scene.DIRECTIONS.index(gold_action)

        info = {
            "feedback": feedback,
            "success": self.goal_prev_visited,
            "expert_action": gold_action_ix
        }

        next_packed_obs = dict(instruction=None,
                               observation=next_obs,
                               feedback=feedback)

        return next_packed_obs, reward, terminated, truncated, info

    def generate_feedback(self, action, reward, old_gold_action, old_room, feedback_type=None):

        gold_action = self.current_scene.get_gold_action(self.current_room)

        if reward != 1.0 and not self.goal_prev_visited:
            assert old_gold_action is not None, "can only be none if you reach the goal"
            assert gold_action is not None, "can only be none if you reach the goal"

        if feedback_type is None:
            feedback_type = self.feedback_type

        feedback = Feedback()

        if "r" in feedback_type:      # Reward described in text
            feedback.r = self.format(prompts.reward_descp, reward=reward)

        if "hn" in feedback_type:     # Hindsight negative

            if self.goal_prev_visited:
                feedback.hp = self.format(prompts.hn_no_op)

            else:
                # This implies we have not reached the goal neither before or nor in this stage
                # Sample a bad action at previous time step, and provide feedback as follows:
                #       Case 1: If the agent avoided taking the bad action, then say good job
                #       Case 2: If the agent takes the bad action, then tell it to avoid

                all_wrong_directions = list(Scene.DIRECTIONS)
                all_wrong_directions.remove(old_gold_action)
                avoid_action = random.choice(all_wrong_directions)

                if avoid_action != Scene.DIRECTIONS[action]:
                    feedback.hn = self.format(prompts.hn_success_descp, avoid_action=avoid_action)
                else:
                    feedback.hn = self.format(prompts.hn_fail_descp, avoid_action=avoid_action)

        if "hp" in feedback_type:     # Hindsight positive

            if self.goal_prev_visited:
                feedback.hp = self.format(prompts.hp_no_op)

            else:
                # This implies we have not reached the goal neither before or nor in this stage
                # Compute the gold action at previous time step, and provide feedback as follows:
                #       Case 1: If the agent took the good action, then say good job
                #       Case 2: If the agent didnt take the good action, then inform it to take the good action

                if old_gold_action != Scene.DIRECTIONS[action]:
                    # Case 1: If the agent takes an action that resulted in no transition
                    feedback.hp = self.format(prompts.hp_fail_descp, old_gold_action=old_gold_action, room=old_room)
                else:
                    feedback.hp = self.format(prompts.hp_succ_descp, old_gold_action=old_gold_action, room=old_room)

        if "fn" in feedback_type:      # Future negative

            if reward == 1.0 or self.goal_prev_visited:
                feedback.fn = self.format(prompts.fn_no_op)

            else:
                # This implies we have not reached the goal neither before or nor in this stage
                # Sample a bad action at this time step, and tell the agent not to take it

                gold_action = self.current_scene.get_gold_action(self.current_room)
                all_directions = list(Scene.DIRECTIONS)
                all_directions.remove(gold_action)

                avoid_action = random.choice(all_directions)

                feedback.fn = self.format(prompts.fn, avoid_action=avoid_action, new_room=self.current_room.get_name())

        if "fp" in feedback_type:      # Future positive

            if reward == 1.0 or self.goal_prev_visited:
                feedback.fp = self.format(prompts.fp_no_op)

            else:
                # This implies we have not reached the goal neither before or nor in this stage
                # Compute the gold action at this time step, and tell the agent not to take it

                gold_action = self.current_scene.get_gold_action(self.current_room)

                feedback.fp = self.format(prompts.fp, gold_action=gold_action, new_room=self.current_room.get_name())

        return feedback
