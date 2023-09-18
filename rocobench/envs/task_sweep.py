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
from rocobench.envs.constants import UR5E_ROBOTIQ_CONSTANTS, UR5E_SUCTION_CONSTANTS, PANDA_CONSTANTS

SWEEP_TASK_OBJECTS=[
    "dustpan",
    "dustpan_handle",
    "broom",
    "broom_handle",
    "table_top",
    "red_cube",
    "blue_cube",
    "green_cube",
]
SWEEP_CUBE_NAMES=[
    "red_cube",
    "green_cube",
    "blue_cube",
]
CUBE_INIT_RANGE = (
    np.array([-1.1, 0.5, 0.2]),
    np.array([-0.6, 0.5, 0.2]),
)
SWEEP_FRONT_BOUND=0 # bounds robotiq gripper's y-dim
SWEEP_BROOM_OFFSET=0.432 # fix height offset for panda's broom handle, obs.panda.ee_xpos[2] - env.physics.data.site('broom_bottom').xpos[2]
SWEEP_DUSTPAN_HEIGHT=0.23
SWEEP_TASK_CONTEXT="""Alice is a robot holding a dustpan, Bob is a robot holding a broom, together they must sweep up all the cubes on the table.
To sweep up a cube, Alice must place the dustpan to one side, while Bob must sweep the cube from the other side into the dustpan.
At each round, given 'Scene description' and 'Environment feedback', use it to reason about the task, and improve any previous plans. Each robot does **exactly** one action per round.\n
"""

SWEEP_ACTION_SPACE="""
[Action Options]
1) MOVE <target>, <target> can only be a cube.
2) SWEEP <target>, this moves the groom so it pushes the <target> into dustpan, only Bob can SWEEP, Alice must WAIT in front of the same <target> cube when Bob SWEEP.
3) WAIT, stays at the current spot.
4) DUMP, only when there are one or more cubes in the dustpan, Alice can DUMP it into trash_bin.
Only SWEEP a cube after both robots MOVEed to the cube.
[Action Output Instruction]
Must first output 'EXECUTE\n', then give exactly one action per robot, put each on a new line.
Example#1: 'EXECUTE\nNAME Alice ACTION MOVE red_cube\nNAME Bob ACTION MOVE red_cube\n'
Example#2: 'EXECUTE\nNAME Alice ACTION WAIT\nNAME Bob ACTION SWEEP red_cube\n'
Example#3: 'EXECUTE\nNAME Alice ACTION DUMP\nNAME Bob ACTION MOVE green_cube\n'
"""

SWEEP_CHAT_PROMPT="""They discuss to find the best strategy. When each robot talk, it first reflects on the task status and its own capability. 
Carefully consider environment feedback and others' responses. Coordinate with other robots to always sweep the same cube.
They talk in order [Alice],[Bob],[Alice],..., then, after reaching agreement, plan exactly one action per robot, output an EXECUTE to summarize the plan, and stop talking.
Their entire chat history and the final plan are: """

