instructions = [
    "You are in a house with a variety of objects. {task} You have to take a sequence of "
    "actions to full fill it. When you take an action, you can change the world. You will be told at each step, "
    "what actions are allowed and you must pick only one of those actions.",

    "You are in a house which contains many different types of objects with which you can interact. "
    "You are given a task. The task description is: {task} You will generate a sequence of "
    "actions to full fill the task. At each step, you will be told what actions are allowed "
    "and you should only pick from this action set.",

    "You are spawned in a house. The house contains many different types of objects. "
    "You can interact with these objects. You are given the following task: {task} "
    "You will generate a sequence of actions to full fill this task. At each step, you will be told what actions "
    "are allowed. You should only select an action that is allowed, otherwise, nothing will happen.",

    "You are in a house which contains many different types of objects with which you can interact. "
    "You are given a task. The task description is: {task} You will generate a sequence of "
    "actions to full fill the task. At each step, you will be told what actions are allowed "
    "and you should only pick from this action set.",

    "You start in a house that contains many different objects and locations. "
    "You can interact with these objects. You are given the following task: {task} "
    "You have to fulfill this task which will require you to take a sequence of actions. Taking an action can change"
    "the world so keep that in mind when taking actions. At each step of this sequence, you will be told what actions "
    "are allowed. You should only select an action that is allowed.",
]

no_feedback = [
    "There is no feedback to provide."
]

hp_no_op = [
    "As you have completed the task, all actions are equally good at this point.",
    "As you have completed the task, you can take any valid action you want."
]

hn_no_op = [
    "As you have completed the task, all actions are equally good at this point.",
    "As you have completed the task, you can take any valid action you want."
]

fp_no_op = [
    "You have completed the task so there are no actions to take.",
    "As you have completed the task, there are no further actions to take."
]

fn_no_op = [
    "You have completed the task so there are no actions to avoid.",
    "Since you have completed the task, there are no further actions to avoid."
]

reward_descp = [
    "You got a reward of {reward}.",
    "You receive a reward of {reward}.",
    "The reward you get for this action is {reward}.",
    "Your latest action gives you a reward of {reward}.",
    "The reward you are owed for your last action is {reward}."
]

# HN
mistake_bad_action_descp = [
    "You made a mistake by taking the bad action {avoid_action}.",
    "You should not have taken the bad action {avoid_action}.",
    "In your last move, you should have avoided the bad action {avoid_action}.",
    "It was a wrong decision to take the action {avoid_action}.",
    "It was a wrong decision to take {avoid_action}.",
]

correct_bad_action_descp = [
    "You were correct in not taking the bad action {avoid_action}.",
    "You did a good job in not taking the bad action {avoid_action}.",
    "It was a right decision to not take the bad action {avoid_action}.",
    "At the last step, you did not take the action {avoid_action}, and this was a good thing as it was a bad action.",
    "Not taking the action {avoid_action} was a good thing.",
]

# HP
mistake_good_action_descp = [
    "You should have taken the {past_opt_action} action.",
    "In the last step, you should have taken the {past_opt_action} action.",
    "You made a mistake by not taking the {past_opt_action} action.",
    "The action {past_opt_action}, is what you should have chosen in your last move.",
    "You should have taken the action {past_opt_action} instead.",
]

correct_good_action_descp = [
    "You did the right thing by taking the {past_opt_action} action.",
    "You were right to take the {past_opt_action} action.",
    "Good job at taking the correct action {past_opt_action} in the last move.",
    "You took the right decision to follow {past_opt_action}.",
    "Following {past_opt_action} was the right thing to do."
]

# FP
follow_opt_action_descp = [
    "You should now take the {opt_action} action.",
    "In the next step, follow the good action {opt_action}.",
    "You must follow the good action {opt_action} in this coming step.",
    "The optimal action to take in the next step is {opt_action}.",
    "Take {opt_action} in the next step."
]

# FN
avoid_bad_action_descp = [
    "You should not take the action {avoid_action} in the next step.",
    "You should avoid the action {avoid_action} in the next step.",
    "Avoid the {avoid_action} action, in your next move.",
    "Do not take the {avoid_action} action in your next move.",
    "In the next step, do not take the {avoid_action} action.",
]
