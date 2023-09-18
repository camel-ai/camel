from typing import List, Tuple, Dict
from real_world.real_env import RealEnv, EnvState
from real_world.task_blockincup import BlockInCupTask
from real_world.kinect import KinectClient

class LLMResponseParser:
    """ 
    Takes in response from LLM query and returns parsed plan for action
    """
    def __init__(
        self,
        env: RealEnv,
        llm_output_mode: str = "action",
        response_keywords: List[str] = ["NAME", "ACTION"],
     ):
        self.llm_output_mode = llm_output_mode
        self.response_keywords = response_keywords
        self.env = env
        self.robot_name = env.robot_name
        self.human_name = env.human_name
        self.agent_names = [self.robot_name, self.human_name] 

    def parse(self, obs: EnvState, response: str) -> Tuple[bool, str, Dict]: 
        for keyword in self.response_keywords:
            if keyword not in response: 
                return False, f"Response does not contain {keyword}." , {}
        for agent_name in self.agent_names:
            if agent_name not in response:
                return False, f"Response missing plan for agent {agent_name}.", {}
        
        execute_str = response.split('EXECUTE')[1]
        
        # find the \n to split the string into line by line
        lines = execute_str.split('\n')
        valid_lines = [
            line for line in lines if all([keyword in line for keyword in self.response_keywords])
        ]
        
        # check that there is one line per robot
        names = set([line.split('NAME')[1].split('ACTION')[0].strip() for line in valid_lines])
        
        if len(valid_lines) != len(self.agent_names) or len(names) != len(self.agent_names):
            return False, f"Response must contain exactly one ACTION for each agent, and must contain all keywords: {self.response_keywords}", {}
        # parse each line to get the agent name and action
        # e.g. NAME Alice ACTION PICK green_cube PLACE table
        # e.g. NAME Bob ACTION PICK blue_triangular_block PLACE wooden_bin 
        all_kwargs = dict()
        for line in valid_lines:
            agent_name = line.split('NAME')[1].split('ACTION')[0].strip()
            
            parse_succ, reason, plan_kwargs = self.parse_single_line(agent_name, obs, line)
            if not parse_succ:
                return False, reason, []
            all_kwargs[agent_name] = plan_kwargs
        
        return True, "Response parsed successfully", all_kwargs
    
    def parse_single_line(
        self,
        agent_name: str, 
        obs: EnvState,
        line: str
        ) -> Tuple[bool, str, List[Dict]]:
        """ parses the plan for a single agent, returns a list of parsed kwargs """
        
        action_desp = line.split('ACTION')[1].strip() # NOTE: PATH not included in action_desp for real-world
        if 'WAIT' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_wait_action(obs, action_desp)
            return True, reason, plan_kwargs
                
        elif 'PICK' in action_desp and 'PLACE' in action_desp:
            parse_succ, reason, plan_kwargs = self.parse_pick_and_place(obs, action_desp)
            if not parse_succ:
                return False, reason, []
            return True, reason, plan_kwargs
        
        else:
            return False, f"Action {action_desp} can't be parsed.", []
    
    def parse_wait_action(
        self,
        obs: EnvState,
        action_desp: str,
    ):
        return True, "", dict(
            pick_obj=None,
            place_where=None,
            action_desp=action_desp,
            action="WAIT",
            )

    def parse_pick_and_place(
        self,
        obs: EnvState,
        action_desp: str,
    ):
        pick_target_name = action_desp.split('PICK')[1].split('PLACE')[0].strip().replace('_', ' ')
        place_target_name = action_desp.split('PLACE')[1].strip().replace('_', ' ')
        
        # TODO uncomment this
        if pick_target_name not in obs.objects:
            return False, f"PICK target {pick_target_name} does not exist in the environment.", []
        
        if place_target_name not in obs.objects and place_target_name != "table":
            return False, f"PLACE target {place_target_name} does not exist in the environment.", []

        return True, "parse success", dict(
            pick_obj=pick_target_name,
            place_where=place_target_name,
            action_desp=action_desp,
            action="PICKPLACE",
            )
        

if __name__ == "__main__":
    # Set up top-down kinect and task environment
    bin_cam = KinectClient(ip='128.59.23.32', port=8080)

    env = BlockInCupTask(bin_cam=bin_cam)
    obs = env.get_obs()

    parser = LLMResponseParser(env)
    succ, parsed, agent_plans = parser.parse(
        obs,
        response="EXECUTE\nNAME Alice ACTION PICK blue_triangular_block PLACE table\nNAME Bob ACTION WAIT\n"
    )
    print(succ, parsed, agent_plans) 
    parsed_proposal = "\n".join([f"{agent_name}: {agent_plan['action_desp']}" for agent_name, agent_plan in agent_plans.items()])
    print(parsed_proposal)
    breakpoint()