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
from rocobench.envs.constants import UR5E_ROBOTIQ_CONSTANTS, PANDA_CONSTANTS, UR5E_SUCTION_CONSTANTS

CABINET_TASK_OBJECTS=[
    "cup",
    "mug",
    "cabinet",
    "left_door_handle",
    "right_door_handle",
    "table_top",
]

CABINET_LEFT_RANGE = (
    np.array([-0.7, 0.5, 0.47]),
    np.array([-0.7, 0.5, 0.7]),
)
CABINET_RIGHT_RANGE = (
    np.array([1, 0.5, 0.47]),
    np.array([1.1, 0.5, 0.7]),
)

CABINET_ACTION_SPACE="""
[Action Options]
1) PICK <handle>.
2) OPEN <handle>.
3) PICK <object> PLACE <location>, <object> can be either cup or mug; PICK and PLACE is considered one single ACTION, i.e. you must always PICK and PLACE together
4) WAIT: stays at current position, choose WAIT to hold the door open.
<handle> must be either left or right door handle. Only OPEN a door after you already PICKed its handle, after you OPENed a door, must WAIT at the same spot to hold it open. 
<object> must be either mug or cup, <location> must be the correct coaster.

[Action Output Instruction]
Must first output 'EXECUTE\n', then give **exactly** one action per robot, put each on a new line.
Example: 'EXECUTE\nNAME Alice ACTION PICK mug PLACE mug_coaster\nNAME Bob ACTION WAIT\nNAME Chad ACTION OPEN left_door_handle\n'
"""

CABINET_TASK_CONTEXT="""3 robots, Alice, Bob, Chad together must take a mug and a cup out of a cabinet and place them on the correct coasters.
Both left and right cabinet doors should be OPENed and stays open before anything inside can be PICKed and PLACEed. Robots must coordinate to complete the task most efficiently while avoiding collision.
At each round, given 'Scene description' and 'Environment feedback', use it to reason about the task, and improve any previous plans. 
Each robot does **exactly** one ACTION per round, selected from only one of the above 4 options.
"""
CABINET_TASK_CHAT_PROMPT="""Robots discuss to find the best strategy. When each robot talk, it must first reflects on the task status, and its own capability. 
Carefully consider environment feedback and others' responses. It must coordinate with other robots' paths to avoid collision. They talk in order [Alice],[Bob],[Chad],[Alice],..., then, after reaching agreement, output an EXECUTE to summarize the plan, and stop talking.
Their chat history and plan are: """

CABINET_TASK_PLAN_PROMPT="""Reason about the task step-by-step, and find the best strategy to coordinate the robots. Carefully consider environment feedback to improve your plan. Output exactly one optimal ACTION for each robot at the current round.\n"""

CABINET_ACTION_SPACE_PATH="""
Options for <action>:
1) PICK <object> PATH <path>
2) PLACE <object> <location> PATH <path>, where <location> is (x,y,z), only PLACE mug or cup after it's PICKed, don't PLACE handles.
3) OPEN <handle> PATH <path>, specifies a path to open the door handle, the path must form a curve pointing away from the cabinet door, and move the handle only horizontally, the last <coord> should be target handle position.
4) WAIT PATH <path>, which keeps the robot still, and PATH is a repeated path of current position.
Only PICK an object if your gripper is empty, only PLACE object if it's already in your gripper. 
Only OPEN a door after you already PICKed its handle, after you OPENed a door, WAIT at the same spot to hold it open.
Each <path> must contain exactly four coordinates, e.g. PATH [(0.11,0.22,0.33),(0.28,0.22,0.33),(0.33,0.22,0.33),(0.40,0.22,0.33)]
Instruction on output format: first output 'EXECUTE\n', then give exactly one action per robot, put each on a new line.
Example: 'EXECUTE\nNAME Alice ACTION PICK mug PATH <path>\nNAME Bob ACTION WAIT <path>\nNAME Chad ACTION OPEN left_door_handle PATH <path>\n'
"""

