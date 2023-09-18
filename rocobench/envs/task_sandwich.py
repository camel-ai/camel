import os
import copy
import time
import cv2 
import random
import numpy as np  
from pydantic import dataclasses, validator 
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import dm_control 
from dm_control.utils.transformations import mat_to_quat
from pyquaternion import Quaternion
from rocobench.envs.base_env import MujocoSimEnv, EnvState
from rocobench.envs.robot import SimRobot
from rocobench.envs.constants import UR5E_SUCTION_CONSTANTS, HUMANOID_CONSTANTS, HUMANOID_LEFT_BODY_NAMES

SANDWICH_TASK_OBJECTS=[ 
    "table",
    "cutting_board",  
    "bread_slice1",
    "bread_slice2",
    "bacon",
    "cheese",
    "tomato", 
    "cucumber",
    "ham",
    "beef_patty",
]
SANDWICH_RECIPES = {
    "bacon": ["bread_slice1", "bacon", "cheese", "tomato", "bread_slice2"],
    "vegetarian": ["bread_slice1", "cheese", "tomato", "cucumber", "bread_slice2"],
    "beef_patty": ["bread_slice1", "beef_patty", "cheese", "tomato", "bread_slice2"],
    "ham": ["bread_slice1", "ham", "cheese", "tomato", "cucumber", "bread_slice2"],
}
bacon_recipe = ", ".join(SANDWICH_RECIPES["bacon"])

SANDWICH_ACTION_SPACE="""
[Action Options]
1) PICK <obj>, Only PICK if gripper is empty. PICK only the correct next item according to the recipe.
2) PUT <obj1> <obj2>. <obj1> can be one of the foods. <obj2> can be food, cutting_board, or table.
3) WAIT, do nothing.
Only one robot can PUT each round. You must PICK up an item before PUT. 
[Action Output Instruction]
Must first output 'EXECUTE\n', then give exactly one action per robot, put each on a new line.
Example#1: 'EXECUTE\nNAME Chad ACTION PUT bread_slice1 cutting_board\nNAME Dave ACTION PICK tomato\n'
Example#2: 'EXECUTE\nNAME Chad ACTION WAIT\nNAME Dave ACTION PUT cheese tomato\n'
"""

SANDWICH_CHAT_PROMPT="""The robots discuss before taking actions. Carefully consider environment feedback and others' responses, and coordinate to strictly follow the sandwich recipe and avoid collision.
They talk in order [Chad],[Dave],[Chad],..., after reaching agreement, they output a plan with **exactly** one ACTION per robot, and stop talking. Their chat and final plan are: """

SANDWICH_PLAN_PROMPT="""
Plan one ACTION for each robot at every round. The robot ACTIONs must strictly follow the sandwich recipe and avoid collision.
"""

