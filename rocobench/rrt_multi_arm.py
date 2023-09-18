import logging
import numpy as np
from time import time
from copy import deepcopy
import matplotlib.pyplot as plt
from transforms3d import euler, quaternions
from typing import Callable, List, Optional, Tuple, Union, Dict, Set, Any, FrozenSet

from dm_control.utils.inverse_kinematics import qpos_from_site_pose
from dm_control.utils.transformations import mat_to_quat, quat_to_euler, euler_to_quat 

from rocobench.rrt import direct_path, smooth_path, birrt, NearJointsUniformSampler, CenterWaypointsUniformSampler
from rocobench.envs import SimRobot 
from rocobench.envs.env_utils import Pose


class MultiArmRRT:
    """ Stores the info for a group of arms and plan all the combined joints together """
    def __init__(
        self,
        physics,
        robots: Dict[str, SimRobot] = {},
        robot_configs: Dict[str, Dict[str, Any]] = {},
        seed: int = 0,
        graspable_object_names: Optional[Union[Dict[str, str], List[str]]] = None,
        allowed_collision_pairs: List[Tuple[int, int]] = [],
        inhand_object_info: Optional[Dict[str, Tuple]] = None,
    ):
        self.robots = robots
        if len(robots) == 0:
            assert len(robot_configs) > 0, "No robot config is passed in"
            print(
                "Warning: No robot is passed in, will use robot_configs to create robots"
            )
        
            for robot_name, robot_config in robot_configs.items():
                self.robots[robot_name] = SimRobot(physics, **robot_config)
        self.physics = physics 
        self.np_random = np.random.RandomState(seed)
        
        self.all_joint_names = []
        self.all_joint_ranges = []
        self.all_joint_idxs_in_qpos = []
        self.all_collision_link_names = []
        self.inhand_object_info = dict()

        for name, robot in self.robots.items():
            self.all_joint_names.extend(
                robot.ik_joint_names
            ) 
            self.all_joint_idxs_in_qpos.extend(
                robot.joint_idxs_in_qpos
            )
            self.all_joint_ranges.extend(
                robot.joint_ranges
            )
            self.all_collision_link_names.extend(
                robot.collision_link_names
            )
        
        self.set_inhand_info(physics, inhand_object_info)


        self.joint_minmax = np.array([jrange for jrange in self.all_joint_ranges])
        self.joint_ranges = self.joint_minmax[:, 1] - self.joint_minmax[:, 0]

        # assign a list of allowed grasp ids to each robot
        graspable_name_dict = dict()
        for robot_name in self.robots.keys():
            if type(graspable_object_names) is dict:
                assert robot_name in graspable_object_names, f"robot_name: {robot_name} not in graspable_object_names"
                graspable_name_dict[robot_name] = graspable_object_names[robot_name]

            elif type(graspable_object_names) is list:
                graspable_name_dict[robot_name] = graspable_object_names

        self.allowed_collision_pairs = allowed_collision_pairs
        self.set_ungraspable(graspable_name_dict)
    
    def set_inhand_info(self, physics, inhand_object_info: Optional[Dict[str, Tuple]] = None):
        """ Set the inhand object info """
        self.inhand_object_info = dict()
        if inhand_object_info is not None:
            for name, robot in self.robots.items():
                self.inhand_object_info[name] = None
                
                obj_info = inhand_object_info.get(name, None)
                
                if obj_info is not None:
                    if 'rope' in obj_info[0] or 'CB' in obj_info[0]:
                        continue
                    assert len(obj_info) == 3, f"inhand obj info: {obj_info} should be a tuple of (obj_body_name, obj_site_name, obj_joint_name)"
                    body_name, site_name, joint_name = obj_info
                    try:
                        mjsite = physics.data.site(site_name)
                        qpos_slice = physics.named.data.qpos._convert_key(joint_name) 
                    except: 
                        print(f"Error: site_name: {site_name} joint_name {joint_name} not found in mujoco model")
                        breakpoint() 
                    self.inhand_object_info[name] = (body_name, site_name, joint_name, (qpos_slice.start, qpos_slice.stop))
        return 
 
    
    def set_ungraspable(
        self, 
        graspable_object_dict: Optional[Dict[str, List[str]]]
    ):
        """ Find all sim objects that are not graspable """
        
        all_bodies = []
        for i in range(self.physics.model.nbody):
            all_bodies.append(self.physics.model.body(i))

        # all robot link bodies are ungraspable:
        ungraspable_ids = [0]  # world
        for name, robot in self.robots.items():
            ungraspable_ids.extend(
                robot.collision_link_ids
            )
        # append all children of ungraspable body
        ungraspable_ids += [
            body.id for body in all_bodies if body.rootid[0] in ungraspable_ids
        ]
 
        if graspable_object_dict is None or len(graspable_object_dict) == 0:
            graspable = set(
                [body.id for body in all_bodies if body.id not in ungraspable_ids]
            )
            ungraspable = set(ungraspable_ids)
            self.graspable_body_ids = {name: graspable for name in self.robots.keys()}
            self.ungraspable_body_ids = {name: ungraspable for name in self.robots.keys()}
        else: 
            # in addition to robots, everything else would be ungraspable if not in this list of graspable objects
            self.graspable_body_ids = {}
            self.ungraspable_body_ids = {}
            for robot_name, graspable_object_names in graspable_object_dict.items():
                graspable_ids = [
                    body.id for body in all_bodies if body.name in graspable_object_names
                ]
                graspable_ids += [
                    body.id for body in all_bodies if body.rootid[0] in graspable_ids
                ]
                self.graspable_body_ids[robot_name] = set(graspable_ids)
                robot_ungraspable = ungraspable_ids.copy()
                robot_ungraspable += [
                    body.id for body in all_bodies if body.rootid[0] not in graspable_ids
                ]
                self.ungraspable_body_ids[robot_name] = set(ungraspable_ids)
            # breakpoint()

    def forward_kinematics_all(
        self,
        q: np.ndarray,
        physics = None,
        return_ee_pose: bool = False,
    ) -> Optional[Dict[str, Pose]]:
        if physics is None:
            physics = self.physics.copy(share_model=True)
        physics = physics.copy(share_model=True)
        
        # transform inhand objects!
        obj_transforms = dict()
        for robot_name, obj_info in self.inhand_object_info.items():
            gripper_pose = self.robots[robot_name].get_ee_pose(physics)
            if obj_info is not None:
                body_name, site_name, joint_name, (start, end) = obj_info
                obj_quat = mat_to_quat(
                    physics.data.site(site_name).xmat.reshape((3, 3))
                )
                obj_pos = physics.data.site(site_name).xpos
                rel_rot = quaternions.qmult( 
                    quaternions.qinverse(
                        gripper_pose.orientation
                        ),
                    obj_quat,
                    )
                rel_pos = obj_pos - gripper_pose.position 
                obj_transforms[robot_name] = (rel_pos, rel_rot)
            else:
                obj_transforms[robot_name] = None
        
        physics.data.qpos[self.all_joint_idxs_in_qpos] = q
        physics.forward()

        ee_poses = {}
        for robot_name, robot in self.robots.items():
            ee_poses[robot_name] = robot.get_ee_pose(physics)
        
        # also transform inhand objects!
        for robot_name, obj_info in self.inhand_object_info.items():
            if obj_info is not None:
                body_name, site_name, joint_name, (start, end) = obj_info
                rel_pos, rel_rot = obj_transforms[robot_name] 
                new_ee_pos = ee_poses[robot_name].position
                new_ee_quat = ee_poses[robot_name].orientation 
                target_pos = new_ee_pos + rel_pos 
                target_quat = quaternions.qmult(new_ee_quat, rel_rot) 
                result = self.solve_ik(
                    physics,
                    site_name,
                    target_pos,
                    target_quat,
                    joint_names=[joint_name], 
                    max_steps=300,
                    inplace=0,   
                    )
                if result is not None:
                    new_obj_qpos = result.qpos[start:end]
                    physics.data.qpos[start:end] = new_obj_qpos
                    physics.forward()
        if return_ee_pose:
            return ee_poses
        # physics.step(10) # to make sure the physics is stable
        return physics # a copy of the original physics object 
 
    
    def check_joint_range(
        self, 
        physics,
        joint_names,
        qpos_idxs,
        ik_result,
        allow_err=0.03,
    ) -> bool:
        _lower, _upper = physics.named.model.jnt_range[joint_names].T
        qpos = ik_result.qpos[qpos_idxs]
        assert len(qpos) == len(_lower) == len(_upper), f"Shape mismatch: qpos: {qpos}, _lower: {_lower}, _upper: {_upper}"
        for i, name in enumerate(joint_names):
            if qpos[i] < _lower[i] - allow_err or qpos[i] > _upper[i] + allow_err:
                # print(f"Joint {name} out of range: {_lower[i]} < {qpos[i]} < {_upper[i]}")
                return False 
        return True

    def solve_ik(
        self,
        physics,
        site_name,
        target_pos,
        target_quat,
        joint_names, 
        tol=1e-14,
        max_steps=300,
        max_resets=20,
        inplace=True, 
        max_range_steps=0,
        qpos_idxs=None,
        allow_grasp=True,
        check_grasp_ids=None,
        check_relative_pose=False
    ):
        physics_cp = physics.copy(share_model=True)
        
        def reset_fn(physics):
            model = physics.named.model 
            _lower, _upper = model.jnt_range[joint_names].T
            
            curr_qpos = physics.named.data.qpos[joint_names]
            # deltas = (_upper - _lower) / 2
            # new_qpos = self.np_random.uniform(low=_lower, high=_upper)
            new_qpos = self.np_random.uniform(low=curr_qpos-0.5, high=curr_qpos + 0.5)
            new_qpos = np.clip(new_qpos, _lower, _upper)
            physics.named.data.qpos[joint_names] = new_qpos
            physics.forward()

        for i in range(max_resets):
            # print(f"Resetting IK {i}")
            if i > 0:
                reset_fn(physics_cp)
                
            result = qpos_from_site_pose(
                physics=physics_cp,
                site_name=site_name,
                target_pos=target_pos,
                target_quat=target_quat,
                joint_names=joint_names,
                tol=tol,
                max_steps=max_steps,
                inplace=True,
            )
            need_reset = False
            if result.success:
                in_range = True 
                collided = False
                if qpos_idxs is not None:
                    in_range = self.check_joint_range(physics_cp, joint_names, qpos_idxs, result)
                    ik_qpos = result.qpos.copy()
                    _low, _high = physics_cp.named.model.jnt_range[joint_names].T
                    ik_qpos[qpos_idxs] = np.clip(
                        ik_qpos[qpos_idxs], _low, _high
                    )
                    ik_qpos = ik_qpos[self.all_joint_idxs_in_qpos]
                    # print('checking collision on IK result: step {}'.format(i))
                    collided = self.check_collision(
                        physics=physics_cp,
                        robot_qpos=ik_qpos,
                        check_grasp_ids=check_grasp_ids,
                        allow_grasp=allow_grasp,
                        check_relative_pose=check_relative_pose,
                        )

                need_reset = (not in_range) or collided

            else:
                need_reset = True
            if not need_reset:
                break
        # img = physics_cp.render(camera_id='teaser', height=400, width=400)
        # plt.imshow(img)
        # plt.show()

        return result if result.success else None

    def inverse_kinematics_all(
        self,
        physics,
        ee_poses: Dict[str, Pose],
        inplace=False, 
        allow_grasp=True, 
        check_grasp_ids=None,
        check_relative_pose=False,
    ) -> Dict[str, Union[None, np.ndarray]]:

        if physics is None:
            physics = self.physics
        physics = physics.copy(share_model=True)
        results = dict() 
        for robot_name, target_ee in ee_poses.items():
            assert robot_name in self.robots, f"robot_name: {robot_name} not in self.robots"
            robot = self.robots[robot_name]
            pos = target_ee.position 
            quat = target_ee.orientation
            if robot.use_ee_rest_quat:
                quat = quaternions.qmult(
                    quat, robot.ee_rest_quat
                ), # TODO 
            # print(robot.ee_site_name, pos, quat, robot.joint_names)
            qpos_idxs = robot.joint_idxs_in_qpos     
            result = self.solve_ik(
                physics=physics,
                site_name=robot.ee_site_name,
                target_pos=pos,
                target_quat=quat,
                joint_names=robot.ik_joint_names,
                tol=1e-14,
                max_steps=300,
                inplace=inplace,  
                qpos_idxs=qpos_idxs,
                allow_grasp=allow_grasp, 
                check_grasp_ids=check_grasp_ids,
                check_relative_pose=check_relative_pose,
            )
            if result is not None:
                result_qpos = result.qpos[qpos_idxs].copy()
                _lower, _upper = physics.named.model.jnt_range[robot.ik_joint_names].T
                result_qpos = np.clip(result_qpos, _lower, _upper)
                results[robot_name] = (result_qpos, qpos_idxs) 
            else:
                results[robot_name] = None
        return results      


    def ee_l2_distance(
        self, 
        q1: np.ndarray, 
        q2: np.ndarray, 
        orientation_factor: float = 0.2
    ) -> float: 
        pose1s = self.forward_kinematics_all(q1, return_ee_pose=True) # {robotA: Pose1, robotB: Pose1}
        pose2s = self.forward_kinematics_all(q2, return_ee_pose=True) # {robotA: Pose2, robotB: Pose2}
        assert pose1s is not None and pose2s is not None
        dist = 0

        # compute pair-wise distance between each robot's Pose1 and Pose2
        for robot_name in pose1s.keys():
            pose1 = pose1s[robot_name]
            pose2 = pose2s[robot_name]
            dist += pose1.distance(pose2, orientation_factor=orientation_factor)
        return dist

    def extend_ee_l2(
        self, 
        q1: np.ndarray, 
        q2: np.ndarray, 
        resolution: float = 0.006
    ) -> List[np.ndarray]:
        dist = self.ee_l2_distance(q1, q2)
        if dist == 0:
            return []
        step = resolution / dist
        return [(q2 - q1) * np.clip(t, 0, 1) + q1 for t in np.arange(0, 1 + step, step)]

    def allow_collision_pairs(
        self,
        physics: Any,
        allow_grasp: bool = False,
        check_grasp_ids: Optional[Dict[str, List]] = None,
    ) -> Set[FrozenSet[int]]:
        
        """ Get the allowed collision pairs """ 
        allowed = set()
        for robot_name, robot in self.robots.items():
            # add the robot's set to the allowed set:
            allowed.update( 
                robot.ee_link_pairs
            )
        for id_pair in self.allowed_collision_pairs:
            allowed.add(frozenset([id_pair[0], id_pair[1]]))

        if allow_grasp:
            # if the robot is in contact with some allowed objects, allow the collision  
            for robot_name, robot in self.robots.items():
                assert robot_name in self.graspable_body_ids, f"Robot {robot_name} not found in graspable_body_ids"
                graspable_ids = self.graspable_body_ids[robot_name]
                
                if check_grasp_ids is not None:
                    assert robot_name in check_grasp_ids, f"Robot {robot_name} not found in check_grasp_ids"
                    # only find the desired grasp_id to allow collision
                    graspable_ids = check_grasp_ids[robot_name]
                
                for ee_id in robot.ee_link_body_ids:
                    for _id in graspable_ids: 
                        allowed.add(
                            frozenset([ee_id, _id])
                            ) 
                # dangerous: allow collision between all arm links and the object
                for arm_id in robot.collision_link_ids:
                    for _id in graspable_ids:
                        # if _id == 40: # broom in sweeping task
                        allowed.add(
                            frozenset([arm_id, _id])
                        )
        return allowed 

    def get_collided_links(
        self,
        qpos: Optional[np.ndarray] = None,
        physics = None,
        allow_grasp: bool = False,
        check_grasp_ids: Optional[Dict[str, List]] = None,
        verbose: bool = False,
        show: bool = False,
    ) -> List[str]:
        """ Get the collided links """ 
        if physics is None:
            physics = self.physics.copy(share_model=True)    
        physics = self.forward_kinematics_all(physics=physics, q=qpos, return_ee_pose=False) 
        
        robot_collison_ids = [physics.model.body(link_name).id for link_name in self.all_collision_link_names]
        # NOTE: cant allow grasped object to collide with other objects in the env
        allowed_collisions = self.allow_collision_pairs(
            physics, allow_grasp=allow_grasp, check_grasp_ids=check_grasp_ids
            ) # robot-to-object 
        collided_id1 = physics.model.geom_bodyid[physics.data.contact.geom1].copy()
        collided_id2 = physics.model.geom_bodyid[physics.data.contact.geom2].copy() 
        

        if len(allowed_collisions) > 0:
            undesired_mask = np.ones_like(collided_id1).astype(bool)
            for idx in range(len(collided_id1)):
                body1 = collided_id1[idx]
                body2 = collided_id2[idx]
                if frozenset([body1, body2]) in allowed_collisions:
                    undesired_mask[idx] = False
            collided_id1 = collided_id1[undesired_mask]
            collided_id2 = collided_id2[undesired_mask]
        
        # TODO: if an object is being grasped, don't allow it to collide with other objects
        # if allow_grasp and check_grasp_ids is not None:
        #     
        #     for robot_name, grasp_id in check_grasp_ids.items():
        #         graspable_ids = check_grasp_ids[robot_name]
        #         robot_collison_ids.extend(graspable_ids)
        all_pairs = set(zip(collided_id1, collided_id2))
        bad_pairs = set()
        for pair in all_pairs:
            # if pair[0] in robot_collison_ids or pair[1] in robot_collison_ids:
            root1 = physics.model.body(pair[0]).rootid 
            root2 = physics.model.body(pair[1]).rootid
            bad_pairs.add(
                (physics.model.body(root1).name, physics.model.body(root2).name)
            )
            # if (pair[0] == 62 and pair[1] == 64) or (pair[0] == 64 and pair[1] == 62):
            #     breakpoint()
        all_ids = set(collided_id1).union(set(collided_id2)) # could contain both object-to-object, robot-to-robot, etc
       
        # undesired_ids = set(robot_collison_ids).intersection(all_ids) 
        undesired_ids = all_ids
        
        # dist = np.linalg.norm(
        #     physics.data.site('robotiq_ee').xpos  - physics.data.site('panda_ee').xpos
        #     )
        # if dist > 0.8 or dist < 0.6:
        #     bad_pairs.add((dist, dist))

        # if a link is on robot AND it's in contact with something Not in the allowed_collisions
        # if np.linalg.norm(physics.data.body('red_cube').xpos  - physics.data.body('dustpan').xpos) < 0.1:
        # if 54 in collided_id1 or 54 in collided_id2:
        if len(undesired_ids) > 0 and show:
            print(bad_pairs)
            img_arr = np.concatenate(
                [
                     physics.render(camera_id=i, height=400, width=400,) for i in range(3)
                ]
                , axis=1
            )
            plt.imshow(img_arr)
            plt.show()
            
            qpos_str = " ".join(physics.data.qpos.astype(str))
            print(f"<key name='rrt_check' qpos='{qpos_str}'/>")
            breakpoint()
           
        return bad_pairs
    
    def check_relative_pose(
        self, 
        qpos: Optional[np.ndarray] = None,
        physics = None,
    ):  
        # get ee poses from qpos?
        poses_dict = self.forward_kinematics_all(q=qpos, physics=physics, return_ee_pose=True) # {robotA: Pose1, robotB: Pose1}
        alice_quat = np.array([7.07106781e-01, 1.73613722e-16, 1.69292055e-16, 7.07106781e-01])
        bob_quat = np.array([7.07106781e-01, 1.73613722e-16, 1.69292055e-16, 7.07106781e-01])
        rot_align = np.allclose(alice_quat, poses_dict['Alice'].orientation) and \
            np.allclose(bob_quat, poses_dict['Bob'].orientation)

        dist = np.linalg.norm(poses_dict["Alice"].position - poses_dict["Bob"].position)
        dist_align = 0.1 <= dist <= 0.4
        # print("===== dist", dist, dist_align)
        # print("===== rot_align", rot_align,  poses_dict['Alice'].orientation, poses_dict['Bob'].orientation)
        return 1 and dist_align
             

    def check_collision(
        self,
        robot_qpos: Optional[np.ndarray] = None,
        physics = None,
        allow_grasp: bool = False,
        check_grasp_ids: Optional[Dict[str, int]] = None,
        verbose: bool = False,
        check_relative_pose: bool = False,
        show: bool = False,
    ) -> bool: 
        
        if check_relative_pose:
            passed = self.check_relative_pose(qpos=robot_qpos, physics=physics)
            if not passed:
                return True
        collided_links = self.get_collided_links(
            qpos=robot_qpos, 
            physics=physics,
            allow_grasp=allow_grasp,           
            check_grasp_ids=check_grasp_ids,
            verbose=verbose,
            show=show,
        ) 
        # if len(collided_links) > 0: 
        #     print("collided_link_ids", collided_links)
        #     for link_id in collided_links:
        #         link_name = self.physics.model.body(link_id).name
        #         print("collided_link_name", link_name)
        #     return True
        # print("collided_link_ids", collided_links)
        # for i in collided_links:
        #     print(self.physics.model.body(i).name)
        # if len(collided_links) > 0: 
        #     physics.named.data.qpos[self.all_joint_names] = robot_qpos
        #     physics.forward()
        #     img = physics.render(camera_id='teaser', height=400, width=400,)
        #     plt.imshow(img)
        #     plt.show()
        #     breakpoint()
        bad = len(collided_links) > 0
        
        # breakpoint()
        return bad 


    
    def plan(
        self, 
        start_qpos: np.ndarray,  # can be either full length or just the desired qpos for the joints 
        goal_qpos: np.ndarray,
        init_samples: Optional[List[np.ndarray]] = None,
        allow_grasp: bool = False,
        check_grasp_ids: Optional[Dict[str, int]] = None,
        skip_endpoint_collision_check: bool = False,
        skip_direct_path: bool = False,
        skip_smooth_path: bool = False,
        timeout: int = 200,
        check_relative_pose: bool = False,
    ) -> Tuple[Optional[List[np.ndarray]], str]:

        if len(start_qpos) != len(goal_qpos):
            return None, "RRT failed: start and goal configs have different lengths."
        if len(start_qpos) != len(self.all_joint_idxs_in_qpos):
            start_qpos = start_qpos[self.all_joint_idxs_in_qpos]
        if len(goal_qpos) != len(self.all_joint_idxs_in_qpos):
            goal_qpos = goal_qpos[self.all_joint_idxs_in_qpos]
  
        def collision_fn(q: np.ndarray, show: bool = False):
            return self.check_collision(
                robot_qpos=q,
                physics=self.physics,
                allow_grasp=allow_grasp,           
                check_grasp_ids=check_grasp_ids,  
                check_relative_pose=check_relative_pose,
                show=show,
                # detect_grasp=False, TODO?
            )
        if not skip_endpoint_collision_check:
            if collision_fn(start_qpos, show=1):
                # print("RRT failed: start qpos in collision.")
                return None, f"ReasonCollisionAtStart_time0_iter0"
            elif collision_fn(goal_qpos, show=1): 
                # print("RRT failed: goal qpos in collision.")
                return None, "ReasonCollisionAtGoal_time0_iter0"
        paths, info = birrt(
                start_conf=start_qpos,
                goal_conf=goal_qpos,
                distance_fn=self.ee_l2_distance,
                sample_fn=CenterWaypointsUniformSampler(
                    bias=0.05,
                    start_conf=start_qpos,
                    goal_conf=goal_qpos,
                    numpy_random=self.np_random,
                    min_values=self.joint_minmax[:, 0],
                    max_values=self.joint_minmax[:, 1],
                    init_samples=init_samples,
                ),
                extend_fn=self.extend_ee_l2,
                collision_fn=collision_fn,
                iterations=800,
                smooth_iterations=200,
                timeout=timeout,
                greedy=True,
                np_random=self.np_random,
                smooth_extend_fn=self.extend_ee_l2,
                skip_direct_path=skip_direct_path,
                skip_smooth_path=skip_smooth_path, # enable to make sure it passes through the valid init_samples 
            )
        if paths is None:
            return None, f"RRT failed: {info}"
        return paths, f"RRT succeeded: {info}"
 
    def plan_splitted(
        self, 
        start_qpos: np.ndarray,  # can be either full length or just the desired qpos for the joints 
        goal_qpos: np.ndarray,
        init_samples: Optional[List[np.ndarray]] = None,
        allow_grasp: bool = False,
        check_grasp_ids: Optional[Dict[str, int]] = None,
        skip_endpoint_collision_check: bool = False,
        skip_direct_path: bool = False,
        skip_smooth_path: bool = False,
        timeout: int = 200,
        check_relative_pose: bool = False,
    ) -> Tuple[Optional[List[np.ndarray]], str]:
       
        all_paths, all_info = [], []
        duration = 0 
        iteration = 0
        def collision_fn(q: np.ndarray, show: bool = False):
            return self.check_collision(
                robot_qpos=q,
                physics=self.physics,
                allow_grasp=allow_grasp,           
                check_grasp_ids=check_grasp_ids,  
                check_relative_pose=check_relative_pose,
                show=show,
                # detect_grasp=False, TODO?
            )
        
        # still try direct path first 
        if not skip_direct_path:
            start_time = time()
            path = direct_path(start_qpos, goal_qpos, self.extend_ee_l2, collision_fn)
            if path is not None:
                return path, f"ReasonDirect_time{time() - start_time}_iter1"

        
        if not skip_endpoint_collision_check:
            if collision_fn(goal_qpos, show=1): 
                print("RRT failed: goal qpos in collision.")
                return None, "ReasonCollisionAtGoal_time0_iter0"
            
            valid_init_samples = []
            for i, interm_goal_qpos in enumerate(init_samples):
                if not collision_fn(interm_goal_qpos, show=0): 
                    valid_init_samples.append(interm_goal_qpos)
                # return None, "RRT failed: goal qpos in collision."
                # omit this waypoint and try planning with pruned init_sample 
            print(f"Given waypoints: {len(init_samples)}, valid: {len(valid_init_samples)} points")
            init_samples = valid_init_samples

        for i, interm_goal_qpos in enumerate(init_samples[::-1] + [goal_qpos]):
            interm_start_qpos = start_qpos if i == 0 else init_samples[::-1][i-1]
            print("planning interm_start_qpos", i)
            if len(interm_start_qpos) != len(interm_goal_qpos):
                return None, "RRT failed: start and goal configs have different lengths."
            if len(interm_start_qpos) != len(self.all_joint_idxs_in_qpos):
                interm_start_qpos = interm_start_qpos[self.all_joint_idxs_in_qpos]
            if len(interm_goal_qpos) != len(self.all_joint_idxs_in_qpos):
                interm_goal_qpos = interm_goal_qpos[self.all_joint_idxs_in_qpos]
  
        
            if not skip_endpoint_collision_check:
                if collision_fn(interm_start_qpos):
                    return None, f"ReasonCollisionAtStart_time0_iter0"
                elif collision_fn(interm_goal_qpos): 
                    return None, f"ReasonCollisionAtGoal_time0_iter0"
                    
            paths, info = birrt(
                    start_conf=interm_start_qpos,
                    goal_conf=interm_goal_qpos,
                    distance_fn=self.ee_l2_distance,
                    sample_fn=CenterWaypointsUniformSampler(
                        bias=0.05,
                        start_conf=interm_start_qpos,
                        goal_conf=interm_goal_qpos,
                        numpy_random=self.np_random,
                        min_values=self.joint_minmax[:, 0],
                        max_values=self.joint_minmax[:, 1],
                        init_samples=[],
                    ),
                    extend_fn=self.extend_ee_l2,
                    collision_fn=collision_fn,
                    iterations=800,
                    smooth_iterations=200,
                    timeout=timeout,
                    greedy=True,
                    np_random=self.np_random,
                    smooth_extend_fn=self.extend_ee_l2,
                    skip_direct_path=skip_direct_path,
                    skip_smooth_path=skip_smooth_path, # enable to make sure it passes through the valid init_samples 
                ) 
            sub_duration = float(info.split("time")[1].split("_")[0])
            sub_iteration = int(info.split("iter")[1].split("_")[0])
            reason = info.split("Reason")[1].split("_")[0]
                
            if paths is None: 
                return None, f"Reason{reason}_time{sub_duration}_iter{sub_iteration}" 
            all_paths.extend(paths)
            all_info.append(info)
            duration += sub_duration
            iteration += sub_iteration
        
        if skip_smooth_path:
            return all_paths, f"ReasonSuccess_time{duration}_iter{iteration}"
        
        print('begin smoothing')
        smoothed_paths = smooth_path(
            path=all_paths,
            extend_fn=self.extend_ee_l2,
            collision_fn=collision_fn,
            np_random=self.np_random,
            iterations=50,
        )
        print('done smoothing')
        return smoothed_paths, f"ReasonSmoothed_time{duration}_iter{iteration}"
 