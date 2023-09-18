import re
import numpy as np
from rocobench.subtask_plan import LLMPathPlan
from typing import List, Tuple, Dict, Union, Optional, Any
from collections import defaultdict
from rocobench.envs import MujocoSimEnv
from transforms3d import euler, quaternions
from rocobench.rrt_multi_arm import MultiArmRRT
from rocobench.envs.env_utils import Pose

class FeedbackManager:
    """
    Takes in **parsed** LLM response, run task validations, and provide feedback if needed
    """
    def __init__(
        self,
        env: MujocoSimEnv,
        planner: MultiArmRRT,
        llm_output_mode: str = "action",
        robot_name_map: Dict[str, str] = {"panda": "Bob"}, 
        step_std_threshold: float = 0.1, # threshold for checking if the waypoint steps are evenly spaced
        max_failed_waypoints: int = 2,
    ):
        self.env = env
        self.planner = planner
        self.llm_output_mode = llm_output_mode
        self.robot_name_map = robot_name_map
        self.robot_agent_names = [v for k, v in robot_name_map.items()] 
        self.step_std_threshold = step_std_threshold
        self.max_failed_waypoints = max_failed_waypoints
    
    def get_full_path(self, llm_plan: LLMPathPlan) -> Dict[str, Pose]:
        full_path = dict()
        obs = self.env.get_obs()  
        for robot_name, agent_name in self.robot_name_map.items():
            robot_state = getattr(obs, robot_name)
            start_pose = robot_state.ee_pose.copy()
            target_pose = llm_plan.ee_targets[agent_name]
            if self.llm_output_mode == "action_and_path":
                full_path[agent_name] = [start_pose] + llm_plan.ee_waypoints[agent_name] + [target_pose]
            else:
                full_path[agent_name] = [start_pose, target_pose]
        return full_path        

    def task_feedback(self, llm_plan: LLMPathPlan) -> str: 
        task_feedback = self.env.get_task_feedback(
            llm_plan, 
            llm_plan.ee_target_poses
            ) 
        return task_feedback    

    def reach_feedback(self, pose_dict: Dict[str, Pose]) -> str:
        """ TODO: merge this into task env feedback """
        feedback = ""
        for agent_name, pose in pose_dict.items():
            if not self.env.check_reach_range(agent_name, pose.position):
                feedback += f"{agent_name} {pose.pos_string}; "
        return feedback

    def ik_feedback(self, pose_dict: Dict[str, Pose]) -> str:
        feedback = ""
        ik_result = self.planner.inverse_kinematics_all(self.env.physics, pose_dict)
        for name, result in ik_result.items():
            if result is None:
                pose = pose_dict[name]
                feedback += f"{name} {pose.pos_string}; "
        return feedback, ik_result
    
    def collision_feedback(
        self, 
        llm_plan: LLMPathPlan, 
        ik_result: Dict[str, np.ndarray]
    ) -> str:
        assert all([result is not None for result in ik_result.values()]), "Collision feedback should be called after ik feedback"
        feedback = ""
        target_qpos = np.concatenate(
            [ik_result[name][0] for name in self.robot_agent_names]
            ) 
        # inhand_ids = llm_plan.get_inhand_ids(self.env.physics)
        allowed_collision_ids = llm_plan.get_allowed_collision_ids(self.env.physics)
        self.planner.set_inhand_info(
            self.env.physics,
            llm_plan.get_inhand_obj_info(self.env.physics)
            )
        collided_body_pairs = self.planner.get_collided_links(
            qpos=target_qpos, 
            physics=self.env.physics,
            allow_grasp=True, # check ids should already be set in at policy __init__
            check_grasp_ids=allowed_collision_ids, 
            show=0,
            )

        adjusted_names = []
        for name1, name2 in collided_body_pairs:
            name1 = self.robot_name_map.get(name1, name1) # convert panda to Bob 
            name2 = self.robot_name_map.get(name2, name2)
            adjusted_names.append((name1, name2))

        if len(collided_body_pairs) > 0: 
            # make a string in the format [name: (x,y,z), name: (x,y,z), ...]
            feedback = "collided object pairs: "
            feedback += ", ".join(
                [f"{name1}-{name2}" for name1, name2 in adjusted_names]
                )
        return feedback

    def path_feedback(self, llm_plan: LLMPathPlan) -> str:
        """ check if the waypoint steps are evenly spaced """
        feedback = ""
        if self.llm_output_mode == "action_and_path":
            full_path = self.get_full_path(llm_plan)
            for agent_name, path in full_path.items():
                stepwise_dist = []
                step_pairs = []
                for i in range(len(path)-1):
                    stepwise_dist.append(np.linalg.norm(path[i+1][:3] - path[i][:3]))
                    x,y,z = path[i][:3]
                    x2,y2,z2 = path[i+1][:3]
                    step_pairs.append(
                        f"({x:.2f},{y:.2f},{z:.2f})-({x2:.2f},{y2:.2f},{z2:.2f})"
                        )
                stepwise_dist = np.array(stepwise_dist)
                max_dist_pair = f"  Distance between {step_pairs[np.argmax(stepwise_dist)]} is {np.max(stepwise_dist):.2f}, too high"
                min_dist_pair = f"  Distance between {step_pairs[np.argmin(stepwise_dist)]} is {np.min(stepwise_dist):.2f}, too low"
                _std = np.std(stepwise_dist)
                if _std > self.step_std_threshold: 
                    feedback += f"You must make {agent_name}'s path more evenly spaced:\n{max_dist_pair}\n{min_dist_pair}\n  Overall Distance std: {_std:.2f}" 
        return feedback
    
    def get_step_string(self, pose_dict) -> str:
        step_string = ""
        for agent_name, pose in pose_dict.items():
            step_string += f"{agent_name} {pose.pos_string}; "
        return step_string[:-2]

    def single_step_feedback(self, llm_plan, pose_dict, step_type: str = "Goal") -> Tuple[bool, str]:
        step_string = self.get_step_string(pose_dict)
        feedback = f"{step_type} Step {step_string}:\n  "
        reach = self.reach_feedback(pose_dict)
        all_passed = True
        if len(reach) > 0:
            all_passed = False
            feedback += f" - Reachability failed: Out of reach: {reach}\n  "
        else:
            # feedback += " - Reach feedback: passed\n  "
            ik_feedback, ik_result = self.ik_feedback(pose_dict)
            if len(ik_feedback) > 0:
                all_passed = False
                feedback += f" - IK failed: on {ik_feedback}\n  "
            else:
                # feedback += " - IK feedback: passed\n  "
                collision_feedback = self.collision_feedback(llm_plan, ik_result)
                if len(collision_feedback) > 0:
                    all_passed = False
                    feedback += f" - Collision detected: {collision_feedback}\n  "
                # else:
                #     feedback += " - Collision feedback: passed\n  "
        if all_passed:
            # feedback = f"{step_type} Step {step_string}: All checks passed\n"
            feedback = ""
        return all_passed, feedback
 
    def give_feedback(self, llm_plan: LLMPathPlan) -> Tuple[bool, str]:
        """
        Given a parsed LLM plan, run task validations and provide feedback if needed
        """
        feedback = f"[Environment Feedback]:\n- Previous Plan:\n{llm_plan.parsed_proposal}\n"
        task_feedback = self.task_feedback(llm_plan)
        plan_passed = True 
        if len(task_feedback) == 0:
            # feedback += "- Task Constraints: all satisfied\n"
            target_passed, target_feedback = self.single_step_feedback(
                llm_plan, llm_plan.ee_target_poses, "- Goal")
            # if not target_passed:
            #     print(target_feedback)
            #     breakpoint()
            feedback += target_feedback
            plan_passed = plan_passed and target_passed

            if self.llm_output_mode == "action_and_path":
                failed_waypoints = 0 
                for pose_dict in llm_plan.ee_waypoints_list:
                    step_passed, step_feedback = self.single_step_feedback(llm_plan, pose_dict, "- Waypoint")
                    feedback += step_feedback
                    if not step_passed:
                        failed_waypoints += 1 

                waypoints_passed = failed_waypoints <= self.max_failed_waypoints  
                plan_passed = plan_passed and waypoints_passed
                if waypoints_passed:              
                    # feedback += f"All waypoint steps: passed\n"
                    path_feedback = self.path_feedback(llm_plan)
                    if len(path_feedback) > 0:
                        feedback += f"- Path feedback: failed, {path_feedback}\n"
                        plan_passed = False 
            
        else:
            plan_passed = False
            feedback += f"Task Constraints:\n faild, {task_feedback}\n"
        # breakpoint()
        return plan_passed, feedback
        

