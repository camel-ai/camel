from real_world.real_env import RealEnv
from real_world.kinect import KinectClient

WS_CROP_X = (180, -120)
WS_CROP_Y = (300, -380)

TASK = 'run_1'
ALL_OBJECTS = ["purple cup", "yellow cup", "green cup", "blue triangular block", "strawberry toy", "red hexagonal block", "wooden bin"]
TASK_OBJECTS = ["blue triangular block", "strawberry toy", "red hexagonal block"]

TASK_CONTEXT="""A human Alice and a robot Bob stand at different sides of a table and work together to move blocks from inside cups to a wooden bin. 
Bob cannot pick blocks when they are inside cups, but can pick blocks when they are on the table. Alice must help Bob by moving blocks from inside cups to the table.
At each round, given [Scene description], use it to reason about the task, and improve any previous plans. 
Each agent does **exactly** one action per round and only oneb agent can move an object in each round.\n
"""

ACTION_SPACE="""
[Action Options]
1) PICK <obj> PLACE <where>: robot Bob must decide which block to PICK. To complete the task, Bob must PLACE all blocks in the wooden bin.
2) WAIT: robot Bob can choose to do nothing, and wait for human Alice to move blocks from inside cups to the table.

[Action Output Instruction]
First output 'EXECUTE\n', then give exactly one ACTION for the robot.
Example#1: 'EXECUTE\nNAME Bob ACTION PICK blue_triangular_block PLACE wooden_bin\n'
Example#2: 'EXECUTE\nNAME Bob ACTION WAIT\n'
"""

CHAT_PROMPT="""Bob and Alice discuss to find the best strategy. Robot Bob must carefully consider human Alice's responses, and coordinate with her to complete the task.
They talk in order [Bob],[Alice],..., then, after reaching agreement, plan exactly one action for Bob, output an EXECUTE to summarize the plan, and stop talking.
Their entire chat history and the final plan are: """