class MakeSandwichTask(MujocoSimEnv):
    def __init__( 
        self,
        filepath: str = "rocobench/envs/task_sandwich.xml",
        one_obj_each: bool = False,
        **kwargs,
    ):    
        self.robot_names = ["ur5e_suction", "humanoid"] 
        self.agent_names = ["Chad", "Dave"]
        self.robot_name_map = {
            "ur5e_suction": "Chad",
            "humanoid": "Dave", 
        }
        self.robot_name_map_inv = {
            "Chad": "ur5e_suction",
            "Dave": "humanoid", 
        }
        self.robots = dict()  
        self.food_items = SANDWICH_TASK_OBJECTS[2:] # exclude cutting board and table

        super(MakeSandwichTask, self).__init__(
            filepath=filepath, 
            task_objects=SANDWICH_TASK_OBJECTS,
            agent_configs=dict(
                ur5e_suction=UR5E_SUCTION_CONSTANTS,
                humanoid=HUMANOID_CONSTANTS,
            ), 
            skip_reset=True,
            **kwargs
        ) 
        self.cutting_board_pos = self.physics.data.body("cutting_board").xpos.copy()  

        all_panels = []
        for n in range(self.physics.model.ngeom):
            geom = self.physics.model.geom(n)
            if 'panel' in geom.name:
                all_panels.append(
                    (geom.name, geom.pos, geom.size)
                )
        assert len(all_panels) >= len(self.food_items), "Not enough panel positions to sample from"
        self.all_panels = all_panels
        self.left_panels = [p for p in all_panels if p[1][0] < 0]
        self.right_panels = [p for p in all_panels if p[1][0] > 0]
        self.reset(keyframe_id=0, home_pos=None, reload=False) # special case for this task
        
        suction_config = UR5E_SUCTION_CONSTANTS.copy()
        self.robots[
            self.robot_name_map["ur5e_suction"]
            ] = SimRobot(
                physics=self.physics,
                use_ee_rest_quat=False,
                **suction_config,
        )
        humanoid_config = HUMANOID_CONSTANTS.copy()
        self.robots[
            self.robot_name_map["humanoid"]
            ] = SimRobot(
                physics=self.physics,
                use_ee_rest_quat=False,
                **humanoid_config,
        )
         
        self.align_threshold = 0.15
        self.recipe_order = SANDWICH_RECIPES["bacon"]
        
 
    
    @property 
    def use_prepick(self):
        return True 

    @property
    def use_preplace(self):
        return True
        
    def get_target_pos(self, agent_name, target_name) -> Optional[np.ndarray]: 
        ret = None 
        robot_name = self.robot_name_map_inv[agent_name]
        if target_name in self.food_items + ["cutting_board"]:
            sname = target_name
            ret = self.physics.data.site(sname).xpos.copy() 
        elif target_name == "table":
            if agent_name == "Chad" or robot_name == "ur5e_suction":
                panels = self.right_panels
            else:
                panels = self.left_panels
            # pick the panel that's farthest from all the objects on this side of table
            empty_pos = panels[0][1]
            for p in panels:
                dist_to_objs = [
                    np.linalg.norm(
                        self.physics.data.site(obj).xpos[:2] - p[1][:2]
                    ) for obj in self.food_items
                ]
                if all([d > 0.1 for d in dist_to_objs]):
                    empty_pos = p[1]
                    break
            ret = empty_pos
        return ret 
         
    def get_target_quat(self, agent_name, target_name) -> Optional[np.ndarray]:
        ret = None 
        if target_name in self.food_items + ["cutting_board"]:
            try:
                xmat = self.physics.data.site(target_name).xmat.copy()
                ret = mat_to_quat(xmat.reshape(3,3))
            except KeyError:
                pass
        if target_name == "table":
            ret = np.array([1, 0, 0, 0])
        return ret

    def get_graspable_objects(self): 
        return dict(
            Chad=self.food_items,
            Dave=self.food_items, 
        )

    def get_grasp_site(self, obj_name: str = "cheese") -> Optional[str]:
        if obj_name in SANDWICH_TASK_OBJECTS:
            return obj_name
        else:
            return None
    
    def get_reward_done(self, obs): 
        # task specific!
        rew = 0
        done = False 
        board_contacts = obs.objects['cutting_board'].contacts
        if len(board_contacts) == 0:
            return 0, False
        elif 'bread_slice1' not in board_contacts:
            return 0, True

        for i, item in enumerate(self.recipe_order):
            item_contacts = obs.objects[item].contacts
            if len(item_contacts) == 0:
                return 0, False
            if i == len(self.recipe_order) - 1:
                return 1, True
            next_item = self.recipe_order[i+1]
            if next_item not in item_contacts:
                return 0, False 
            
        return rew, done
   
    def get_robot_reach_range(self, robot_name: str) -> Dict[str, Tuple[float, float]]:
        if robot_name == "humanoid" or robot_name == self.robot_name_map["humanoid"]:
            return dict(x=(-1.4, 0.1), y=(0.3, 1.5), z=(0.16, 1))
        elif robot_name == "ur5e_suction" or robot_name == self.robot_name_map["ur5e_suction"]:
            return dict(x=(-0.1, 1.3), y=(-0.2, 0.7), z=(0.16, 1))
        else:
            raise NotImplementedError
    
    def sample_initial_scene(self):
        # sample locations of the pan 
        sampled_panels = []
        n_left_items = len(self.food_items) // 2
        left_idxs = self.random_state.choice(
                len(self.left_panels), size=n_left_items, replace=False
                )
        sampled_panels.extend(
            [self.left_panels[i] for i in left_idxs]
        )
 
        n_right_items = len(self.food_items) - n_left_items
        right_idxs = self.random_state.choice(
                len(self.right_panels), size=n_right_items, replace=False
                )
        sampled_panels.extend(
            [self.right_panels[i] for i in right_idxs]
        )
        
        for food, (_, pos, size) in zip(self.food_items, sampled_panels): 
            # new_quat = Quaternion(
            #     axis=[0,0,1], angle=self.random_state.uniform(low=0, high=np.pi*2)
            #     ) 
        
            # new_quat = np.array([new_quat.w, new_quat.x, new_quat.y, new_quat.z]) 
            new_quat = None # TODO: fix the picking quat before enable sampling
            new_pos = self.random_state.uniform(
                low=pos - size/2, high=pos + size/2
            )
            new_pos[2] = 0.2
            self.reset_body_pose(
                body_name=food,
                pos=new_pos,
                quat=new_quat,
            )  
            self.reset_qpos(
                jnt_name=f"{food}_joint",
                pos=new_pos,
                quat=new_quat,
            )

        self.physics.forward()
        self.physics.step(100) # let the food drop 
        # sampling a random recipe!!
        recipe_idx = self.random_state.choice(
            len(SANDWICH_RECIPES), size=1, replace=False)[0]
        recipe = list(SANDWICH_RECIPES.keys())[recipe_idx]
        recipe_order = SANDWICH_RECIPES[recipe]
        # randomly shuffle the order
        food_items = recipe_order[1:-1].copy()
        self.random_state.shuffle(food_items)
        recipe_order[1:-1] = food_items
        self.recipe_order = recipe_order
        self.recipe_name = f"{recipe}_sandwich"
    
    def get_allowed_collision_pairs(self) -> List[Tuple[int, int]]:
        table_id = self.physics.model.body("table").id 
        board_id = self.physics.model.body("cutting_board").id
        food_ids = [self.physics.model.body(food).id for food in self.food_items]
        
        ret = []
        for food_id in food_ids:
            ret.append((food_id, table_id)) 
            ret.append((food_id, board_id))
            for food_id2 in food_ids:
                if food_id != food_id2:
                    ret.append((food_id, food_id2))

        for link_id in self.robots["Chad"].all_link_body_ids + self.robots["Dave"].all_link_body_ids:
            for food_id in food_ids + [board_id]:
                ret.append((link_id, food_id))
        
        # humanoid left arm is allowed to touch the table
        for link_name in HUMANOID_LEFT_BODY_NAMES:
            link_id = self.physics.model.body(link_name).id
            ret.append((link_id, table_id))
        # special case for suction gripper sometimes it can touch the table
        ret.extend(
            [
                (self.physics.model.body("ur5e_suction").id, table_id),
                (self.physics.model.body("rpalm").id, table_id),
            ]

        )
        return ret
    
    def get_obs(self):
        obs = super().get_obs()
        for name in self.robot_names:
            assert getattr(obs, name) is not None, f"Robot {name} is not in the observation"
        return obs
 
    def describe_food_state(self, obs, item_name: str = "bacon") -> str:
        food_state = obs.objects[item_name]
        food_desp = f"{item_name}: "
        contacts = food_state.contacts 
        if 'table' in contacts and 'cutting_board' not in contacts:
            side = 'left' if food_state.xpos[0] < 0 else 'right'
            food_desp += f"on {side} side"
        elif 'cutting_board' in contacts:
            xpos = obs.objects['cutting_board'].xpos
            if xpos[2] < food_state.xpos[2]:
                food_desp += f"on cutting_board"
        elif any([f in contacts for f in self.food_items]):
            for f in self.food_items:
                xpos = obs.objects[f].xpos
                if f != item_name and f in contacts and xpos[2] < food_state.xpos[2]:
                    food_desp += f"atop {f}" 
        else:
            food_desp = ""
        return food_desp
    
    def describe_robot_state(self, obs, robot_name: str = "humanoid") -> str:
        robot_state = getattr(obs, robot_name)
        # x, y, z = robot_state.xpos.tolist()
        # robot_desp += f"{agent_name}'s gripper is at ({x:.2f}, {y:.2f}, {z:.2f}),\n"
        contacts = robot_state.contacts 
        agent_name = self.robot_name_map[robot_name]
        if len(contacts) == 0:
            robot_desp = f"{agent_name}'s gripper is empty"
        else:
            obj = ",".join([c for c in contacts]) 
            robot_desp = f"{agent_name}'s gripper is holding {obj}"
        return robot_desp

    def get_agent_prompt(self, obs, agent_name: str = "Chad") -> str:
        assert agent_name in self.agent_names, f"Agent {agent_name} is not in the scene"
        other_robot = [r for r in self.agent_names if r != agent_name][0]
        table_side = "left" if agent_name == "Dave" else "right"
        other_side = "right" if agent_name == "Dave" else "left"

        recipe_str = ", ".join(self.recipe_order)
        
        # each agent can only see items on their own side of the table or on the cutting board
        food_states = [] 
        for food in self.food_items:
            desp = self.describe_food_state(obs, food) 
            if (other_side not in desp and len(desp) > 0):
                food_states.append(desp.replace(table_side, "your"))
        food_states = "\n".join(food_states)

        robot_name = self.robot_name_map_inv[agent_name]
        agent_state = self.describe_robot_state(obs, robot_name)
        agent_state = agent_state.replace(f"{agent_name}'s", "Your")
        agent_prompt = f"""
You are a robot {agent_name}, collaborating with {other_robot} to make a [{self.recipe_name}].
Food items must be stacked following this order: {recipe_str}, where bread_slice1 must be PUT on cutting_board. 
You must stay on {table_side} side of the table! This means you can only PICK food from {table_side} side, and {other_robot} can only PICK from the other side.
Only one robot can PUT at a time, so you must coordiate with {other_robot}.

At the current round:
You can see these food items are on your reachable side:
{food_states}
{agent_state}
Think step-by-step about the task and {other_robot}'s response. Carefully check and correct them if they made a mistake. 
Improve your plans if given [Environment Feedback].
Respond very concisely but informatively, and do not repeat what others have said. Discuss with others to come up with the best plan.
Propose exactly one action for yourself at the **current** round, select from [Action Options].
End your response by either: 1) output PROCEED, if the plans require further discussion; 2) If everyone has made proposals and got approved, output the final plan, must strictly follow [Action Output Instruction]!
        """
        return agent_prompt

    def describe_obs(self, obs: EnvState):
        object_desp =  "[Scene description]\n" 
        for food in self.food_items:
            object_desp += self.describe_food_state(obs, food) + "\n"
             
        robot_desp = "The robots:\n"
        for robot_name, agent_name in self.robot_name_map.items():
            robot_desp += self.describe_robot_state(obs, robot_name) + "\n"

        full_desp = object_desp + robot_desp
        return full_desp 
    
    def get_task_feedback(self, llm_plan, pose_dict):
        task_feedback = ""
        obs = self.get_obs()
        
        for agent_name, action_str in llm_plan.action_strs.items():
            if 'PICK' in action_str and 'PUT' in action_str:
                task_feedback += f"{agent_name}'s can't PICK and PUT at same time.\n" 
            elif 'PUT' in action_str:
                objects = action_str.split('PUT')[1].strip().split(' ')
                if len(objects) == 2:
                    obj1 = objects[0]
                    obj2 = objects[1]
                    if obj1 not in self.recipe_order:
                        task_feedback += f"{obj1} is not in the recipe\n"
                    elif obj2 == "table":
                        continue 
                    else:
                        idx1 = self.recipe_order.index(obj1)
                        if idx1 == 0 and obj2 != 'cutting_board':
                            task_feedback += f"recipe says {obj1} must be put on cutting_board\n"
                        elif idx1 > 0:
                            if obj2 not in self.recipe_order:
                                task_feedback += f"{obj1} is not allowed to be put on {obj2}"
                            else:
                                idx2 = self.recipe_order.index(obj2)
                                if idx2 != idx1 - 1:
                                    task_feedback += f"recipe says {obj1} must be put on {self.recipe_order[idx1-1]}\n"
                                else:
                                    obj2_xpos = obs.objects[obj2].xpos
                                    if np.linalg.norm(obj2_xpos[:2] - self.cutting_board_pos[:2]) > 0.4:
                                        task_feedback += f"{obj2} is not on cutting_board\n"
            elif 'PICK' in action_str:
                obj = action_str.split('PICK')[1].strip()
                if obj in self.food_items:
                    contacts = obs.objects[obj].contacts
                    if 'cutting_board' in contacts or any([f in contacts for f in self.food_items]):
                        task_feedback += f"{agent_name} cannot PICK {obj}, it's already stacked\n"

        if all(['PUT' in action_str for action_str in llm_plan.action_strs.values()]):
            task_feedback += "only one robot can PUT at a time\n"
        
        
        return task_feedback
    
    def describe_robot_capability(self):
        return ""

    def describe_task_context(self):
        recipe_str = ", ".join(self.recipe_order)
        context = f"""
2 robots, Chad and Dave, together make a [{self.recipe_name}].
Food items must be stacked following this order: {recipe_str}, where bread_slice1 must be PUT on cutting_board. 
Chad can only reach right side of the table, and Dave can only reach left side of the table.
Both robots can PICK food items, or PUT an item atop something; only one robot can PUT at a time. 
At each round, given [Scene description] and [Environment feedback], use it to reason about the task and improve plans.
        """
        return context

    def get_contact(self):
        contacts = super().get_contact()
        # temp fix!  
        contacts["ur5e_suction"] = [c for c in contacts["ur5e_suction"] if c in self.food_items]
        contacts["humanoid"] = [c for c in contacts["humanoid"] if c in self.food_items]
        return contacts

    def chat_mode_prompt(self, chat_history: List[str] = []):
        return SANDWICH_CHAT_PROMPT 

    def central_plan_prompt(self):
        return SANDWICH_PLAN_PROMPT 

    def get_action_prompt(self) -> str:
        return SANDWICH_ACTION_SPACE
 
if __name__ == "__main__":
    env = MakeSandwichTask()
    obs = env.reset()
    print(env.describe_obs(obs))
    print(env.get_agent_prompt(obs, "Dave"))
    print(env.get_agent_prompt(obs, "Chad"))