SWEEP_PLAN_PROMPT="""
Plan one action for each robot at every round. Analyze the task status and plan for each robot based on its current capability. Make sure they focus on the same cube to sweep.
"""
class SweepTask(MujocoSimEnv):
    def __init__( 
        self,
        filepath: str = "rocobench/envs/task_sweep.xml",
        one_obj_each: bool = False,
        **kwargs,
    ):    
        self.robot_names = ["ur5e_robotiq", "panda"] 
        self.robot_name_map = {
            "ur5e_robotiq": "Alice",
            "panda": "Bob", 
        }
        self.robot_name_map_inv = {
            "Alice": "ur5e_robotiq",
            "Bob": "panda", 
        }
        self.robots = dict()  

        robotiq_config = UR5E_ROBOTIQ_CONSTANTS.copy()
        robotiq_config["all_link_names"].append("dustpan")
        robotiq_config["ee_link_names"].append("dustpan")

        panda_config = PANDA_CONSTANTS.copy()
        panda_config["all_link_names"].append("broom")
        panda_config["arm_link_names"].append("broom")
        panda_config["ee_link_names"].append("broom")

        self.cube_names = SWEEP_CUBE_NAMES

        super(SweepTask, self).__init__(
            filepath=filepath, 
            task_objects=SWEEP_TASK_OBJECTS,
            agent_configs=dict(
                ur5e_robotiq=robotiq_config,
                panda=panda_config, 
            ),
            **kwargs
        ) 
        
        self.robots[
            self.robot_name_map["ur5e_robotiq"]
            ] = SimRobot(
            physics=self.physics,
            use_ee_rest_quat=False,
            **robotiq_config,
        )
        self.robots[
            self.robot_name_map["panda"]
        ] = SimRobot(
            physics=self.physics,
            use_ee_rest_quat=False,
            **panda_config,
        )
         
        self.align_threshold = 0.1
        
    def get_task_feedback(self, llm_plan, pose_dict):
        feedback = ""
        if 'SWEEP' in llm_plan.action_strs.get('Bob', ''):
            if "WAIT" not in llm_plan.action_strs.get('Alice', ''):
                feedback = "Alice must WAIT while Bob SWEEPs"
        for agent_name, action_str in llm_plan.action_strs.items():
            if 'MOVE' in action_str and "cube" not in action_str:
                feedback = "MOVE target must be a cube, you can directly dump without moving to trash_bin"
        return feedback

    def get_target_pos(self, agent_name, target_name) -> Optional[np.ndarray]: 
        ret = None 
        robot_name = self.robot_name_map_inv[agent_name]

        if target_name in ["dustpan_bottom", "dustpan_rim", "broom_bottom"]:
            return self.physics.data.site(target_name).xpos.copy()

        elif 'dustpan' in target_name:
            return self.physics.data.site("dustpan_handle").xpos.copy() 
        
        elif 'broom' in target_name:
            return self.physics.data.site("broom_handle").xpos.copy()
        
        elif 'trash_bin' in target_name:
            return self.physics.data.site("trash_bin_top").xpos.copy()
        
        splitted = target_name.split("_")

        if len(splitted) == 2:
            try:
                ret = self.physics.data.site(target_name).xpos.copy() 
                if 'cube' in splitted:
                    if agent_name == "Alice":
                        cube_x = ret[1]
                        ret[1] = max(cube_x-0.4, SWEEP_FRONT_BOUND)
                        ret[2] = SWEEP_DUSTPAN_HEIGHT
                    else:
                        ret[1] += 0.3
                        ret[2] += SWEEP_BROOM_OFFSET
            except:
                pass
        return ret

    def get_target_quat(self, agent_name, target_name) -> Optional[np.ndarray]:
        ret = None
        robot_name = self.robot_name_map_inv[agent_name]
        if 'dustpan' in target_name:
            # sweeping 
            if agent_name == "Bob": 
                return np.array([0.5, -0.5, 0.50, 0.50])
            xmat = self.physics.data.site("dustpan_bottom").xmat.copy()
            return mat_to_quat(xmat.reshape(3,3))

        splitted = target_name.split("_")
        # applies to both cubes and transh bin
        if agent_name == "Bob": 
            ret = np.array([0.5, -0.5, 0.50, 0.50])
        else:
            ret = np.array([0.707, 0, 0, 0.707])
        if 'trash_bin' in target_name and agent_name == "Alice":
            # dumping quat
            ret = np.array([ 0.67, -0.22,  0.21,  0.67 ]) 
        return ret 

    def get_allowed_collision_pairs(self) -> List[Tuple[int, int]]:
        
        broom_id = self.physics.model.body("broom").id
        table_id = self.physics.model.body("table").id
        dustpan_ids = [self.physics.data.body("dustpan").id]
        trash_bin_ids = self.get_all_body_ids("trash_bin")

        ret = [(table_id, broom_id)]
        for id1 in trash_bin_ids:
            for id2 in trash_bin_ids:
                ret.append((id1, id2))
            ret.append((id1, table_id))
                
        for n in range(self.physics.model.nbody):
            body = self.physics.model.body(n)
            if body.rootid == dustpan_ids[0]:
                ret.append((body.id, broom_id))
                if body.name != "dustpan_bottom":
                    # only **allows** collision between cubes and and dustpan_bottom_up panel
                    dustpan_ids.append(body.id) 

        for link_id in self.robots["Alice"].all_link_body_ids + self.robots["Bob"].all_link_body_ids:
            ret.append((broom_id, link_id))
            for dustpan_id in dustpan_ids:
                ret.append((dustpan_id, link_id))

        dustpan_bottom_id = self.physics.data.body("dustpan_bottom").id

        for dustpan_id in dustpan_ids + [dustpan_bottom_id]:
            ret.append((dustpan_id, table_id))

        cube_ids = []
        for cube in self.cube_names:
            cube_id = self.physics.data.body(cube).id
            cube_ids.append(cube_id)
            ret.append((cube_id, dustpan_bottom_id))
            for _id in dustpan_ids:
                ret.append((cube_id, _id))
            ret.append((cube_id, broom_id))
            ret.append((cube_id, table_id))
            for bin_id in trash_bin_ids:
                ret.append((cube_id, bin_id))
        for cube_id in cube_ids:
            for cube_id2 in cube_ids:
                ret.append((cube_id, cube_id2))
        return ret


    def get_graspable_objects(self):
        graspables = self.cube_names
        return dict(
            Alice=graspables,
            Bob=graspables, 
        )

    def get_grasp_site(self, obj_name: str = "broom") -> Optional[str]:

        if 'broom' in obj_name:
            return "broom_handle"
        elif 'dustpan' in obj_name:
            return "dustpan_handle"
        else:
            return f"{obj_name}_top"

    def get_object_joint_name(self, obj_name: str) -> str:
        return f"{obj_name}_joint"

    def get_robot_name(self, agent_name):
        return self.robot_name_map_inv[agent_name]
    
    def get_agent_name(self, robot_name):
        return self.robot_name_map[robot_name]
    
    def get_robot_config(self) -> Dict[str, Dict[str, Any]]:
        return self.agent_configs
    
    def get_sim_robots(self) -> Dict[str, SimRobot]:
        """NOTE this is indexed by agent name, not actual robot names"""
        return self.robots

    def get_robot_reach_range(self, robot_name: str) -> Dict[str, Tuple[float, float]]:
        if robot_name == "ur5e_robotiq" or robot_name == self.robot_name_map["ur5e_robotiq"]:
            return dict(x=(-1.3, 1.6), y=(-0.4, 1.5), z=(0, 1))
        elif robot_name == "panda" or robot_name == self.robot_name_map["panda"]:
            return dict(x=(-1.3, 1.6), y=(0, 1.5), z=(0, 1))
        else:
            raise NotImplementedError
    
    def sample_initial_scene(self):
        # sample locations of the cabinet
        tosample_panels = []
        for n in range(self.physics.model.ngeom):
            geom = self.physics.model.geom(n)
            if 'panel' in geom.name:
                low = geom.pos - geom.size
                high = geom.pos + geom.size
                tosample_panels.append(
                    (low, high)
                )
        assert len(tosample_panels) >= len(self.cube_names), "Not enough panel positions to sample from"
        panel_idxs = self.random_state.choice(
            len(tosample_panels), 
            len(self.cube_names),
            replace=False
            )
        for _idx, cube_name in zip(panel_idxs, self.cube_names):
            low, high = tosample_panels[_idx]
            new_pos = self.random_state.uniform(low, high) 
            new_pos[2] = self.physics.data.body(cube_name).xpos[2] # height stays same!
            new_quat = Quaternion(
                axis=[0,0,1], 
                angle=self.random_state.uniform(low=0, high=2*np.pi)
                ) 
            new_quat = np.array([new_quat.w, new_quat.x, new_quat.y, new_quat.z]) 
            self.reset_body_pose(
                body_name=cube_name,
                pos=new_pos,
                quat=new_quat,
            )  
            self.reset_qpos(
                jnt_name=f"{cube_name}_joint",
                pos=new_pos,
                quat=new_quat,
            )
         
     
        self.physics.forward()
        # self.physics.step(100)
    
    def get_obs(self):
        contacts = self.get_contact()
        allow_objs = self.cube_names + ["broom", "dustpan"]
        contacts["ur5e_robotiq"] = [c for c in contacts["ur5e_robotiq"] if c in allow_objs]
        contacts["panda"] = [c for c in contacts["panda"] if c in allow_objs]

        obj_states = self.get_object_states(contact_dict=contacts)
        agent_states = dict()
        for agent_name, agent_constants in self.agent_configs.items():
            agent_state = self.get_agent_state(
                agent_constants, contact_dict=contacts
            ) 
            agent_states[agent_name] = agent_state
        kwargs = dict(
            objects=obj_states,
        )
        kwargs.update(agent_states)
        if self.render_point_cloud:
            point_cloud = self.get_point_cloud()
            kwargs['scene'] = point_cloud # NOTE: should include bboxes! 
        obs = EnvState(**kwargs)
         
        for name in self.robot_names:
            assert getattr(obs, name) is not None, f"Robot {name} is not in the observation"
        return obs
     
 
    def describe_obs(self, obs: EnvState):
        object_desp =  "[Scene description]\n" 
        on_table_cubes = []
        for name in self.cube_names:
            x,y,z = self.physics.data.site(name).xpos
            object_desp += self.describe_cube_state(obs, name) + "\n"
        # for sname in ["broom_bottom", "dustpan_rim"]:
        #     x,y,z = self.physics.data.site(sname).xpos
        #     obj = sname.split("_")[0]
        #     object_desp += f"{obj} is at ({x:.2f}, {y:.2f}, {z:.2f}), " 
        robot_desp = ""
        for robot_name, agent_name in self.robot_name_map.items():
            robot_desp += self.describe_robot_state(obs, agent_name=agent_name)+"\n" 
        
        full_desp = object_desp + robot_desp
        return full_desp 
    
    def describe_robot_state(self, obs, agent_name: str = "Alice"):
        robot_name = self.robot_name_map_inv.get(agent_name, None)
        assert robot_name is not None, f"Agent {agent_name} is not found in the task env!"
        robot_state = getattr(obs, robot_name)
        x, y, z = robot_state.ee_xpos
        contacts = robot_state.contacts
        if agent_name == 'Alice' or robot_name == 'ur5e_robotiq':
            obj = 'dustpan'
            site_name = 'dustpan_rim'
        else:
            obj = 'broom'
            site_name = 'broom_bottom'
        # dist_to_cubes = [(cube_name, np.linalg.norm(self.physics.data.site(cube_name).xpos - site_xpos)) for cube_name in on_table_cubes]
        # if len(dist_to_cubes) > 0:
        #     closest_cube = min(dist_to_cubes, key=lambda x: x[1])[0]
        #     robot_desp += f" and closest to {closest_cube} on the table,"
        # robot_desp += "\n"
        site_xpos = self.physics.data.site(site_name).xpos
        robot_desp = f"{agent_name}'s gripper is at ({x:.1f}, {y:.1f}, {z:.1f}), holding {obj}"
        for cube in self.cube_names:
            cube_xpos = self.physics.data.site(cube).xpos.copy()
            if cube_xpos[2] - site_xpos[2] < 0.1 and 'table' in obs.objects[cube].contacts:
                dist = np.linalg.norm(cube_xpos - site_xpos)
                robot_desp += f", in front of {cube} with distance: {dist:.2f}"
            
        return robot_desp
    
    def describe_cube_state(self, obs, cube_name: str = "red_cube") -> str: 
        assert cube_name in self.cube_names, f"Cube {cube_name} is not found in the task env!"
        cube_state = obs.objects[cube_name]
        x, y, z = cube_state.xpos.copy()
        cube_desp = f"{cube_name} is at ({x:.1f}, {y:.1f}, {z:.1f}), "
        contacts = cube_state.contacts 
        if 'dustpan_bottom' in contacts:
            cube_desp += f"inside dustpan; "
        elif 'trash_bin_bottom' in contacts:
            cube_desp += f"inside trash_bin; "
        else:
            cube_desp += f"on the table; "
        return cube_desp
    
    def get_agent_prompt(self, obs, agent_name) -> str:
        other_robot = [name for name in self.robots.keys() if name != agent_name][0]
        tool = "dustpan" if agent_name == 'Alice' else "broom"
        if agent_name == 'Alice':
            instruction = f"You must WAIT at the same cube while {other_robot} SWEEPs."
        else: 
            instruction = f"You must move to the same cube as {other_robot} before SWEEP."
        
        agent_state = self.describe_robot_state(obs, agent_name=agent_name)
        agent_state = agent_state.replace(f"{agent_name}'s", "Your")
        cube_states = [self.describe_cube_state(obs, cube_name) for cube_name in self.cube_names]
        cube_states = "\n".join(cube_states)

        agent_prompt = f"""
You are a robot called {agent_name}, and you are collaborating with {other_robot} to sweep up all the cubes on the table.
You hold a {tool}. 
To sweep up a cube, you and {other_robot} must get close to it by MOVE to opposite sides of the same cube. {instruction}
Talk with {other_robot} to coordinate together and decide which cube to sweep up first.
At the current round:
{agent_state}
{cube_states}
Think step-by-step about the task and {other_robot}'s response. Carefully check and correct them if they made a mistake. 
Improve your plans if given [Environment Feedback].
Never forget you are {agent_name}!
Respond very concisely but informatively, and do not repeat what others have said. Discuss with others to come up with the best plan.
Propose exactly one action for yourself at the **current** round, select from [Action Options].
End your response by either: 1) output PROCEED, if the plans require further discussion; 2) If everyone has made proposals and got approved, output the final plan, must strictly follow [Action Output Instruction]!
        """
        return agent_prompt

    def get_reward_done(self, obs): 
        all_dumped = True
        reward = 1
        trash_bin_xpos = self.physics.data.body("trash_bin_bottom").xpos
        for cube in self.cube_names:
            # TODO: handle the corner case where one cube is atop another cube which is inside the trash bin
            xpos = self.physics.data.body(cube).xpos
            if np.linalg.norm(xpos - trash_bin_xpos) > 0.2:
                all_dumped = False 
                reward = 0
                break 
        return reward, all_dumped

    def describe_robot_capability(self):
        return ""

    def describe_task_context(self):
        context = SWEEP_TASK_CONTEXT
        return context

    def get_contact(self):
        contacts = super().get_contact()
        # temp fix! 
        link_names = self.agent_configs["ur5e_robotiq"]['all_link_names'] + ['ur5e_robotiq']
        contacts["ur5e_robotiq"] = [c for c in contacts["ur5e_robotiq"] if c not in link_names]

        contacts["ur5e_robotiq"] = [c for c in contacts["ur5e_robotiq"] if "dustpan" not in c]
        contacts["ur5e_robotiq"].append("dustpan")

        contacts["panda"] = [c for c in contacts['panda'] if "broom" not in c]
        contacts["panda"] = [c for c in contacts['panda'] if c not in ["panda_right_finger", "panda_left_finger", "panda"] ]
        contacts["panda"].append("broom")

        return contacts

    def chat_mode_prompt(self, chat_history: List[str] = []):
        return SWEEP_CHAT_PROMPT

    def central_plan_prompt(self, chat_history: List[str] = []):
        return SWEEP_PLAN_PROMPT 


    def get_action_prompt(self) -> str:
        return SWEEP_ACTION_SPACE
 

