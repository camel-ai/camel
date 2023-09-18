import re
import numpy as np
from rocobench.subtask_plan import LLMPathPlan
from typing import List, Tuple, Dict, Union, Optional, Any
from rocobench.envs import MujocoSimEnv, EnvState, RobotState
from scipy.spatial.transform import Rotation, Slerp

class LLMResponseParser:
    """
    Takes in response from LLM query and returns parsed plan for action
    """
    def __init__(
        self,
        env: MujocoSimEnv,
        llm_output_mode: str = "action",
        robot_agent_names: Dict[str, str] = {"panda": "Bob"}, 
        response_keywords: List[str] = ["NAME", "ACTION"],
        direct_waypoints: int = 0,
        use_prepick: bool = False,
        use_preplace: bool = False,
        split_parsed_plans: bool = False, # split the waypoints into separate plans for each action
    ):
        self.llm_output_mode = llm_output_mode
        self.response_keywords = response_keywords
        self.robot_agent_names = robot_agent_names
        self.agent_names = list(robot_agent_names.values())
        self.robot_names = list(robot_agent_names.keys())
        self.env = env
        self.direct_waypoints = direct_waypoints
        self.use_prepick = use_prepick # if True, separate pre-pick and pick actions
        self.use_preplace = use_preplace # if True, separate pre-place and place actions
        self.split_parsed_plans = split_parsed_plans 

    def parse(self, obs: EnvState, response: str) -> Tuple[bool, str, List[LLMPathPlan]]: 
        parsed = ''  
        for keyword in self.response_keywords:
            if keyword not in response: 
                return False, f"Response does not contain {keyword}." , []
        for agent_name in self.robot_agent_names.values():
            if agent_name not in response:
                return False, f"Response missing plan for robot {agent_name}.", []
        
        robot_states = dict() 
        for robot_name, agent_name in self.robot_agent_names.items():
            robot_state = getattr(obs, robot_name)
            robot_states[agent_name] = robot_state 
        
        execute_str = response.split('EXECUTE')[1]
        # find the \n to split the string into line by line
        lines = execute_str.split('\n')
        valid_lines = [
            line for line in lines if all([keyword in line for keyword in self.response_keywords])
        ]
        # check that there is one line per robot
        names = set([line.split('NAME')[1].split('ACTION')[0].strip() for line in valid_lines])

        if len(valid_lines) != len(self.robot_agent_names) or len(names) != len(self.robot_agent_names):
            return False, f"Response must contain exactly one ACTION for each robot, and must contain all keywords: {self.response_keywords}", []
        # parse each line to get the robot name, action, and path, 
        # e.g. NAME Alice ACTION PICK banana PATH [(0.292, 0.136, 0.504, 0), (0.054, 0.272, 0.350, 0), (0.030, 0.501, 0.204, 1)]  
        all_kwargs = dict()
        for line in valid_lines:
            agent_name = line.split('NAME')[1].split('ACTION')[0].strip()
            state = robot_states[agent_name]
            parse_succ, reason, plan_kwargs = self.parse_single_line(agent_name, obs, state, line)
            if not parse_succ:
                return False, reason, []
            all_kwargs[agent_name] = plan_kwargs
        
        
        # merge the kwargs for each robot into a single LLMPathPlan
        max_len = max([len(kwargs) for kwargs in all_kwargs.values()])
        same_len_kwargs = dict()
        for agent_name, kwargs in all_kwargs.items():
            if len(kwargs) == max_len:
                same_len_kwargs[agent_name] = kwargs
            else:
                if 'WAIT' not in kwargs[0]['action_strs'] and 'MOVE' not in kwargs[0]['action_strs']:
                    return False, f"Bad action for {agent_name}, it can only MOVE or WAIT", []
                same_len_kwargs[agent_name] = [kwargs[0]] * max_len

        path_plans = []
        for i in range(max_len):
            kwargs = dict(
                agent_names=[],
                ee_targets={},
                ee_waypoints={},
                parsed_proposal="\n".join(valid_lines),
                action_strs=dict(),
                inhand=dict(),
                tograsp=dict(),
                return_home=dict(),
            )
            for agent_name, plan_kwarg_list in same_len_kwargs.items():
                plan_kwargs = plan_kwarg_list[i]
                 
                kwargs['agent_names'].append(agent_name)
                for key, val in plan_kwargs.items():
                    if key == 'robot_name':
                        continue
                    kwargs[key][agent_name] = val
                if 'return_home' not in plan_kwargs:
                    kwargs['return_home'][agent_name] = False
            # check if waypoint lengths match!
            waypoint_lens = [len(waypoints) for waypoints in kwargs['ee_waypoints'].values()]
            if not all([waypoint_lens[0] == _len for _len in waypoint_lens]):
                return False, 'Planned PATH must have exact same number of steps for all agents', []
            path_plans.append(LLMPathPlan(**kwargs))
        

        # if self.split_parsed_plans:
        #     splitted_plans = []
        #     for plan in path_plans:
        #         agent_names = plan.agent_names
        #         empty_grasp = {name: None for name in agent_names}
        #         num_waypoints = len(plan.ee_waypoints[agent_names[0]])
        #         for i in range(num_waypoints + 1):
        #             if i == num_waypoints:
        #                 sub_target = plan.ee_targets
        #             else:
        #                 sub_target = {_name: plan.ee_waypoints[_name][i] for _name in agent_names}
        #             sub_kwargs = dict(
        #                 agent_names=agent_names,
        #                 ee_targets=sub_target,
        #                 ee_waypoints={_name: [] for _name in agent_names},
        #                 parsed_proposal=plan.parsed_proposal,
        #                 action_strs=plan.action_strs,
        #                 inhand=plan.inhand,
        #                 tograsp=(plan.tograsp if i == num_waypoints else empty_grasp),
        #                 return_home=(plan.return_home if i == num_waypoints else {_name: False for _name in agent_names}),
        #             )
        #             splitted_plans.append(LLMPathPlan(**sub_kwargs))
        #     print(f"Split {len(path_plans)} plans into a total of {len(splitted_plans)} sub-plans")
        #     path_plans = splitted_plans

        return True, parsed, path_plans
    
    def parse_single_line(
        self,
        agent_name: str, 
        obs: EnvState, 
        robot_state: RobotState, 
        line: str
        ) -> Tuple[bool, str, List[Dict]]:
        """ parses the plan for a single robot, returns a list of parsed kwargs, to be used to compose LLMPathPlan later"""
        
        # action_desp = line.split('ACTION')[1].split('PATH')[0].strip() 
        action_desp = line.split('ACTION')[1].strip() # NOTE: include PATH in action_desp
        if 'PICK' in action_desp and 'PLACE' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_pick_and_place(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []
        elif 'PICK' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_pick_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []
        elif 'PLACE' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_place_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []

        elif 'PUT' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_put_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, [] 

        elif 'OPEN' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_open_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []

        elif 'SWEEP' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_sweep_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []
        elif 'DUMP' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_dump_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []

        elif 'MOVE' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_move_action(agent_name, obs, robot_state, line)
            if not parse_succ:
                return False, reason, []
        elif 'WAIT' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_wait_action(agent_name, obs, robot_state, line)
                
        else:
            return False, f"Action {action_desp} can't be parsed.", []
 
        for kwargs in plan_kwargs:  
            kwargs['action_strs'] = action_desp
        return True, "", plan_kwargs
    
    def parse_open_action(
        self,
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ specifically for the cabinet task """
        # should be OPEN left_door (x,y,z) 
        open_target = action_desp.split('OPEN ')[1].strip().split(' ')[0]
        if open_target not in ['left_door', 'right_door', 'left_door_handle', 'right_door_handle']:
            return False, "Only left_door and right_door can be opened.", []
        if open_target in ['left_door', 'right_door']:
            open_target += '_handle'

        if open_target not in robot_state.contacts:
            parsed = f"{open_target} cannot be opened, robot {agent_name} must first PICK it."
            return False, parsed, []
  
  
        target_pose = self.env.open_pose[open_target]

        if self.llm_output_mode == "action_and_path":
            if 'PATH' not in action_desp:
                return False, f"Action {action_desp} must contain PATH information.", []

            path_pts = self.parse_path(action_desp)
            if path_pts is None:
                return False, f"Action {action_desp} must contain correct (x,y,z) format.", []
            open_waypoints = self.add_planned_waypoints(
                ee_start=np.array(robot_state.ee_pose), 
                path_pts=path_pts,
                ee_target=target_pose,
            )
        else:
            open_waypoints = self.add_direct_waypoints(
            ee_start=np.array(robot_state.ee_pose),
            ee_target=target_pose
        )
        if "right" in open_target:
            inhand = ("cabinet_rightdoor", "right_door_handle", "rightdoorhinge") #  allow collision with both door and handle
        else:
            inhand = ("cabinet_leftdoor", "left_door_handle", "leftdoorhinge") # allow collision with both door and handle 
        
        open_plan = dict(
            robot_name=agent_name,
            ee_targets=target_pose,
            ee_waypoints=open_waypoints,
            tograsp=(open_target, open_target, 1) ,
            inhand=inhand,
            action_strs=action_desp,
        )
        return True, '', [open_plan]

    def parse_wait_action(
        self, 
        agent_name, 
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ): 
        current_pose = np.array(robot_state.ee_pose)
        if self.llm_output_mode == "action_and_path":
            if 'PATH' not in action_desp:
                return False, f"Action WAIT {action_desp} must contain PATH information.", []

            path_pts = self.parse_path(action_desp)
            if path_pts is None:
                return False, f"Action WAIT {action_desp} does not fit desired format.", []
            waypoints = self.add_planned_waypoints(
                ee_start=current_pose,
                path_pts=path_pts,
                ee_target=current_pose,
            )
        else:
            waypoints = self.add_direct_waypoints(
            ee_start=current_pose,
            ee_target=current_pose,
        )
        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        )

        return True, "", [dict(
            robot_name=agent_name,
            ee_targets=current_pose,
            ee_waypoints=waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs="WAIT",
            )]
    
    def parse_pick_action(
        self, 
        agent_name, 
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ): 
        """ Given an object name, assumes the .env has a feasible grasp site"""
        if len(robot_state.contacts) > 0:
            return False, f"Robot {agent_name} is already holding an object, can't pick another one.", []
        obj_name = action_desp.split('PICK')[1].strip()
        obj_name = obj_name.split(' ')[0]
        
        if 'Rope' in str(self.env):
            # special case 
            site_name = obj_name 
            pick_pos = self.env.get_target_pos(agent_name, site_name)
            pick_quat = np.array([1,0,0,0])
        else:
            if obj_name not in obs.objects: 
                return False, f"Object {obj_name} does not exist in the environment.", []
            
            obj_state = obs.objects[obj_name]
            for r_name in self.robot_names:
                if r_name in obj_state.contacts:
                    return False, f"Object {obj_name} is already being held by robot {r_name}, can't pick again", []
    
            site_name = self.env.get_grasp_site(obj_name) 
            if site_name is None:
                return False, f"Object {obj_name} cannot be grasped, no graspable sites found.", []

            pick_pos = obj_state.sites[site_name].xpos
            pick_quat = obj_state.sites[site_name].xquat 

        tograsp = (obj_name, site_name, 1) 
        
        pick_target_pose = np.concatenate([pick_pos, pick_quat]) 
        pick_plan = []
        if self.use_prepick:
            prepick_pos = pick_pos + np.array([0, 0, 0.1])
            prepick_quat = pick_quat.copy()
            prepick_pose = np.concatenate([prepick_pos, prepick_quat])
            if self.llm_output_mode == "action_and_path":
                if 'PATH' not in action_desp:
                    return False, f"Action {action_desp} must contain PATH information.", []
                path_pts = self.parse_path(action_desp) 
                if path_pts is None:
                    return False, f"Action {action_desp} must contain correct (x,y,z) format.", []
                prepick_waypoints = self.add_planned_waypoints(
                    ee_start=np.array(robot_state.ee_pose), 
                    path_pts=path_pts,
                    ee_target=prepick_pose
                )
            else:
                prepick_waypoints = self.add_direct_waypoints(
                    ee_start=np.array(robot_state.ee_pose), 
                    ee_target=prepick_pose
                )
            pick_plan.append(
                dict(
                robot_name=agent_name,
                ee_targets=prepick_pose,
                ee_waypoints=prepick_waypoints,
                tograsp=None,
                inhand=None,
                action_strs=action_desp,
                )
            )

        if self.llm_output_mode == "action_and_path" and not self.use_prepick:
            if 'PATH' not in action_desp:
                return False, f"Action {action_desp} must contain PATH information.", []

            path_pts = self.parse_path(action_desp) 
            if path_pts is None:
                return False, f"Action {action_desp} must contain correct (x,y,z) format.", []
            pick_waypoints = self.add_planned_waypoints(
                ee_start=np.array(robot_state.ee_pose), 
                path_pts=path_pts,
                ee_target=pick_target_pose
            )
        else:
            # adjust target to match the object site 
            pick_waypoints = self.add_direct_waypoints(
                ee_start=np.array(robot_state.ee_pose), 
                ee_target=pick_target_pose
            )
        inhand = None 
        # if obj_name == "mug" or obj_name == "cup": 
        #     # special case for cabinet task 
        #     inhand = "cabinet" 

        pick_plan.append(
            dict(
                robot_name=agent_name,
                ee_targets=pick_target_pose,
                ee_waypoints=pick_waypoints,
                tograsp=tograsp,
                inhand=inhand,
                action_strs=action_desp,
                return_home=(True if 'Sandwich' in str(self.env) else False),
                )
            )
        return True, '', pick_plan

    def parse_pick_and_place(
        self,
        agent_name, 
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ this should help construct **3** LLMPathPlan objects, pick -> place -> move back to pre-pick pose""" 
        parse_succ, reason, pick_plan = self.parse_pick_action(
            agent_name, obs, robot_state, action_desp
            )
        if not parse_succ:
            return False, reason, []
        pick_target_pose = pick_plan[0]['ee_targets']

        place_target_name = action_desp.split('PLACE')[1].strip().replace(' ', '_')
        
        target_pos = self.env.get_target_pos(
            agent_name, place_target_name
            )
        if target_pos is None:
            return False, f"PLACE target {place_target_name} does not exist in the environment.", []
        
        place_target_pose = self.get_place_target_pose(
            agent_name, obs, robot_state, place_target_name
            )
        if place_target_pose is None:
            parsed = f"Target {target_name} cannot be parsed, bad format."
            return False, parsed, []
        # update the target quat!
        place_target_pose[3:] = pick_target_pose[3:]

        place_waypoints = self.add_direct_waypoints(
            ee_start=pick_target_pose,
            ee_target=place_target_pose,
        )
        tograsp = pick_plan[0]['tograsp']
        obj_name, obj_site = tograsp[0], tograsp[1]
        
        place_plan = dict(
            robot_name=agent_name,
            ee_targets=place_target_pose,
            ee_waypoints=place_waypoints,
            tograsp=(obj_name, obj_site, 0),
            inhand=None, # NOTE: tmp issue here, cannot set inhand to (obj_name, obj_site, joint_name) when planning ahead
            action_strs=action_desp,
            return_home=True
        )

        current_pose = np.array(robot_state.ee_pose)
 
        return True, "parse success", [pick_plan[0], place_plan] #, move_plan]


    def adjust_inhand_names(
        self,
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str, 
    ):
        inhand = None
        contacts = list(robot_state.contacts) 
        if len(contacts) > 0:
            
            inhand = contacts[0]
            for door_name in [
                'cabinet_rightdoor', 
                'right_door_handle', 
                'cabinet_leftdoor',
                'left_door_handle',
                'cabinet', 
            ]:
                if door_name in contacts:
                    inhand = None 
                    break 

            for bar_name in [ 
                "bar_front_end",
                "bar_back_end",
                "bar"
            ]:
                if bar_name in contacts:
                    inhand = 'bar'
                    break 
            
            if inhand == 'pan_handle':
                inhand = 'saucepan'
            elif inhand == 'pan_lid':
                inhand = 'lid'
        if inhand is None:
            return None
        site_name = self.env.get_grasp_site(inhand)
        joint_name = self.env.get_object_joint_name(inhand)
        return (inhand, site_name, joint_name)

    def parse_move_action(
        self,
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ assumes MOVE <target> format, NEW: matches target quat when moving """
        targets = action_desp.split('MOVE ')
        if len(targets) != 2:
            parsed = f"Failed to parse target location for MOVE {action_desp}"
            return False, parsed, []
        targets = targets[1].split('PATH')[0].strip().split(' ')
        if len(targets) != 1:
            parsed = f"Failed to parse target location for MOVE {action_desp}, must be MOVE <target> format."
            return False, parsed, [] 
        target_name = targets[0].replace(' ', '_') 
        target_pos = self.env.get_target_pos(agent_name, target_name)
        if target_pos is None:
            parsed = f"MOVE target {target_name} does not exist in the environment."
            return False, parsed, []

        if target_pos is []:
            parsed = f"MOVE {target_name} cannot be parsed, bad format."
            return False, parsed, []
        
        if "," not in target_name:
            target_quat = self.env.get_target_quat(agent_name, target_name)
        else:
            target_quat = robot_state.ee_xquat.copy() # stay current quat  
        move_target_pose = np.concatenate([target_pos, target_quat])

        move_waypoints = self.add_direct_waypoints(
            ee_start=np.array(robot_state.ee_pose),
            ee_target=move_target_pose,
        )

        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        )

        move_plan = dict(
            robot_name=agent_name,
            ee_targets=move_target_pose,
            ee_waypoints=move_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp
        )

        return True, "parse MOVE success", [move_plan]

    def parse_sweep_action(
        self,
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ SWEEP parses into 3 motion plans: first move to the object, then push it horizontally towards the dustpan."""
        target_name = action_desp.split('SWEEP')[1].split('PATH')[0].strip()
        target_pos = self.env.get_target_pos(agent_name, target_name)
        if target_pos is None:
            parsed = f"SWEEP target {target_name} does not exist in the environment."
            return False, parsed, []

        current_pose = np.concatenate(
            [robot_state.ee_xpos, robot_state.ee_xquat]
        ) # return to this after sweeo 
            
        target_quat = self.env.get_target_quat(agent_name, target_name) # should stay Bob's desired flat current quat
        # target_pos[2] = robot_state.ee_xpos[2] # stay current height
        target_pos[1] -= 0.25 # offset the hard-coded val for MOVE
        target_pose1 = np.concatenate([target_pos, target_quat])

        
        _waypoints = self.add_direct_waypoints(
            ee_start=np.array(robot_state.ee_pose),
            ee_target=target_pose1,
        )

        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        )

        sweep_plan1 = dict(
            robot_name=agent_name,
            ee_targets=target_pose1,
            ee_waypoints=_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp
        )

        # second plan: push the object towards the dustpan
        target_pos = self.env.get_target_pos(agent_name, 'dustpan_rim')
        if target_pos is None:
            parsed = f"SWEEP target dustpan_bottom does not exist in the environment."
            return False, parsed, []
        target_pos[2] = target_pose1[2] # stay current height
        target_quat = self.env.get_target_quat(agent_name, 'dustpan_rim') 
        target_pose2 = np.concatenate([target_pos, target_quat])

        _waypoints = self.add_direct_waypoints(
            ee_start=target_pose1,
            ee_target=target_pose2,
        )

        sweep_plan2 = dict(
            robot_name=agent_name,
            ee_targets=target_pose2,
            ee_waypoints=_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp
        )

        
        target_pose3 = current_pose.copy()
        _waypoints = self.add_direct_waypoints(
            ee_start=target_pose2,
            ee_target=target_pose3,
        )
        sweep_plan3 = dict(
            robot_name=agent_name,
            ee_targets=target_pose3,
            ee_waypoints=_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp
        )
 
        return True, "parse SWEEP success", [sweep_plan1, sweep_plan2, sweep_plan3]


    def parse_dump_action(
        self,
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ 
        [specific to the sweeping task] 
        DUMP parses into two motion plans: 1) move to trash bin horizontally, 2) rotate gripper to dump the object from dustpan into the trash bin.
        """        
        target_name = action_desp.split('DUMP')[1].split('PATH')[0].strip()
        target_pos = self.env.get_target_pos(agent_name, "trash_bin")
        if target_pos is None:
            parsed = f"DUMP target trash_bin site does not exist in the environment."
            return False, parsed, []

        current_quat = robot_state.ee_xquat
        current_pos = robot_state.ee_xpos
        target_quat = current_quat.copy() # stay current quat
 
        target_pose1 = np.concatenate([target_pos, target_quat])

        _waypoints = self.add_direct_waypoints(
            ee_start=np.array(robot_state.ee_pose),
            ee_target=target_pose1,
        )

        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        )

        dump_plan1 = dict(
            robot_name=agent_name,
            ee_targets=target_pose1,
            ee_waypoints=_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp
        )

        # second plan: rotate gripper
        target_quat = self.env.get_target_quat(agent_name, 'trash_bin') 
        target_pos[1] -= 0.2 # move backward a bit
        target_pose2 = np.concatenate([target_pos, target_quat])

        _waypoints = self.add_direct_waypoints(
            ee_start=target_pose1,
            ee_target=target_pose2,
        )

        dump_plan2 = dict(
            robot_name=agent_name,
            ee_targets=target_pose2,
            ee_waypoints=_waypoints,
            tograsp=None,
            inhand=inhand,
            action_strs=action_desp,
            return_home=True,
        )

        target_pose3 = target_pose2.copy()
        target_pose3[3:] = current_quat
        target_pose3[1] += 0.1 # move back & rotate the gripper back!
        # target_pose3 = np.concatenate([current_pos, current_quat])
        _waypoints = self.add_direct_waypoints(
            ee_start=target_pose2,
            ee_target=target_pose3,
        )
        # dump_plan3 = dict(
        #     robot_name=agent_name,
        #     ee_targets=target_pose3,
        #     ee_waypoints=_waypoints,
        #     tograsp=None,
        #     inhand=inhand,
        #     action_strs=action_desp
        # )

 
        return True, "parse SWEEP success", [dump_plan1, dump_plan2] # , dump_plan3]



    def add_direct_waypoints(self, ee_target, ee_start) -> List[np.ndarray]:
        if self.direct_waypoints == 0:
            return []
        delta = np.array(ee_target) - np.array(ee_start)
        delta = delta / (self.direct_waypoints + 1)
        waypoints = []
        for i in range(self.direct_waypoints):
            waypoints.append(ee_start + delta * (i + 1))
        if ee_target[2] < 0.3:
            # hard code a step directly above the target
            top_pose = ee_target.copy()
            top_pose[2] = 0.3
            waypoints.append(top_pose)
        else:
            waypoints.append(ee_target)
        return waypoints
    
    def add_planned_waypoints(self, ee_target, path_pts, ee_start) -> List[np.ndarray]:
        start_rot = Rotation.from_quat(ee_start[3:])
        end_rot = Rotation.from_quat(ee_target[3:])
        orientation_slerp = Slerp(
            times=[0, 1], 
            rotations=Rotation.concatenate([start_rot, end_rot])
        )
        waypoints = []
        num_pts = len(path_pts)
        quat_idxs = np.arange(0, 1, 1/num_pts).tolist()
        quats = orientation_slerp(quat_idxs).as_quat().tolist()
        for pos, quat in zip(path_pts, quats):
            waypoints.append(np.concatenate([pos, quat])) 

        return waypoints

    def get_place_target_pose(
        self, 
        agent_name, 
        obs: EnvState,
        robot_state: RobotState, 
        target_name: str, 
    ):
        target_quat = robot_state.ee_xquat # stay same quat
        # if target location is (x, y, z) 
        if "," in target_name:
            target_name = target_name.replace('(', '').replace(')', '').replace(' ', '')
            target_name = target_name.split(',')

            if len(target_name) != 3:
                return None
            x,y,z = (float(target_name[0]), float(target_name[1]), float(target_name[2]))
            
        else: 
            target_pos = self.env.get_target_pos(agent_name, target_name)
            if target_pos is None:
                return None
            x,y,z = target_pos  

        if 'PackGroceryTask' in str(self.env):
            print('[Warning]: PLACE in packing task uses target quat')
            target_quat = self.env.get_target_quat(agent_name, target_name)
        

        place_target_pose = np.concatenate([np.array([x, y, z]), target_quat]) 
        return place_target_pose

    def parse_place_action(
        self, 
        agent_name, 
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ assumes PLACE <object> <target> format, different from PICK&PLACE actions"""
        targets = action_desp.split('PLACE')[1].strip().split('PATH')[0].strip()
        targets = targets.split(' ') 

        obj_name = targets[0].replace(' ', '_')
        target_name = " ".join(targets[1:])
        if obj_name not in obs.objects:
            parsed = f"Object {obj_name} cannot be parsed, bad format."
            return False, parsed, []
        if obj_name not in robot_state.contacts:
            parsed = f"Object {obj_name} cannot be picked, robot {agent_name} is not in contact with it."
            return False, parsed, []

        place_target_pose = self.get_place_target_pose(
            agent_name, obs, robot_state, target_name
            )
        if place_target_pose is None:
            parsed = f"Target {target_name} cannot be parsed, bad format."
            return False, parsed, []

        site_name = self.env.get_grasp_site(obj_name)
        if site_name is None:
            return False, f"Object {obj_name} cannot be un-grasped, no site found.", []
        place_plan = []
        if self.use_preplace:
            place_target_pose[2] += 0.1

        if 'milk' in obj_name:
            print(f'WARNING: Packing task hard-coded to lift the {obj_name} higher up for place')
            place_target_pose[2] += 0.15
        if 'cereal' in obj_name:
            print(f'WARNING: Packing task hard-coded to lift the {obj_name} higher up for place')
            place_target_pose[2] += 0.12

        if self.llm_output_mode == "action_and_path":
            if 'PATH' not in action_desp:
                return False, f"Action {action_desp} must contain PATH information.", []
            path_pts = self.parse_path(action_desp)
            if path_pts is None:
                return False, f"Action {action_desp} PATH does not fit desired (x,y,z) format.", []

            place_waypoints = self.add_planned_waypoints(
                ee_start=np.array(robot_state.ee_pose), 
                path_pts=path_pts,
                ee_target=place_target_pose
            )
        else:
            place_waypoints = self.add_direct_waypoints(
                ee_start=np.array(robot_state.ee_pose),
                ee_target=place_target_pose
            )
        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        ) 
            
        place_plan.append(
            dict(
                robot_name=agent_name,
                ee_targets=place_target_pose,
                ee_waypoints=place_waypoints,
                tograsp=(None if self.use_preplace else (obj_name, site_name, 0)),
                inhand=inhand,
                action_strs=action_desp,
                return_home=(not self.use_preplace),
                )
            )
        
        if self.use_preplace:
            final_place_target_pose = place_target_pose.copy()
            final_place_target_pose[2] -= 0.1
            _waypoints = self.add_direct_waypoints(
                ee_start=place_target_pose,
                ee_target=final_place_target_pose
            )
            place_plan.append(
                dict(
                    robot_name=agent_name,
                    ee_targets=final_place_target_pose,
                    ee_waypoints=_waypoints,
                    tograsp=(obj_name, site_name, 0),
                    inhand=inhand,
                    action_strs=action_desp,
                    return_home=True,
                    )
                )
        return True, "parse success", place_plan
    
    def parse_put_action(
        self, 
        agent_name,
        obs: EnvState,
        robot_state: RobotState,
        action_desp: str,
    ):
        """ PLACE doesnt match quat, PUT does """
        targets = action_desp.split('PUT')[1].split('PATH')[0].strip()
        targets = targets.split(' ') 
     
        obj_name = targets[0].replace(' ', '_')
        target_name = " ".join(targets[1:])
        
        if 'Rope' in str(self.env):
            # special case 
            site_name = obj_name 
        else:
            if obj_name not in obs.objects:
                parsed = f"Object {obj_name} cannot be parsed, bad format."
                return False, parsed, []
            if obj_name not in robot_state.contacts:
                parsed = f"Object {obj_name} cannot be PUT down, robot {agent_name} is not in contact with it."
                return False, parsed, [] 

        put_target_pose = self.get_place_target_pose(
            agent_name, obs, robot_state, target_name
            )
        
        if put_target_pose is None:
            parsed = f"Put target {target_name} cannot be parsed, bad format."
            return False, parsed, []
        
        # replace quat with desired site quat
        put_target_pose[3:] = self.env.get_target_quat(agent_name, target_name)
        if self.use_preplace:
            put_target_pose[2] += 0.15

        site_name = self.env.get_grasp_site(obj_name)
        if site_name is None:
            return False, f"Object {obj_name} cannot be un-grasped, no site found.", []

        if self.llm_output_mode == "action_and_path":
            if 'PATH' not in action_desp:
                return False, f"Action {action_desp} must contain PATH information.", []
            path_pts = self.parse_path(action_desp)
            if path_pts is None:
                return False, f"Action {action_desp} PATH does not fit desired (x,y,z) format.", []

            _waypoints = self.add_planned_waypoints(
                ee_start=np.array(robot_state.ee_pose), 
                path_pts=path_pts,
                ee_target=put_target_pose
            )
        else:
            _waypoints = self.add_direct_waypoints(
                ee_start=np.array(robot_state.ee_pose),
                ee_target=put_target_pose
            )
        
        inhand = self.adjust_inhand_names(
            agent_name, obs, robot_state, action_desp
        )

        put_plan = []
        return_home = (False if self.use_preplace else True)

        put_plan.append(
            dict(
                robot_name=agent_name,
                ee_targets=put_target_pose,
                ee_waypoints=_waypoints,
                tograsp=(None if self.use_preplace else (obj_name, site_name, 0)),
                inhand=inhand,
                action_strs=action_desp,
                return_home=return_home,
            )
        )
        if self.use_preplace:
            final_put_target_pose = put_target_pose.copy()
            final_put_target_pose[2] -= 0.15
            _waypoints = self.add_direct_waypoints(
                ee_start=put_target_pose,
                ee_target=final_put_target_pose
            )
            put_plan.append(
                dict(
                    robot_name=agent_name,
                    ee_targets=final_put_target_pose,
                    ee_waypoints=_waypoints,
                    tograsp=(obj_name, site_name, 0),
                    inhand=inhand,
                    action_strs=action_desp,
                    return_home=True,
                )
            )
        return True, "parse success", put_plan

    def parse_path_string(self, path_string: str):
        # Given a string such as '[(0.00,0.50,0.10), (0.00,0.50,0.10)].' 
        # convert it to a list of tuples of floats using regular expression match  re.
        triplet_strs = re.findall(r"\(([^)]+)\)", path_string)
        if ',' not in triplet_strs[0]:
            return None
        # remove all the non-numerical characters, e.g. parse "\"0.7" into "0.7", parse "?\"-1.2" into "-1.2" 

        tuples = [
            tuple([
                float(
                    re.sub(r"[^0-9\.\-]", "", x)
                    ) for x in triplet_str.split(",")]) for triplet_str in triplet_strs
        ] 
        return tuples 

    def parse_path(self, line: str) -> List[Tuple[float, float, float]]:
        """ 
        Parses the path from the line of the response. 
        """
        # parse the path
        gripper_path = line.split('PATH ')[1]  
        # a string of [(x,y,z), (x,y,z), ...], convert it to a list of tuples of floats
        tuples = self.parse_path_string(gripper_path) 

        return tuples 
        

if __name__ == "__main__":
    from envs import MujocoSimEnv, EnvState, SortBlockTask, SortOneBlockTask 
    env = SortOneBlockTask()
    obs = env.reset()

    parser = LLMResponseParser(
        env, 
        robot_agent_names=dict(
            ur5e_robotiq="Alice",
            panda="Bob",
            ur5e_suction="Chad",
        ),
        direct_waypoints=3,
        )
    succ, parsed, path_plans = parser.parse(
        obs,
        response="""EXECUTE
NAME Alice ACTION WAIT
NAME Bob ACTION PICK pink_polygon PLACE bin_polygon
NAME Chad ACTION PICK yellow_trapezoid PLACE bin_trapezoid
        """
    )
    print(succ, parsed, path_plans) 