from typing import List
from real_world.real_env import RealEnv, EnvState
import openai
from .feedback import FeedbackManager
from .parser import LLMResponseParser
 
class DialogPrompter:
    """
    Each round contains multiple prompts, query LLM once per each agent 
    """
    def __init__(
        self,
        env: RealEnv,
        parser: LLMResponseParser,
        feedback_manager: FeedbackManager, 
        max_tokens: int = 512,
        num_replans: int = 3, 
        max_calls_per_round: int = 6,
        use_history: bool = True,  
        use_feedback: bool = True,
        temperature: float = 0,
        llm_source: str = "gpt-4"
    ):
        self.max_tokens = max_tokens
        self.use_history = use_history
        self.use_feedback = use_feedback
        self.num_replans = num_replans
        self.env = env
        self.robot_name = env.robot_name
        self.human_name = env.human_name
        self.feedback_manager = feedback_manager
        self.parser = parser
        self.round_history = []
        self.failed_plans = [] 
        self.latest_chat_history = []
        self.max_calls_per_round = max_calls_per_round 
        self.temperature = temperature
        self.llm_source = llm_source
        assert llm_source in ["gpt-4", "gpt-3.5-turbo", "claude"], f"llm_source must be one of [gpt4, gpt-3.5-turbo, claude], got {llm_source}"

    def compose_system_prompt(
        self, 
        obs: EnvState, 
        robot_name: str,
        chat_history: List = [], # chat from previous replan rounds
        current_chat: List = [],  # chat from current round, this comes AFTER env feedback 
        feedback_history: List = []
    ) -> str:
        action_desp = self.env.get_action_prompt()
        robot_prompt = self.env.get_robot_prompt(obs.objects)
        
        round_history = self.get_round_history() if self.use_history else ""

        execute_feedback = ""
        if len(self.failed_plans) > 0:
            execute_feedback = "Plans below failed to execute, improve them to avoid collision and smoothly reach the targets:\n"
            execute_feedback += "\n".join(self.failed_plans) + "\n"

        chat_history = "[Previous Chat]\n" + "\n".join(chat_history) if len(chat_history) > 0 else ""
            
        system_prompt = f"{action_desp}\n{round_history}\n{execute_feedback}{robot_prompt}\n{chat_history}\n" 
        
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
    
    def prompt_one_round(self, obs: EnvState): 
        plan_feedbacks = []
        chat_history = [] 
        for i in range(self.num_replans):
            final_agent, final_response, agent_responses = self.prompt_one_dialog_round(
                obs,
                chat_history,
                plan_feedbacks,
                replan_idx=i,
            )
            chat_history += agent_responses
            parse_succ, parsed_str, agent_plans = self.parser.parse(obs, final_response)

            curr_feedback = "None"
            if not parse_succ:  
                curr_feedback = f"""
This previous response from [{final_agent}] failed to parse!: '{final_response}'
{parsed_str} Re-format to strictly follow [Action Output Instruction]!"""
                ready_to_execute = False  
            
            else:
                ready_to_execute, env_feedback = self.feedback_manager.give_feedback(agent_plans)       
                if not ready_to_execute:
                    curr_feedback = env_feedback
                    
            plan_feedbacks.append(curr_feedback)
            
            if ready_to_execute: 
                break  
        self.latest_chat_history = chat_history
        return ready_to_execute, agent_plans, plan_feedbacks, chat_history
   
    def prompt_one_dialog_round(
        self, 
        obs, 
        chat_history, 
        feedback_history, 
        replan_idx=0,
        ):
        """
        keep prompting until an EXECUTE is outputted or max_calls_per_round is reached
        """
        
        agent_responses = []
        usages = []
        dialog_done = False 
        agent_names = [self.robot_name, self.human_name]
        num_responses = {agent_name: 0 for agent_name in agent_names}
        n_calls = 0

        while n_calls < self.max_calls_per_round:
            for agent_name in agent_names:
                agent_prompt = f"You are {agent_name}, your response is: "
                final_agent_prompt = f"""
You are {agent_name}, this is the last call, you must end your response by incoporating all previous discussions and output the best plan via EXECUTE. 
Your response is:
                """
                if n_calls == self.max_calls_per_round - 1:
                    agent_prompt = final_agent_prompt

                if agent_name == self.human_name:
                    # get response as input from user
                    response = input(agent_prompt)
                    if '\\n' in response:
                        response = response.replace('\\n', '\n')
                    usage = None

                else:
                    system_prompt = self.compose_system_prompt(
                        obs, 
                        agent_name,
                        chat_history=chat_history,
                        current_chat=agent_responses,
                        feedback_history=feedback_history,   
                        ) 
                    
                    response, usage = self.query_once(
                        system_prompt, 
                        user_prompt=agent_prompt, 
                        max_query=3,
                        )
                
                num_responses[agent_name] += 1
                # strip all the repeated \n and blank spaces in response: 
                pruned_response = response.strip()
                # pruned_response = pruned_response.replace("\n", " ")
                agent_responses.append(
                    f"[{agent_name}]:\n{pruned_response}"
                    )
                usages.append(usage)
                n_calls += 1
                if 'EXECUTE' in response and 'NAME Bob' in response and 'NAME Alice' in response:
                    print("EXECUTE detected, dialog done")
                    if replan_idx > 0 or all([v > 0 for v in num_responses.values()]):
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
        print('======= user prompt ======= \n ', user_prompt)

        for n in range(max_query):
            print('querying {}th time'.format(n))
            try:
                response = openai.ChatCompletion.create(
                    model=self.llm_source, 
                    messages=[
                        # {"role": "user", "content": ""},
                        {"role": "system", "content": system_prompt+user_prompt},                                    
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    )
                usage = response['usage']
                response = response['choices'][0]['message']["content"]
                print('======= response ======= \n ', response)
                print('======= usage ======= \n ', usage)
                break
            except:
                print("API error, try again")
            continue
        # breakpoint()
        return response, usage
    
    def post_execute_update(self, execute_success: bool, parsed_plan: str):
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