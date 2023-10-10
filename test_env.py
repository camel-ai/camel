import os
import pickle
import json
import numpy as np
import logging
from datetime import datetime
from glob import glob
from natsort import natsorted
from copy import deepcopy
import argparse
from typing import List, Tuple, Dict, Union, Optional, Any
from collections import defaultdict
import matplotlib.pyplot as plt

from PIL import Image

from rocobench.envs import SortOneBlockTask, CabinetTask, MoveRopeTask, SweepTask, MakeSandwichTask, PackGroceryTask, MujocoSimEnv, SimRobot #, visualize_voxel_scene
from rocobench import PlannedPathPolicy, LLMPathPlan, MultiArmRRT
from prompting import LLMResponseParser, FeedbackManager, DialogPrompter, SingleThreadPrompter, save_episode_html

# print out logging.info
logging.basicConfig(level=logging.INFO)
logging.root.setLevel(logging.INFO)

TASK_NAME_MAP = {
    "sweep": SweepTask,
}

def main(args):
    assert args.task in TASK_NAME_MAP.keys(), f"Task {args.task} not supported"
    env_cl = TASK_NAME_MAP[args.task]
    if args.task == 'rope':
        args.output_mode = 'action_and_path'
        args.split_parsed_plans = True
        logging.warning("MoveRopeTask requires split parsed plans\n")

        args.control_freq = 20
        args.max_failed_waypoints = 0
        logging.warning("MopeRope requires max failed waypoints 0\n")
        if not args.no_feedback:
            args.tstep = 5
            logging.warning("MoveRope needs only 5 tsteps\n")

    elif args.task == 'pack':
        args.output_mode = 'action_and_path'
        args.control_freq = 10
        args.split_parsed_plans = True
        args.max_failed_waypoints = 0
        args.direct_waypoints = 0
        logging.warning("PackGroceryTask requires split parsed plans, and no failed waypoints, no direct waypoints\n")

    render_freq = 600
    if args.control_freq == 15:
        render_freq = 1200
    elif args.control_freq == 10:
        render_freq = 2000
    elif args.control_freq == 5:
        render_freq = 3000
    env = env_cl(
        render_freq=render_freq,
        image_hw=(400,400),
        sim_forward_steps=300,
        error_freq=30,
        error_threshold=1e-5,
        randomize_init=True,
        render_point_cloud=0,
        render_cameras=["face_panda","face_ur5e","teaser",],
        one_obj_each=True,
    )
    robots = env.get_sim_robots()
    if args.no_feedback:
        assert args.num_replans == 1, "no feedback mode requires num_replans=1 but longer -tsteps"

    # save args into a json file
    args_dict = vars(args)
    args_dict["env"] = env.__class__.__name__
    timestamp = datetime.now().strftime("%Y%m_%H%M")
    fname = os.path.join(args.data_dir, args.run_name, f"args_{timestamp}.json")
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    json.dump(args_dict, open(fname, "w"), indent=2)

    obs = env.reset()
    #img=env.physics.render(camera_id="ur5e_camera", height=480, width=600)
    img=env.physics.render(camera_id="panda_camera", height=480, width=600)

    im = Image.fromarray(img)
    plt.imshow(img)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", "-d", type=str, default="data")
    parser.add_argument("--temperature", "-temp", type=float, default=0)
    parser.add_argument("--start_id", "-sid", type=int, default=-1)
    parser.add_argument("--num_runs", '-nruns', type=int, default=1)
    parser.add_argument("--run_name", "-rn", type=str, default="test")
    parser.add_argument("--tsteps", "-t", type=int, default=10)
    parser.add_argument("--task", type=str, default="sweep")
    parser.add_argument("--output_mode", type=str, default="action_only", choices=["action_only", "action_and_path"])
    parser.add_argument("--comm_mode", type=str, default="dialog", choices=["chat", "plan", "dialog"])
    parser.add_argument("--control_freq", "-cf", type=int, default=15)
    parser.add_argument("--skip_display", "-sd", action="store_true")
    parser.add_argument("--direct_waypoints", "-dw", type=int, default=5)
    parser.add_argument("--num_replans", "-nr", type=int, default=5)
    parser.add_argument("--cont", "-c", action="store_true")
    parser.add_argument("--load_run_name", "-lr", type=str, default="sort_task")
    parser.add_argument("--load_run_id", "-ld", type=int, default=0)
    parser.add_argument("--max_failed_waypoints", "-max", type=int, default=1)
    parser.add_argument("--debug_mode", "-i", action="store_true")
    parser.add_argument("--use_weld", "-w", type=int, default=1)
    parser.add_argument("--rel_pose", "-rp", action="store_true")
    parser.add_argument("--split_parsed_plans", "-sp", action="store_true")
    parser.add_argument("--no_history", "-nh", action="store_true")
    parser.add_argument("--no_feedback", "-nf", action="store_true")
    parser.add_argument("--llm_source", "-llm", type=str, default="gpt-4")
    logging.basicConfig(level=logging.INFO)

    args = parser.parse_args()
    main(args)
