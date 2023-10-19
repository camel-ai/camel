import os 
import json
import pickle 
import openai
import numpy as np
from datetime import datetime
from os.path import join
from typing import List, Tuple, Dict, Union, Optional, Any

from rocobench.subtask_plan import LLMPathPlan
from rocobench.rrt_multi_arm import MultiArmRRT
from rocobench.envs import MujocoSimEnv, EnvState 
from .feedback import FeedbackManager
from .parser import LLMResponseParser

####################
##### minigpt4 #####

######## debug ########
import faulthandler

import argparse
import random
from collections import defaultdict

import cv2
import re


from PIL import Image
import torch
import html
import gradio as gr

import torchvision.transforms as T
import torch.backends.cudnn as cudnn

'''
from .minigpt4.common.config import Config

from .minigpt4.common.registry import registry
from .minigpt4.conversation.conversation import Conversation, SeparatorStyle, Chat


#from .minigpt4.datasets.builders import *

from .minigpt4.models import *
from .minigpt4.processors import *
from .minigpt4.runners import *
from .minigpt4.tasks import *
'''''''''

###################################

assert os.path.exists("openai_key.json"), "Please put your OpenAI API key in a string in robot-collab/openai_key.json"
#OPENAI_KEY = str(json.load(open("openai_key.json")))
#openai.api_key = OPENAI_KEY
#print(openai.api_key)
with open("openai_key.json") as f:
    data = json.load(f)
    #openai.api_key = json.load(f)
openai.api_key = data["api_key"]
#print(openai.api_key)

PATH_PLAN_INSTRUCTION="""
[Path Plan Instruction]
Each <coord> is a tuple (x,y,z) for gripper location, follow these steps to plan:
1) Decide target location (e.g. an object you want to pick), and your current gripper location.
2) Plan a list of <coord> that move smoothly from current gripper to the target location.
3) The <coord>s must be evenly spaced between start and target.
4) Each <coord> must not collide with other robots, and must stay away from table and objects.  
[How to Incoporate [Enviornment Feedback] to improve plan]
    If IK fails, propose more feasible step for the gripper to reach. 
    If detected collision, move robot so the gripper and the inhand object stay away from the collided objects. 
    If collision is detected at a Goal Step, choose a different action.
    To make a path more evenly spaced, make distance between pair-wise steps similar.
        e.g. given path [(0.1, 0.2, 0.3), (0.2, 0.2. 0.3), (0.3, 0.4. 0.7)], the distance between steps (0.1, 0.2, 0.3)-(0.2, 0.2. 0.3) is too low, and between (0.2, 0.2. 0.3)-(0.3, 0.4. 0.7) is too high. You can change the path to [(0.1, 0.2, 0.3), (0.15, 0.3. 0.5), (0.3, 0.4. 0.7)] 
    If a plan failed to execute, re-plan to choose more feasible steps in each PATH, or choose different actions.
"""

###################
##### minigpt4 ####
###################