if __name__ == "__main__":
    env = SweepTask(np_seed=10)
    obs = env.reset()
    print(env.describe_obs(obs))
    print(env.get_agent_prompt(obs, "Alice"))
    breakpoint()
    
    img=env.physics.render(camera_id="teaser", height=480, width=600)
    im = Image.fromarray(img)
    plt.imshow(img)
    plt.show()
    breakpoint()
    qpos_str ='2.29713e-08 -1.5708 -1.56377 1.57773 -1.56978 -1.5711 1.5708 0.284905 -0.0174837 0.264695 -0.264704 0.284905 -0.0173209 0.264824 -0.264998 -7.51154e-10 -1.57 0.000855777 1.57078 -1.57897 -1.56874 1.57001 -0.785298 0.0101015 0.0101007 1.15393 0.916272 0.674846 0.707121 0.00393568 0.00175927 0.70708 0.291037 0.108907 0.469551 -0.707118 -0.00508377 -0.00550396 -0.707056 0.151986 -0.151986 -0.532194 0.556831 -0.656483 0.529295 0.174891 -0.238563 0.665648 0.238563 0.665648 0.5 0.4 0.184784 1 4.40206e-17 7.02693e-19 4.76025e-17 0.869316 0.602884 0.184909 0.969597 -0.000376084 0.000355242 -0.244706'
    qpos = np.array([float(x) for x in qpos_str.split(' ')])
    env.physics.data.qpos[:] = qpos 
    env.physics.forward()
    obs = env.get_obs()
    print(env.describe_obs(obs))
    breakpoint()
    # print(print(env.get_system_prompt(mode="chat", obs=obs)))
    
    # env.render_all_cameras(save_img=1)
    print(env.get_system_prompt(mode="chat", obs=obs))
    # print('------------------')
    # print(env.get_system_prompt(mode="central", obs=obs))
    # qpos = env.physics.named.data.qpos
    
    # 
    # plt.show()
    # im.save('sorting_seed0.jpg')