class BlockInCupTask(RealEnv):
    def __init__(
        self,
        bin_cam,
        output_name,
        **kwargs,
    ):
        super(BlockInCupTask, self).__init__(
            bin_cam=bin_cam,
            task=TASK,
            all_objects=ALL_OBJECTS,
            task_objects=TASK_OBJECTS,
            output_name=output_name,
            **kwargs
        )
        self.robot = None
    
    def describe_objects(self, objects, cup="cup", bin="wooden bin"):
        objects_desp = ""
        assert bin in objects, f"{bin} not detected"
        bin_box = objects[bin]
        bin_center = (bin_box[0]+bin_box[2])/2, (bin_box[1]+bin_box[3])/2
        bin_size = (bin_box[2]-bin_box[0])/2

        for obj in self.task_objects:
            obj_box = objects[obj]
            obj_center = (obj_box[0]+obj_box[2])/2, (obj_box[1]+obj_box[3])/2
            dist = ((obj_center[0]-bin_center[0])**2 + (obj_center[1]-bin_center[1])**2)**0.5
            if dist < bin_size:
                # determine if the object is inside the wooden bin
                obj_name = obj.replace(" ", "_")
                bin_name = bin.replace(" ", "_")
                objects_desp += f"{obj_name}: in {bin_name}\n"
            
            elif cup not in obj:
                # determine if the object is inside a cup
                inside_sth = False
                for other_obj in objects:
                    if cup in other_obj:
                        other_obj_box = objects[other_obj]
                        other_obj_center = (other_obj_box[0]+other_obj_box[2])/2, (other_obj_box[1]+other_obj_box[3])/2
                        dist_to_cup = ((obj_center[0]-other_obj_center[0])**2 + (obj_center[1]-other_obj_center[1])**2)**0.5
                        cup_size = (other_obj_box[2]-other_obj_box[0])/2
                        if dist_to_cup < cup_size:
                            obj_name = obj.replace(" ", "_")
                            other_obj_name = other_obj.replace(" ", "_")
                            objects_desp += f"{obj_name}: in {other_obj_name}\n"
                            inside_sth = True
                            break
                if not inside_sth:
                    # determine if the object is on the table
                    obj_name = obj.replace(" ", "_")
                    objects_desp += f"{obj_name}: on table\n"
        return objects_desp
    
    def describe_scene(self, objects):
        scene_desp = "[Scene description]\n"
        scene_desp += self.describe_objects(objects)
        return scene_desp
    
    def get_robot_prompt(self, objects) -> str:
        # Provide oracle user input to describe the scene if needed
        # object_desp = input("Give objects description: ").replace("\\n", "\n")
        object_desp = self.describe_objects(objects)
        print("Scene description: ", object_desp)
        # breakpoint()
        
        # If task order specified, add to the robot_prompt: "While placing blocks in the wooden bin, make sure you follow the order blue, yellow, red."
        robot_prompt = f"""
You are a robot called {self.robot_name}, and you are collaborating with human {self.human_name} to move blocks from inside cups to a wooden bin.
You cannot pick blocks when they are inside cups, but can pick blocks when they are on the table. {self.human_name} must help you by moving blocks from inside cups to the table.
If there are any blocks on the table, you can PICK blocks from the table and PLACE them in the wooden bin. If there are no blocks on the table, you can only WAIT for the {self.human_name} to move blocks from inside cups to the table.
Only one agent can pick and place in each round. If the human is picking a block, then the robot should wait. If the robot is picking a block, then the human should wait.
Talk with {self.human_name} to coordinate and decide what to do.
At the current round:
{object_desp}
Think step-by-step about the task and {self.human_name}'s response.
Improve your plans if given [Environment Feedback].
Never forget you are {self.robot_name}!
Propose exactly one action for yourself at the **current** round, select from [Action Options].
End your response by either: 1) output PROCEED, if the plans require further discussion; 2) If everyone has made proposals and got approved, output the final plan, must strictly follow [Action Output Instruction]!
        """
        return robot_prompt
    
    def get_reward_done(self, objects, bin="wooden bin"):
        all_binned = True
        assert bin in objects, f"{bin} not detected"
        bin_box = objects[bin]
        bin_center = (bin_box[0]+bin_box[2])/2, (bin_box[1]+bin_box[3])/2
        bin_size = (bin_box[2]-bin_box[0])/2

        for obj in self.task_objects:
            obj_box = objects[obj]
            obj_center = (obj_box[0]+obj_box[2])/2, (obj_box[1]+obj_box[3])/2
            dist = ((obj_center[0]-bin_center[0])**2 + (obj_center[1]-bin_center[1])**2)**0.5
            if dist >= bin_size:
                # determine if any task object is not inside the wooden bin and thus, the task is not done
                all_binned = False
                break
        return all_binned
    
    def describe_task_context(self):
        context = TASK_CONTEXT
        return context
    
    def chat_mode_prompt(self):
        return CHAT_PROMPT

    def get_action_prompt(self):
        return ACTION_SPACE
    
    def get_task_feedback(self, agent_plans):
        feedback = ""

        if all([agent_plan['action'] == 'WAIT' for agent_plan in agent_plans.values()]):
            feedback += "At least one agent should be acting, all can't WAIT. If human is waiting, robot should be acting."
        if all([agent_plan['action'] == 'PICKPLACE' for agent_plan in agent_plans.values()]):
            feedback += "To prevent any collisions and maintain safety, the robot should wait if human is acting."

        for agent_name, agent_plan in agent_plans.items():
            if agent_plan['action'] == 'PICKPLACE' and agent_plan['pick_obj'] not in self.task_objects:
                feedback += f"{agent_name} can only pick blocks."
        
        return feedback


if __name__ == "__main__":
    # Set up top-down kinect and task environment
    bin_cam = KinectClient(ip='128.59.23.32', port=8080)

    env = BlockInCupTask(bin_cam=bin_cam)
    obs = env.get_obs()
    ws_color_im = obs.color_im[WS_CROP_X[0]:WS_CROP_X[1], WS_CROP_Y[0]:WS_CROP_Y[1]]
    env.plot_preds(ws_color_im, obs.objects, save=False, show=True)
    print(env.describe_scene(obs.objects))
    print(env.get_robot_prompt(obs.objects))
    print(env.get_system_prompt(mode="chat", obs=obs))
    print("reward: ", env.get_reward_done(obs.objects))
    breakpoint()
