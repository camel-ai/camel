import numpy as np
from copy import deepcopy
from transforms3d import quaternions
from dm_control.utils.inverse_kinematics import qpos_from_site_pose
from typing import Callable, List, Optional, Tuple, Union, Dict, Set, Any, FrozenSet

from rocobench.envs.env_utils import Pose
from rocobench.envs.base_env import MujocoSimEnv

class SimRobot:
    """ Stores the info for a single arm, doesn't store or change physics state """
    def __init__(
        self,
        physics: Any, # use only for gathering more arm infos
        name: str,
        all_joint_names: List[str],
        ik_joint_names: List[str],
        arm_joint_names: List[str],
        actuator_info: Dict[str, Any],
        all_link_names: List[str],
        arm_link_names: List[str], # 
        ee_link_names: List[str],
        base_joint: str,
        ee_site_name: str,
        grasp_actuator: str,
        weld_body_name: str = "rhand", # or gripper
        ee_rest_quat: np.ndarray = np.array([0, 1, 0, 0]),
        use_ee_rest_quat: bool = False,
    ):
        self.ik_joint_names = ik_joint_names
        self.ee_site_name = ee_site_name
        self.ee_link_names = ee_link_names
        self.ee_rest_quat = ee_rest_quat
        self.arm_link_names = arm_link_names
        self.use_ee_rest_quat = use_ee_rest_quat
        self.grasp_actuator = grasp_actuator
        self.grasp_idx_in_ctrl = physics.named.data.ctrl._convert_key(grasp_actuator)

        self.actuator_info = actuator_info
        self.weld_body_name = weld_body_name
        
        self.joint_ranges = []
        self.joint_idxs_in_qpos = [] 
        self.joint_idxs_in_ctrl = [] 
        for _name in ik_joint_names:
            qpos_slice = physics.named.data.qpos._convert_key(_name)
            assert int(qpos_slice.stop - qpos_slice.start) == 1, "Only support single joint for now"
            idx_in_qpos = qpos_slice.start
            self.joint_idxs_in_qpos.append(idx_in_qpos)
            self.joint_ranges.append(physics.model.joint(_name).range)

            assert _name in actuator_info, f"Joint {_name} not in actuator_info"
            actuator_name = actuator_info[_name]
            idx_in_ctrl = physics.named.data.ctrl._convert_key(actuator_name)
            self.joint_idxs_in_ctrl.append(idx_in_ctrl)
        
        
        self.ee_link_body_ids = []
        for _name in ee_link_names:
            try:
                link = physics.model.body(_name)
            except Exception as e:
                print(f'link name: {_name} does NOT have a body in env.physics.model.body')
                raise e
            self.ee_link_body_ids.append(link.id)
        
        self.all_link_body_ids = []
        for _name in all_link_names:
            try:
                link = physics.model.body(_name)
            except Exception as e:
                print(f'link name: {_name} does NOT have a body in env.physics.model.body')
                raise e
            self.all_link_body_ids.append(link.id)
        
        self.ee_link_pairs = set()
        for _id1 in self.ee_link_body_ids:
            for _id2 in self.ee_link_body_ids:
                if _id1 != _id2:
                    self.ee_link_pairs.add(
                        frozenset([_id1, _id2])
                    )
        self.collision_link_names = self.arm_link_names + self.ee_link_names
        self.collision_link_ids = [
            physics.model.body(_name).id for _name in self.collision_link_names
        ]
        self.home_qpos = physics.data.qpos[self.joint_idxs_in_qpos].copy()
    
    def set_home_qpos(self, env: MujocoSimEnv):
        env_cp = deepcopy(env)
        env_cp.reset()
        self.home_qpos = env_cp.physics.data.qpos[self.joint_idxs_in_qpos].copy()        
    
    def get_home_qpos(self) -> np.ndarray:
        return self.home_qpos.copy()

    def get_ee_pose(
        self,
        physics: Any,
    ) -> Pose:
        """ Get the pose of the end effector """
        ee_site = physics.data.site(self.ee_site_name)
        ee_pos = ee_site.xpos.copy()
        ee_quat = quaternions.mat2quat(
                    physics.named.data.site_xmat[self.ee_site_name].copy()
                )
        if self.use_ee_rest_quat:
            ee_quat = quaternions.qmult(ee_quat, self.ee_rest_quat)
        return Pose(position=ee_pos, orientation=ee_quat)
 
    def map_qpos_to_joint_ctrl(self, qpos: np.ndarray) -> Dict[str, np.ndarray]:
        """ Map the full qpos to the joint ctrl """
        assert len(qpos) > len(self.joint_idxs_in_qpos), f"qpos: {qpos} should be full state"
        desired_joint_qpos = qpos[self.joint_idxs_in_qpos]
        return {
            'ctrl_idxs': self.joint_idxs_in_ctrl,
            'ctrl_vals': desired_joint_qpos,
        }

    @property
    def grasp_idx(self) -> int:
        """ Get the grasp idx of the end effector """
        return self.grasp_idx_in_ctrl

    def get_grasp_ctrl_val(self, grasp: bool):
        # Hard code for now
        if self.grasp_actuator == 'adhere_gripper':
            grasp_ctrl_val = 0.0 if grasp else 0.0 # disabled!
        elif self.grasp_actuator == "panda_gripper_actuator":
            grasp_ctrl_val = 0 if grasp else 255 
        elif self.grasp_actuator == "adhere_hand":
            grasp_ctrl_val = 0 if grasp else 0
        elif self.grasp_actuator == "robotiq_fingers_actuator":
            grasp_ctrl_val = 255 if grasp else 0
        else:
            raise NotImplementedError(f"Grasp actuator {self.grasp_actuator} not implemented")
        return grasp_ctrl_val
        
    def solve_ik(
        self, 
        physics, 
        target_pos, 
        target_quat = None,
        tol=1e-14,
        max_resets=20,
        max_steps=300,
        allow_err=1e-2,
        ):
        """ solves single arm IK, helpful to check if a pose is achievable """
        
        physics_cp = physics.copy(share_model=True)
        joint_names = self.ik_joint_names
        qpos_idxs = self.joint_idxs_in_qpos
        target_quat = np.array([1, 0, 0, 0]) if target_quat is None else target_quat 

        def reset_fn(physics):
            model = physics.named.model 
            _lower, _upper = model.jnt_range[joint_names].T 
            curr_qpos = physics.named.data.qpos[joint_names]
            # deltas = (_upper - _lower) / 2
            # new_qpos = self.np_random.uniform(low=_lower, high=_upper)
            new_qpos = np.random.uniform(low=curr_qpos-0.5, high=curr_qpos + 0.5)
            new_qpos = np.clip(new_qpos, _lower, _upper)
            physics.named.data.qpos[joint_names] = new_qpos
            physics.forward()

        for i in range(max_resets):
            # print(f"Resetting IK {i}")
            if i > 0:
                reset_fn(physics_cp)
            result = qpos_from_site_pose(
                physics=physics_cp,
                site_name=self.ee_site_name,
                target_pos=target_pos,
                target_quat=target_quat,
                joint_names=joint_names,
                tol=tol,
                max_steps=max_steps,
                inplace=True,
            )
            if result.success:
                # check joint range
                _lower, _upper = physics_cp.named.model.jnt_range[joint_names].T
                qpos = result.qpos[qpos_idxs]
                in_range = True 
                assert len(qpos) == len(_lower) == len(_upper), f"Shape mismatch: qpos: {qpos}, _lower: {_lower}, _upper: {_upper}"
                for i, name in enumerate(joint_names):
                    if qpos[i] < _lower[i] - allow_err or qpos[i] > _upper[i] + allow_err:
                        # print(f"Joint {name} out of range: {_lower[i]} < {qpos[i]} < {_upper[i]}")
                        in_range = False 
                if in_range:
                    break 
        return result if result.success else None 
