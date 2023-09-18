import numpy as np
from typing import Callable, List, Optional, Tuple, Union, Dict, Set, Any, FrozenSet
from dm_control.utils.inverse_kinematics import qpos_from_site_pose
from pydantic import dataclasses, validator
from rocobench.envs.env_utils import Pose
import matplotlib.pyplot as plt

@dataclasses.dataclass(frozen=False)
class LLMPathPlan:
    agent_names: List[str]
    ee_waypoints: Dict[str, List] # {robot_name: [ee_pose1, ee_pose2, ...]}
    tograsp: Dict[str, Union[Tuple, None]] # optionally, at the end of the path, target object (name, site) to grasp 
    inhand: Dict[str, Union[Tuple, None]] # optionally, at the start of the path, object (obj_name, site_name, joint_name) already in hand
    ee_targets: Dict #[str, np.ndarray]
    parsed_proposal: str # orginal proposal string
    action_strs: Dict[str, str] # action string for each robot
    return_home: Optional[Dict[str, bool]] # whether to return home after the path

    @validator("ee_waypoints")
    def check_waypoints_shape(cls, v):
        for robot_name, waypoints in v.items():
            for waypoint in waypoints:
                assert len(waypoint) == 7, "waypoint should be a 3-dim pos, 4-dim quat"
        return v
    
    @validator("ee_targets")
    def check_ee_targets_shape(cls, v):
        for robot_name, ee_pose in v.items():
            assert len(ee_pose) == 7, "ee_pose should be a 3-dim pos, 4-dim quat"
        return v
    
    @validator("ee_waypoints")
    def check_same_length(cls, v):
        assert len(set([len(waypoints) for waypoints in v.values()])) == 1, "all robot waypoints should have same length"
        return v
    
    @property
    def num_robots(self):
        return len(self.agent_name)

    def get_robot_action_str(self, name) -> str:
        return self.action_strs.get(name, "")
        
    def get_action_desp(self):
        return "\n".join(
            f"{robot_name}: {self.action_strs[robot_name]}" for robot_name in self.agent_names
        )
    
    @property
    def num_ee_waypoints(self):
        if len(self.ee_waypoints) == 0:
            return 0
        return len(self.ee_waypoints[self.agent_names[0]])
     
    def convert_waypoints_dict_to_list(self) -> List[Dict[str, Pose]]:
        """ converts from {name1: [pose1,...], name2: [pose1,...]} to [{name1: pose1, name2: pose1}, {name1: pose2, name2: pose2},...] """
        result = []
        for t in range(self.num_ee_waypoints):
            pose_dict = dict()
            for robot_name in self.agent_names:
                pose_arr = self.ee_waypoints[robot_name][t]
                pose_dict[robot_name] = Pose(position=pose_arr[:3], orientation=pose_arr[3:])
            result.append(pose_dict)
        return result

    def __post_init__(self):
        poses = dict()
        for name, target_arr in self.ee_targets.items():
            poses[name] = Pose(position=target_arr[:3], orientation=target_arr[3:]) 
        self.ee_target_poses = poses 
         
        self.ee_waypoint_poses = dict()
        for name, waypoints in self.ee_waypoints.items():
            self.ee_waypoint_poses[name] = [Pose(position=waypoint[:3], orientation=waypoint[3:]) for waypoint in waypoints]

        self.ee_waypoints_list = self.convert_waypoints_dict_to_list()

        self.path_3d_list = []
        for name in self.agent_names:
            waypts_3d = [pose.position for pose in self.ee_waypoint_poses[name]]
            waypts_3d = waypts_3d + [self.ee_targets[name][:3]]
            self.path_3d_list.append(waypts_3d)
        
        if self.return_home is None:
            self.return_home = {name: False for name in self.agent_names}
    
    def get_inhand_ids(self, physics) -> Dict[str, List[int]]:
        all_bodies = []
        for i in range(physics.model.nbody):
            all_bodies.append(physics.model.body(i))
        inhand = dict()
        for robot_name, info in self.inhand.items(): 
            inhand[robot_name] = []
            if info is not None:
                obj_body_name = info[0]
                root_id = physics.model.body(obj_body_name).id
                obj_ids = [root_id]
                obj_ids += [
                    body.id for body in all_bodies if body.rootid[0] == root_id
                ]
                inhand[robot_name] = obj_ids 
        
        return inhand 
    
    def get_allowed_collision_ids(self, physics) -> Dict[str, List[int]]:
        """ includes both inhand and tograsp bodies """
        inhand = self.get_inhand_ids(physics)
        
        all_bodies = []
        for i in range(physics.model.nbody):
            all_bodies.append(physics.model.body(i))
        for robot_name, info in self.tograsp.items():
            if info is not None:
                body_name = info[0]
                body_ids = [body.id for body in all_bodies if body.name == body_name]
                inhand[robot_name] += body_ids
        return inhand

    def get_inhand_obj_info(self, physics) -> Dict[str, Tuple]:
        """ returns obj_site_name, obj_joint_name """ 
        inhand_info = dict()
        for robot_name, _info in self.inhand.items():
            if _info is not None:
                assert len(_info) == 3, "inhand info should be a tuple of (obj_body_name, obj_site_name, obj_joint_name)"
            inhand_info[robot_name] = _info
        return inhand_info