class CabinetTask(MujocoSimEnv):
    def __init__( 
        self,
        filepath: str = "rocobench/envs/task_cabinet.xml",
        one_obj_each: bool = False,
        **kwargs,
    ):    
        self.robot_names = ["ur5e_robotiq", "panda", "ur5e_suction"] 
        self.robot_name_map = {
            "ur5e_robotiq": "Alice",
            "panda": "Bob",
            "ur5e_suction": "Chad",
        }
        self.robot_name_map_inv = {
            "Alice": "ur5e_robotiq",
            "Bob": "panda",
            "Chad": "ur5e_suction",
        }
        self.robots = dict()  

        super(CabinetTask, self).__init__(
            filepath=filepath, 
            task_objects=CABINET_TASK_OBJECTS,
            agent_configs=dict(
                ur5e_robotiq=UR5E_ROBOTIQ_CONSTANTS,
                panda=PANDA_CONSTANTS,
                ur5e_suction=UR5E_SUCTION_CONSTANTS,
            ),
            **kwargs
        )
        # remove base joint 
        robotiq_config = UR5E_ROBOTIQ_CONSTANTS.copy()
        # robotiq_config["ik_joint_names"].remove("ur5e_0_base_joint")
        # robotiq_config["all_joint_names"].remove("ur5e_0_base_joint")
        self.robots[
            self.robot_name_map["ur5e_robotiq"]
            ] = SimRobot(
            physics=self.physics,
            use_ee_rest_quat=False,
            **robotiq_config,
        )
        panda_config = PANDA_CONSTANTS.copy()
        # panda_config["ik_joint_names"].remove("panda_base_joint")
        # panda_config["all_joint_names"].remove("panda_base_joint")
        self.robots[
            self.robot_name_map["panda"]
        ] = SimRobot(
            physics=self.physics,
            use_ee_rest_quat=False,
            **panda_config,
        )
        suction_config = UR5E_SUCTION_CONSTANTS.copy()
        # suction_config["ik_joint_names"].remove("ur5e_1_base_joint")
        # suction_config["all_joint_names"].remove("ur5e_1_base_joint")
        self.robots[
            self.robot_name_map["ur5e_suction"]
        ] = SimRobot(
            physics=self.physics,
            use_ee_rest_quat=False,
            **suction_config,
        )

        self.align_threshold = 0.25
        self.coaster_pos = dict()
        for geom_name in ["mug_coaster", "cup_coaster"]:
            self.coaster_pos[geom_name] = self.physics.data.geom(geom_name).xpos.copy()
            self.coaster_pos[geom_name][2] += 0.25 # move up a bit
            self.coaster_pos[geom_name][0] += 0.09 # because cup_right grasp site is not at center
        self.open_pose = dict(
            left_door_handle=self.compute_open_pose("left_door_handle"),
            right_door_handle=self.compute_open_pose("right_door_handle"),
        )
        self.cabinet_pos = self.physics.data.body("cabinet").xpos.copy()

    def get_allowed_collision_pairs(self) -> List[Tuple[int, int]]:
        ret = []
        cabinet_ids = self.get_all_body_ids('cabinet') 
        for link_id in self.robots["Alice"].all_link_body_ids + self.robots["Bob"].all_link_body_ids + self.robots["Chad"].all_link_body_ids:
            for cabinet_id in cabinet_ids:
                ret.append((link_id, cabinet_id))

        table_id = self.physics.model.body("table").id 
        mug_id = self.physics.model.body("mug").id
        cup_id = self.physics.model.body("cup").id
        for cabinet_id in cabinet_ids:
            ret.append((cabinet_id, mug_id))
            ret.append((cabinet_id, cup_id))
        for _id in [mug_id, cup_id] + cabinet_ids:
            ret.append((table_id, _id))
        
        for _id1 in cabinet_ids:
            for _id2 in cabinet_ids:
                if _id1 != _id2:
                    ret.append((_id1, _id2))
        
        # for _id1 in self.robots["Chad"].all_link_body_ids:
        #     # ret.append((table_id, _id1))
        #     for _id2 in self.robots["Chad"].all_link_body_ids:
        #         if _id1 != _id2:
        #             ret.append((_id1, _id2))

        return ret
        

    def get_target_pos(self, agent_name, target_name) -> Optional[np.ndarray]:
        """ find target pos for PLACE, can only do coaster"""
        ret = None 
        robot_name = self.robot_name_map_inv[agent_name]
        if "coaster" in target_name:
            return self.coaster_pos.get(target_name, None)
        return ret 
         
    def get_graspable_objects(self):
        graspables = [
            "cup",
            "mug",
            "left_door_handle",
            "right_door_handle", 
        ]
        return dict(
            Alice=graspables,
            Bob=graspables,
            Chad=graspables,
        )
    
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
            return dict(x=(-1.3, 1.6), y=(-0.4, 1.5), z=(0.16, 1))
        
        elif robot_name == "panda" or robot_name == self.robot_name_map["panda"]:
            return dict(x=(-1.4, 1.4), y=(0, 1.5), z=(0.16, 1))
        
        elif robot_name == "ur5e_suction" or robot_name == self.robot_name_map["ur5e_suction"]:
            return dict(x=(-1.4, 1.6), y=(0, 1.5), z=(0.16, 1))
        
        else:
            raise NotImplementedError
    
    def sample_initial_scene(self):
        # sample locations of the cabinet
        range_idx = 0 # self.random_state.choice(2, size=1)[0]  TODO: fix the IK bugs when cabinet is on the right side
        low, high = CABINET_LEFT_RANGE if range_idx == 0 else CABINET_RIGHT_RANGE
        cab_pos = self.random_state.uniform(low, high) 
        if cab_pos[0] > 0:
            # rotate to face left side
            cab_quat = np.array([0.707, 0, 0, -0.707])
            quat = Quaternion(cab_quat)
            angle = self.random_state.uniform(low=-np.pi*0.45, high=-np.pi*0.55)
            new_quat = quat.rotate(
                Quaternion(axis=[0,0,1], angle=angle)
            )
        else:
            quat = Quaternion(
                np.array([0.707, 0, 0, 0.707])
            )
            angle = self.random_state.uniform(low=np.pi*0.45, high=np.pi*0.55)
            new_quat = quat.rotate(
                Quaternion(axis=[0,0,1], angle=angle)
            )
        new_cab_quat = np.array([new_quat.w, new_quat.x, new_quat.y, new_quat.z]) 
        self.reset_body_pose(
            body_name="cabinet",
            pos=cab_pos,
            quat=new_cab_quat,
        )  
        self.cabinet_pos = self.physics.data.body("cabinet").xpos.copy() 

        # then put mugs and cups inside the cabinet
        mug_pos = np.array([0.1, 0, 0.08]) + cab_pos
        self.reset_body_pose(
            body_name="mug",
            pos=mug_pos,
        )
        self.reset_qpos(
            jnt_name="mug_joint",
            pos=mug_pos, 
        )

        cup_pos = np.array([0.1, 0.15, -0.17]) + cab_pos 
        self.reset_body_pose(
            body_name="cup",
            pos=cup_pos,
        ) 
        self.reset_qpos(
            jnt_name="cup_joint",
            pos=cup_pos, 
        )
             
        self.physics.forward()
        self.physics.step(100)
        self.open_pose = dict(
            left_door_handle=self.compute_open_pose("left_door_handle"),
            right_door_handle=self.compute_open_pose("right_door_handle"),
        )
    
    def get_obs(self):
        obs = super().get_obs()
        for name in self.robot_names:
            assert getattr(obs, name) is not None, f"Robot {name} is not in the observation"
        return obs

    def compute_open_pose(self, door_name: str):
        physics = self.physics.copy(share_model=True)
        if door_name == "left_door_handle":
            qpos_slice = self.physics.named.data.qpos._convert_key("leftdoorhinge")
            if self.cabinet_pos[0] > 0:
                physics.data.qpos[qpos_slice.start] = -2.2
            else:
                physics.data.qpos[qpos_slice.start] = -2.6
        elif door_name == "right_door_handle":
            qpos_slice = self.physics.named.data.qpos._convert_key("rightdoorhinge")
            if self.cabinet_pos[0] > 0:
                physics.data.qpos[qpos_slice.start] = 1.8    
            else:
                physics.data.qpos[qpos_slice.start] = 2.6
        else:
            raise NotImplementedError
        physics.forward()
        desired_handle_pose = np.concatenate(
            [physics.data.body(door_name).xpos, physics.data.body(door_name).xquat]
        ) 
        # img = physics.render(camera_id="teaser")
        # plt.imshow(img)
        # plt.show()
        del physics 
        return desired_handle_pose
    
    def describe_cabinet(self, obs: EnvState, include_coords=True):
        object_desp = ""
        for jnt_name in ["leftdoorhinge", "rightdoorhinge"]:
            qpos_slice = self.physics.named.data.qpos._convert_key(jnt_name)
            jnt_qpos = self.physics.data.qpos[qpos_slice.start] # should be 1-dim!
            if "left" in jnt_name:
                # jnt range [-2.6, 0]
                door_state = "closed" if jnt_qpos > -2 else "open"
                object_desp += f"left door is {door_state}, " 
                handle = "left_door_handle"
                x,y,z = self.physics.data.body(handle).xpos
                x1,y1,z1 = self.open_pose["left_door_handle"][:3]
                
            else:
                # jnt range [0, 2.6]
                door_state = "closed" if jnt_qpos < 2 else "open"
                object_desp += f"right door is {door_state}, "
                handle = "right_door_handle"
                x,y,z = self.physics.data.body(handle).xpos
                x1,y1,z1 = self.open_pose["right_door_handle"][:3]
            
            if include_coords:
                object_desp += f"{handle} is at ({x:.1f}, {y:.1f}, {z:.1f}), "
            # if door_state == "closed":
            #     object_desp += f"to open it, move {handle} to ({x1:.2f}, {y1:.2f}, {z1:.2f})); "
        return object_desp

    def describe_cups(self, obs: EnvState, include_coords=True):
        object_desp = ""
        cab_pos = self.physics.data.body("cabinet").xpos 
        for obj in ["mug", "cup"]:
            obj_pos = self.physics.data.body(obj).xpos
            coaster_pos = self.coaster_pos[f"{obj}_coaster"] 
            if np.linalg.norm(obj_pos - cab_pos) < 0.35: 
                object_desp += f"{obj} is inside cabinet; "
            elif np.linalg.norm(obj_pos - coaster_pos) < self.align_threshold:
                object_desp += f"{obj} is on its coaster;"
            else:
                x, y, z = obj_pos
                if include_coords:
                    object_desp += f"{obj} is at ({x:.1f}, {y:.1f}, {z:.1f}); "
        return object_desp
    
    def describe_robot_state(self, obs, agent_name: str = "Alice", include_coords=True):
        robot_name = self.robot_name_map_inv[agent_name]
        robot_state = getattr(obs, robot_name)
        x, y, z = robot_state.ee_xpos
        contacts = robot_state.contacts 
        contacts = [con for con in contacts if con != "cabinet" and 'leftdoor' not in con and 'rightdoor' not in con]
        if len(contacts) == 0:
            obj = "nothing"
        else:
            obj = ",".join([c for c in contacts]) 
        if include_coords:
            robot_desp = f"{agent_name}'s gripper is at ({x:.1f} {y:.1f} {z:.1f}), holding {obj}, "
        else:
            robot_desp = f"{agent_name}'s gripper is holding {obj}, "
        return robot_desp

    def describe_obs(self, obs: EnvState):
        object_desp =  "[Scene description]\n"  
        object_desp += self.describe_cabinet(obs) + "\n"
        object_desp += self.describe_cups(obs) + "\n"  
        robot_desp = "\n".join([self.describe_robot_state(obs, name) for name in self.robot_name_map_inv.keys()])
        full_desp = object_desp + robot_desp
        return full_desp 
    
    def get_agent_prompt(self, obs: EnvState, agent_name: str):
        other_robots = [name for name in self.robots.keys() if name != agent_name]
        if self.cabinet_pos[0] < 0: # cabinet on table left side
            if agent_name == "Alice":
                reachables = "left_door_handle, mug, cup"
            elif agent_name == "Bob":
                reachables = "right_door_handle"
            elif agent_name == "Chad":
                reachables = "right_door_handle, mug, cup"
            else:
                raise NotImplementedError
        else: # cabinet on table right side
            if agent_name == "Alice":
                reachables = "right_door_handle, mug, cup"
            elif agent_name == "Bob":
                reachables = "left_door_handle, mug, cup"
            elif agent_name == "Chad":
                reachables = "left_door_handle"

        robot_desps = [self.describe_robot_state(obs, agent_name).replace(f"{agent_name}'s", "Your")]
        for name in other_robots:
            robot_desps.append(
                self.describe_robot_state(obs, name)
            )
        robot_desp = "\n".join(robot_desps)
        
        door_desp = self.describe_cabinet(obs)
        cup_desp = self.describe_cups(obs)

        agent_prompt = f"""
You are {agent_name}, collaborate with {', '.join(other_robots)} to pick a mug and a cup out of cabinet, and place them on correct coasters.
Both left and right cabinet doors should be OPENed and held open, while anything inside can be PICKed.
You must coordinate to complete the task most efficiently while avoiding collision.
You can only reach {reachables}.
At current round:
{door_desp}
{cup_desp}
{robot_desp}
Think step-by-step about the task and others' response. Carefully check and correct them if they made a mistake. 
Improve your plans if given [Environment Feedback].

When you respond, tell others about your goal and all constraints. Respond very concisely but informatively, and do not repeat what others have said.
Discuss together to come up with the best plan. Never forget you are {agent_name}! Never forget you can only reach {reachables}!
Propose exactly one action for yourself at the **current** round, select from [Action Options]. At least one robot should be acting, you can't all WAIT.
End your response by either: 1) output PROCEED, if the plans require further discussion, or 2) If everyone has made proposals and got approved, output EXECUTE and the final plan, must strictly follow [Action Output Instruction]!

"""
        return agent_prompt
    
    def get_reward_done(self, obs: EnvState):
        reward = 1
        done = True
        for obj in ["mug", "cup"]:
            obj_pos = self.physics.data.body(obj).xpos
            coaster_pos = self.coaster_pos[f"{obj}_coaster"]
            if np.linalg.norm(obj_pos - coaster_pos) > self.align_threshold:
                done = False
                reward = 0 
                break
        return reward, done
                
    def get_task_feedback(self, llm_plan, pose_dict):
        feedback = ""
        for agent_name, action_str in llm_plan.action_strs.items():
            if 'PICK mug' in action_str or 'PICK cup' in action_str:
                if 'PLACE' not in action_str:
                    feedback += f"{agent_name}'s ACTION must contain both PICK and PLACE"
            if self.cabinet_pos[0] < 0:
                if 'door_handle' in action_str and agent_name == "Chad":
                    feedback += f"{agent_name} cannot reach door"
            else:
                if 'door_handle' in action_str and agent_name == "Bob":
                    feedback += f"{agent_name} cannot reach door"
        if all(['WAIT' in action_str for action_str in llm_plan.action_strs.values()]):
            feedback += "At least one robot should be acting, you can't all WAIT."
        return feedback 

    def describe_robot_capability(self):
        return ""

    def describe_task_context(self):
        context = CABINET_TASK_CONTEXT
        return context

    def get_contact(self):
        contacts = super().get_contact()
        # temp fix! 
        for robot_name in ["ur5e_robotiq", "panda", "ur5e_suction"]:
            link_names = self.agent_configs[robot_name]['all_link_names'] + [robot_name]
            contacts[robot_name] = [c for c in contacts[robot_name] if c not in link_names]
        return contacts

    def chat_mode_prompt(self) -> str:
        return CABINET_TASK_CHAT_PROMPT

    def central_plan_prompt(self):
        return CABINET_TASK_PLAN_PROMPT

    def get_action_prompt(self) -> str:
        return CABINET_ACTION_SPACE

    def get_grasp_site(self, obj_name: str = "mug") -> Optional[str]:
        if obj_name in ["mug", "cup"]:
            if self.cabinet_pos[0] < 0: # cabinet on table left side
                return f"{obj_name}_right"
            else: # cabinet on table right side
                return f"{obj_name}_left"
        else:
            if obj_name in ["left_door_handle", "right_door_handle"]:
                return obj_name
            else:
                return None
 
    def get_waypoint_feedback(
        self, 
        waypoint_paths: Dict[str, List],
        display = False,
        save_img = False,
        img_path = 'test.jpg',
        ):
        """
        Give feedback to the robots about the waypoints they are going to visit.
        """
        bad_waypoints = defaultdict(list)
        for robot_name, path in waypoint_paths.items(): 
            for waypoint in path:
                if not self.check_reach_range(robot_name, waypoint):
                    bad_waypoints[robot_name].append(waypoint)
        summ = ""
        for name, waypoints in bad_waypoints.items():
            summ += f"{name}: {waypoints} \n"
        if display:
            print(summ)
            self.render_point_cloud = True 
            obs = self.get_obs() 
            path_ls = list(waypoint_paths.values())
            visualize_voxel_scene(obs.scene, path_pts=path_ls, path_colors=[], save_img=save_img, img_path=img_path)
        if summ == "":
            summ = "Reachability feedback: sucess."
        else:
            summ = "Reachability feedback: failed. These steps are beyond the robot's reach: \n" + summ
        return summ 
       

if __name__ == "__main__":
    env = CabinetTask()
    env.seed(2)
    obs = env.reset()
    print(env.describe_obs(obs))
    print(env.get_agent_prompt(obs, "Alice"))
    