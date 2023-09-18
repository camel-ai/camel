import os 
import logging 
import argparse
import numpy as np
import openai 
import json
from real_world.kinect import KinectClient
from real_world.realur5 import UR5RTDE
from real_world.real_env import RealEnv
from real_world.task_blockincup import BlockInCupTask
from real_world.prompts import LLMResponseParser, FeedbackManager, DialogPrompter
# print out logging.info
logging.basicConfig(level=logging.INFO)
logging.root.setLevel(logging.INFO)

key_path="../openai_key.json"  # TODO: change this to your own key 
OPENAI_KEY = json.load(open(key_path))
openai.api_key = OPENAI_KEY 

WS_CROP_X = (180, -120)
WS_CROP_Y = (300, -380)

class LLMRunner:
    def __init__(
        self,
        env: RealEnv, 
        max_runner_steps: int = 15, 
        num_runs: int = 1,
        verbose: bool = False,
        np_seed: int = 0,
        start_seed: int = 0,
        llm_output_mode="action_only", # "action_only" or "action_and_path"
        llm_comm_mode="dialog", 
        llm_num_replans=1,
        give_env_feedback=False,
        skip_display=True,
        use_history: bool = False,
        use_feedback: bool = False,
        temperature: float = 0.0,
        llm_source: str = "gpt4",
        ): 
        self.env = env
        self.verbose = verbose
        self.np_seed = np_seed
        self.start_seed = start_seed
        self.num_runs = num_runs
        self.max_runner_steps = max_runner_steps
        self.give_env_feedback = give_env_feedback
        self.use_history = use_history
        self.use_feedback = use_feedback

        self.llm_output_mode = llm_output_mode  
        
        self.llm_num_replans = llm_num_replans
        self.llm_comm_mode = llm_comm_mode
        self.response_keywords = ['NAME', 'ACTION']
        self.skip_display = skip_display
        self.temperature = temperature
        self.parser = LLMResponseParser(
            self.env,
            llm_output_mode,
            self.response_keywords,
        )
        self.feedback_manager = FeedbackManager(
            env=self.env,
            llm_output_mode=self.llm_output_mode,
        )
        
        if llm_comm_mode == "dialog":
            self.prompter = DialogPrompter(
                env=self.env,
                parser=self.parser,
                feedback_manager=self.feedback_manager,
                max_tokens=512,
                max_calls_per_round=5,
                use_history=self.use_history,
                use_feedback=self.use_feedback,
                num_replans=self.llm_num_replans,
                temperature=self.temperature,
                llm_source=llm_source,
            )   
        else:
            raise NotImplementedError
     
    def one_run(self, run_id):
        done = False

        for step in range(self.max_runner_steps):
            obs = self.env.get_obs(save=True)
            ws_color_im = obs.color_im[WS_CROP_X[0]:WS_CROP_X[1], WS_CROP_Y[0]:WS_CROP_Y[1]]
            self.env.plot_preds(ws_color_im, obs.objects, save=True, show=False)
            
            done = self.env.get_reward_done(obs.objects)
            print(f"At step {step}, task done: {done}")

            if done:
                break
            
            ready_to_execute, agent_plans, response, prompt_breakdown = self.prompter.prompt_one_round(obs)
            if not ready_to_execute or agent_plans is None:
                print(f"Run {run_id}: Step {step} failed to get a plan from LLM. Move on to next step.")
                continue
                
            print(f"Step: {step} LLM parsed, executing the following plan:")
            print("\n".join([f"{agent_name}: {agent_plan['action_desp']}" for agent_name, agent_plan in agent_plans.items()]))
            # breakpoint()

            # Implementing robot execution if action is PICKPLACE and use_robot is True
            # Assumption: human implementation is correct once the human confirms it has been executed
            if agent_plans['Bob']['action'] == 'PICKPLACE' and self.env.robot is not None:
                pick_obj = agent_plans['Bob']['pick_obj']
                place_where = agent_plans['Bob']['place_where']
                self.env.pick_and_place_primitive(obs, pick_obj, place_where)

            parsed_plan = "\n".join([f"{agent_name}: {agent_plan['action_desp']}" for agent_name, agent_plan in agent_plans.items()])
            self.prompter.post_execute_update(execute_success=done, parsed_plan=parsed_plan)
            input("Press enter to confirm execution!")
        
        print("Run finished after {} timesteps".format(step+1))
        self.prompter.post_episode_update()
            

    def run(self, args):
        start_id = 0 if args.start_id == -1 else args.start_id
        for run_id in range(start_id, start_id + self.num_runs):
            print(f"==== Run {run_id} starts ====")
            self.one_run(run_id)

def main(args):
    # Set up top-down kinect and task environment
    bin_cam = KinectClient(ip='128.59.23.32', port=8080)

    if args.task == 'blockincup':
        env_cl = BlockInCupTask
        args.output_mode = 'action_only'
        args.comm_mode = 'dialog'
    else:
        raise NotImplementedError 
    
    env = env_cl(bin_cam=bin_cam, output_name="run_1") 
    if args.no_feedback:
        assert args.num_replans == 1, "no feedback mode requires num_replans=1 but longer -tsteps"

    # breakpoint()
    # Set up UR5 RTDE robot for execution
    if args.use_robot:
        env.robot = UR5RTDE(ip='192.168.0.113', gripper='suction', home_joint=np.array([-180, -90, 90, -90, -90, 0]) / 180 * np.pi)
        env.robot.home()

    runner = LLMRunner(
        env=env,
        max_runner_steps=args.tsteps, 
        num_runs=args.num_runs, 
        skip_display=args.skip_display,
        llm_output_mode=args.output_mode, # "action_only" or "action_and_path"
        llm_comm_mode=args.comm_mode, # "chat" or "plan"
        llm_num_replans=args.num_replans,
        use_history=(not args.no_history),
        use_feedback=(not args.no_feedback),
        temperature=args.temperature,
        llm_source=args.llm_source,
    )
    # runner.run(args)
    runner.one_run(run_id=0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--temperature", "-temp", type=float, default=0)
    parser.add_argument("--start_id", "-sid", type=int, default=-1)
    parser.add_argument("--num_runs", '-nruns', type=int, default=1)
    parser.add_argument("--tsteps", "-t", type=int, default=10) 
    parser.add_argument("--task", type=str, default="blockincup")
    parser.add_argument("--output_mode", type=str, default="action_only", choices=["action_only", "action_and_path"])
    parser.add_argument("--comm_mode", type=str, default="dialog", choices=["chat", "plan", "dialog"])
    parser.add_argument("--skip_display", "-sd", action="store_true")
    parser.add_argument("--num_replans", "-nr", type=int, default=5)
    parser.add_argument("--cont", "-c", action="store_true") 
    parser.add_argument("--load_run_name", "-lr", type=str, default="blockincup_task")
    parser.add_argument("--load_run_id", "-ld", type=int, default=0)
    parser.add_argument("--no_history", "-nh", action="store_true")
    parser.add_argument("--no_feedback", "-nf", action="store_true")
    parser.add_argument("--llm_source", "-llm", type=str, default="gpt-4")
    parser.add_argument("--use_robot", "-robot", action="store_true")
    logging.basicConfig(level=logging.INFO)

    args = parser.parse_args()
    main(args)