class DialogPrompter:
    """
    Each round contains multiple prompts, query LLM once per each agent 
    """
    def __init__(
        self,
        env: MujocoSimEnv,
        parser: LLMResponseParser,
        feedback_manager: FeedbackManager, 
        max_tokens: int = 512 * 8, # 512
        debug_mode: bool = False,
        use_waypoints: bool = False,
        robot_name_map: Dict[str, str] = {"panda": "Bob"},
        num_replans: int = 3, 
        max_calls_per_round: int = 10,
        use_history: bool = True,  
        use_feedback: bool = True,
        temperature: float = 0,
        llm_source: str = "gpt-4"
    ):
        self.max_tokens = max_tokens
        self.debug_mode = debug_mode
        self.use_waypoints = use_waypoints
        self.use_history = use_history
        self.use_feedback = use_feedback
        self.robot_name_map = robot_name_map
        self.robot_agent_names = list(robot_name_map.values())
        self.num_replans = num_replans
        self.env = env
        self.feedback_manager = feedback_manager
        self.parser = parser
        self.round_history = []
        self.failed_plans = [] 
        self.latest_chat_history = []
        self.max_calls_per_round = max_calls_per_round 
        self.temperature = temperature
        self.llm_source = llm_source

        ##### minigpt4 #####
        '''
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)

        cudnn.benchmark = False
        cudnn.deterministic = True

        def parse_args():
            parser = argparse.ArgumentParser(description="Demo")
            parser.add_argument("--cfg-path", default='prompting/eval_configs/minigptv2_eval.yaml',
                                help="path to configuration file.")
            parser.add_argument("--gpu-id", type=int, default=0, help="specify the gpu to load the model.")
            parser.add_argument(
                "--options",
                nargs="+",
                help="override some settings in the used config, the key-value pair "
                    "in xxx=yyy format will be merged into config file (deprecate), "
                    "change to --cfg-options instead.",
            )
            args = parser.parse_args()
            return args

        print('Initializing Chat')
        args = parse_args()
        cfg = Config(args)

        device = 'cuda:{}'.format(args.gpu_id)

        model_config = cfg.model_cfg
        model_config.device_8bit = args.gpu_id
        model_cls = registry.get_model_class(model_config.arch)
        model = model_cls.from_config(model_config).to(device)
        bounding_box_size = 100

        vis_processor_cfg = cfg.datasets_cfg.cc_sbu_align.vis_processor.train
        vis_processor = registry.get_processor_class(vis_processor_cfg.name).from_config(vis_processor_cfg)

        model = model.eval()

        self.CONV_VISION = Conversation(
            system="",
            roles=(r"<s>[INST] ", r" [/INST]"),
            messages=[],
            offset=2,
            sep_style=SeparatorStyle.SINGLE,
            sep="",
        )

        self.chat = Chat(model, vis_processor, device=device)
        print('load model')
        '''
        assert llm_source in ["gpt-4", "gpt-3.5-turbo", "claude", "minigpt4", "llava"], f"llm_source must be one of [gpt4, gpt-3.5-turbo, claude], got {llm_source}"

    def compose_system_prompt(
        self, 
        obs: EnvState, 
        agent_name: str,
        chat_history: List = [], # chat from previous replan rounds
        current_chat: List = [],  # chat from current round, this comes AFTER env feedback 
        feedback_history: List = []
    ) -> str:
        action_desp = self.env.get_action_prompt()
        if self.use_waypoints:
            action_desp += PATH_PLAN_INSTRUCTION
        agent_prompt = self.env.get_agent_prompt(obs, agent_name)
        
        round_history = self.get_round_history() if self.use_history else ""

        execute_feedback = ""
        if len(self.failed_plans) > 0:
            execute_feedback = "Plans below failed to execute, improve them to avoid collision and smoothly reach the targets:\n"
            execute_feedback += "\n".join(self.failed_plans) + "\n"

        chat_history = "[Previous Chat]\n" + "\n".join(chat_history) if len(chat_history) > 0 else ""
            
        system_prompt = f"{action_desp}\n{round_history}\n{execute_feedback}{agent_prompt}\n{chat_history}\n" 
        
        if self.use_feedback and len(feedback_history) > 0:
            system_prompt += "\n".join(feedback_history)
        
        if len(current_chat) > 0:
            system_prompt += "[Current Chat]\n" + "\n".join(current_chat) + "\n"

        return system_prompt 

    def get_round_history(self):
        if len(self.round_history) == 0:
            return ""
        ret = "[History]\n"
        for i, history in enumerate(self.round_history):
            ret += f"== Round#{i} ==\n{history}\n"
        ret += f"== Current Round ==\n"
        return ret
    
    def prompt_one_round(self, obs: EnvState, save_path: str = ""): 
        plan_feedbacks = []
        chat_history = [] 
        for i in range(self.num_replans):
            final_agent, final_response, agent_responses = self.prompt_one_dialog_round(
                obs,
                chat_history,
                plan_feedbacks,
                replan_idx=i,
                save_path=save_path,
            )
            chat_history += agent_responses
            parse_succ, parsed_str, llm_plans = self.parser.parse(obs, final_response) 

            curr_feedback = "None"
            if not parse_succ:  
                curr_feedback = f"""
                This previous response from [{final_agent}] failed to parse!: '{final_response}'
                {parsed_str} Re-format to strictly follow [Action Output Instruction]!"""
                ready_to_execute = False  
            
            else:
                ready_to_execute = True
                for j, llm_plan in enumerate(llm_plans): 
                    ready_to_execute, env_feedback = self.feedback_manager.give_feedback(llm_plan)        
                    if not ready_to_execute:
                        curr_feedback = env_feedback
                        break
            plan_feedbacks.append(curr_feedback)
            tosave = [
                {
                    "sender": "Feedback",
                    "message": curr_feedback,
                },
                {
                    "sender": "Action",
                    "message": (final_response if not parse_succ else llm_plans[0].get_action_desp()),
                },
            ]
            timestamp = datetime.now().strftime("%m%d-%H%M")
            fname = f'{save_path}/replan{i}_feedback_{timestamp}.json'
            json.dump(tosave, open(fname, 'w')) 

            if ready_to_execute: 
                break  
            else:
                print(curr_feedback)
        self.latest_chat_history = chat_history
        return ready_to_execute, llm_plans, plan_feedbacks, chat_history
   
    def prompt_one_dialog_round(
        self, 
        obs, 
        chat_history, 
        feedback_history, 
        replan_idx=0,
        save_path='data/',
        ):
        """
        keep prompting until an EXECUTE is outputted or max_calls_per_round is reached
        """
        
        agent_responses = []
        usages = []
        dialog_done = False 
        num_responses = {agent_name: 0 for agent_name in self.robot_agent_names}
        n_calls = 0

        while n_calls < self.max_calls_per_round:
            for agent_name in self.robot_agent_names:
                system_prompt = self.compose_system_prompt(
                    obs, 
                    agent_name,
                    chat_history=chat_history,
                    current_chat=agent_responses,
                    feedback_history=feedback_history,   
                    ) 
                
                agent_prompt = f"You are {agent_name}, your response is:"
                if n_calls == self.max_calls_per_round - 1:
                    agent_prompt = f"""
You are {agent_name}, this is the last call, you must end your response by incoporating all previous discussions and output the best plan via EXECUTE. 
Your response is:
                    """
                response, usage = self.query_once(
                    system_prompt, 
                    user_prompt=agent_prompt, 
                    max_query=3,
                    )
                
                tosave = [ 
                    {
                        "sender": "SystemPrompt",
                        "message": system_prompt,
                    },
                    {
                        "sender": "UserPrompt",
                        "message": agent_prompt,
                    },
                    {
                        "sender": agent_name,
                        "message": response,
                    },
                    usage,
                ]
                timestamp = datetime.now().strftime("%m%d-%H%M")
                fname = f'{save_path}/replan{replan_idx}_call{n_calls}_agent{agent_name}_{timestamp}.json'
                json.dump(tosave, open(fname, 'w'))  

                num_responses[agent_name] += 1
                # strip all the repeated \n and blank spaces in response: 
                pruned_response = response.strip()
                # pruned_response = pruned_response.replace("\n", " ")
                agent_responses.append(
                    f"[{agent_name}]:\n{pruned_response}"
                    )
                usages.append(usage)
                n_calls += 1
                if 'EXECUTE' in response:
                    if replan_idx > 0 or all([v > 0 for v in num_responses.values()]):
                        dialog_done = True
                        break
 
                if self.debug_mode:
                    dialog_done = True
                    break
            
            if dialog_done:
                break
 
        # response = "\n".join(response.split("EXECUTE")[1:])
        # print(response)  
        return agent_name, response, agent_responses

    def query_once(self, system_prompt, user_prompt, max_query):
        response = None
        usage = None   
        # print('======= system prompt ======= \n ', system_prompt)
        # print('======= user prompt ======= \n ', user_prompt)

        if self.debug_mode: 
            response = "EXECUTE\n"
            for aname in self.robot_agent_names:
                action = input(f"Enter action for {aname}:\n")
                response += f"NAME {aname} ACTION {action}\n"
            return response, dict()

        for n in range(max_query):
            print('querying {}th time'.format(n))
            try:
                #if self.llm_source == 'gpt-4' or 'gpt-3.5-turbo':
                response = openai.ChatCompletion.create(
                    model=self.llm_source, 
                    messages=[
                        # {"role": "user", "content": ""},
                        {"role": "system", "content": system_prompt+user_prompt},                                    
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    )
                # else
                '''
                if self.llm_source == 'minigpt4':
                    text_input = 'Is there any cube within the trashbin?'
                    img = Image.open('./Figure_1.png').convert("RGB")
                    #img.show() 

                    user_message = text_input

        
                    if isinstance(img, dict):
                        img, mask = img['image'], img['mask']
                    else:
                        mask = None

                    if '[identify]' in user_message:
                        # check if user provide bbox in the text input
                        integers = re.findall(r'-?\d+', user_message)
                        if len(integers) != 4:  # no bbox in text
                            bbox = self.mask2bbox(mask)
                            user_message = user_message + bbox
                    

                    chat_state = self.CONV_VISION.copy()
                    img_list = []
                    llm_message = self.chat.upload_img(img, chat_state, img_list)
                    self.chat.ask(user_message, chat_state)
                    temperature = 1.0
                    chat_state, ans = self.stream_answer(chat_state, img_list, temperature)
                    print(ans)
                '''
                
                usage = response['usage']
                response = response['choices'][0]['message']["content"]
                print('======= response ======= \n ', response)
                print('======= usage ======= \n ', usage)
                break
                
            except:
                print("API error in dialog, try again")
            continue
        # breakpoint()
        return response, usage
    
    def post_execute_update(self, obs_desp: str, execute_success: bool, parsed_plan: str):
        if execute_success: 
            # clear failed plans, count the previous execute as full past round in history
            self.failed_plans = []
            chats = "\n".join(self.latest_chat_history)
            self.round_history.append(
                f"[Chat History]\n{chats}\n[Executed Action]\n{parsed_plan}"
            )
        else:
            self.failed_plans.append(
                parsed_plan
            )
        return 

    def post_episode_update(self):
        # clear for next episode
        self.round_history = []
        self.failed_plans = [] 
        self.latest_chat_history = []

    ###################
    ##### minigpt4 ####
    ###################

    def extract_substrings(self, string):
        # first check if there is no-finished bracket
        index = string.rfind('}')
        if index != -1:
            string = string[:index + 1]

        pattern = r'<p>(.*?)\}(?!<)'
        matches = re.findall(pattern, string)
        substrings = [match for match in matches]

        return substrings

    def save_tmp_img(self, visual_img):
        file_name = "".join([str(random.randint(0, 9)) for _ in range(5)]) + ".jpg"
        file_path = "/tmp/" + file_name
        visual_img.save(file_path)
        return file_path


    def mask2bbox(self, mask):
        if mask is None:
            return ''
        mask = mask.resize([100, 100], resample=Image.NEAREST)
        mask = np.array(mask)[:, :, 0]

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if rows.sum():
            # Get the top, bottom, left, and right boundaries
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            bbox = '{{<{}><{}><{}><{}>}}'.format(cmin, rmin, cmax, rmax)
        else:
            bbox = ''

        return bbox


    def escape_markdown(self, text):
        # List of Markdown special characters that need to be escaped
        md_chars = ['<', '>']

        # Escape each special character
        for char in md_chars:
            text = text.replace(char, '\\' + char)

        return text


    def reverse_escape(self, text):
        md_chars = ['\\<', '\\>']

        for char in md_chars:
            text = text.replace(char, char[1:])

        return text



    def ask(self, user_message, chatbot, chat_state, img, img_list, upload_flag, replace_flag):
        if isinstance(img, dict):
            img, mask = img['image'], img['mask']
        else:
            mask = None

        if '[identify]' in user_message:
            # check if user provide bbox in the text input
            integers = re.findall(r'-?\d+', user_message)
            if len(integers) != 4:  # no bbox in text
                bbox = mask2bbox(mask)
                user_message = user_message + bbox

        if len(user_message) == 0:
            return gr.update(interactive=True, placeholder='Input should not be empty!'), chatbot, chat_state

        if chat_state is None:
            chat_state = CONV_VISION.copy()

        '''
        print('upload flag: {}'.format(upload_flag))
        if upload_flag:
            if replace_flag:
                print('RESET!!!!!!!')
                chat_state = CONV_VISION.copy()  # new image, reset everything
                replace_flag = 0
                chatbot = []
            print('UPLOAD IMAGE!!')
            img_list = []
            llm_message = chat.upload_img(img, chat_state, img_list)
            upload_flag = 0
        '''

        chat.ask(user_message, chat_state)

        chatbot = chatbot + [[user_message, None]]
        
        '''
        if '[identify]' in user_message:
            visual_img, _ = visualize_all_bbox_together(gr_img, user_message)
            if visual_img is not None:
                print('Visualizing the input')
                file_path = save_tmp_img(visual_img)
                chatbot = chatbot + [[(file_path,), None]]
        '''

        return '', chatbot, chat_state, img_list, upload_flag, replace_flag



    def stream_answer(self, chat_state, img_list, temperature):
        print('chat state', chat_state.get_prompt())
        if not isinstance(img_list[0], torch.Tensor):
            chat.encode_img(img_list)
        streamer = chat.stream_answer(conv=chat_state,
                                    img_list=img_list,
                                    temperature=temperature,
                                    max_new_tokens=500,
                                    max_length=2000)
        output = ''
        for new_output in streamer:
            escapped = escape_markdown(new_output)
            output += escapped
            #chatbot[-1][1] = output
            #yield chatbot, chat_state
            #yield chat_state
        #     print('message: ', chat_state.messages)
        chat_state.messages[-1][1] = '</s>'
        return chat_state, output