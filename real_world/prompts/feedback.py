from typing import Tuple
from real_world.real_env import RealEnv
from real_world.task_blockincup import BlockInCupTask
from real_world.kinect import KinectClient
from real_world.prompts.parser import LLMResponseParser

class FeedbackManager:
    """
    Takes in **parsed** LLM response, run task validations, and provide feedback if needed
    """
    def __init__(
        self,
        env: RealEnv,
        llm_output_mode: str = "action",
    ):
        self.env = env
        self.llm_output_mode = llm_output_mode
    
    def task_feedback(self, agent_plans) -> str: 
        task_feedback = self.env.get_task_feedback(agent_plans)
        return task_feedback 
 
    def give_feedback(self, agent_plans) -> Tuple[bool, str]:
        """
        Given a parsed plan, run task validations and provide feedback if needed
        """
        parsed_proposal = "\n".join([f"{agent_name}: {agent_plan['action_desp']}" for agent_name, agent_plan in agent_plans.items()])
        feedback = f"[Environment Feedback]:\n- Previous Plan:\n{parsed_proposal}\n"

        task_feedback = self.task_feedback(agent_plans)
        plan_passed = True 
        if len(task_feedback) != 0:
            plan_passed = False
            feedback += f"Task Constraints:\n failed, {task_feedback}\n"

        return plan_passed, feedback


if __name__ == "__main__":
    # Set up top-down kinect and task environment
    bin_cam = KinectClient(ip='128.59.23.32', port=8080)

    env = BlockInCupTask(bin_cam=bin_cam)
    obs = env.get_obs()

    parser = LLMResponseParser(env)
    succ, parsed, agent_plans = parser.parse(
        obs,
        response="""EXECUTE
NAME Alice ACTION PICK blue_triangular_block PLACE table
NAME Bob ACTION WAIT
        """
    )
    print(succ, parsed, agent_plans) 
    
    feedback_manager = FeedbackManager(env)
    plan_passed, feedback = feedback_manager.give_feedback(agent_plans)
    print(plan_passed, feedback)
    breakpoint()