instructions = [
    "You are in a house with multiple rooms. Each room can have objects that will "
    "be visible to you only if you are in that room. Each room can have a door along the "
    "North, South, East and West direction. You can follow a direction to go from one room to another. "
    "If there is no door along that direction, then you will remain in the room. You will start in a room. "
    "Your goal is to navigate to another room which has the treasure. There is only one such room which "
    "contains treasure. You have an action space of size 4. Action 0 leads to going North. "
    "Action 1 leads to going East. Action 2 leads going west. Action 3 leads to going South.",

    "You are in a house that has multiple rooms. When you are in a room, you can see all the objects "
    "that this room contains but cannot see objects in different room. At a given time, you can only be in one room. "
    "Each room can have a door along the North, South, East and West direction. Different rooms can different number of"
    "doors. You can follow a direction to go from one room to another, provided there is a door in that direction. "
    "If there is no door along that direction, then you will remain where you are. You will start in a room. "
    "Your goal is to navigate to the unique room which has the treasure. You have an action space of size 4. "
    "Action 0 leads to going North. Action 1 leads to going East. Action 2 leads going west. "
    "Action 3 leads to going South.",

    "You are in a house that has multiple rooms and your goal is to reach the unique room which contains the treasure "
    "starting from a given starting room. Each room has objects that will only be visible to you if you are in "
    "that room. You cannot be in two rooms at once. Each room can have a door along the 4 directions: "
    "North, South, East and West. Two different rooms need not have the same number of doors. If there is a door "
    "between room A and room B then you can use it to travel from both room A to room B, and vice versa. "
    "However, if you follow the West direction to go from room A to room B, then you must follow the East direction "
    "to go from Room B to room A via the same door. Similarly, if you follow the North direction to go from room A to "
    "room B, then you must follow the South direction to go from Room B to room A via the same door. You can follow a "
    "direction to go from one room to another, provided there is a door in that direction. If there is no door in "
    "that direction, then you will remain where you are.You have an action space of size 4. Action 0 leads to going "
    "North. Action 1 leads to going East. Action 2 leads going west. Action 3 leads to going South.",
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

success_descp = [
    "You succeeded! Congratulations.",
    "You have successfully completed the task.",
    "You have completed the task successfully! Great job",
    "You have succeeded at solving the task."
]

treasure_reached_descp = [
    "You have already reached the treasure. Good job.",
    "You have reached the treasure already.",
    "You have already reached the treasure and solve the task. Congratulations.",
    "You can now do anything since you have already solved the task."
]

hn_success_descp = [
    "You did correct thing by not following the {avoid_action} direction in the old room.",
    "You were right in not going in the {avoid_action} direction in your latest move.",
    "You were right at avoiding the {avoid_action} direction in your last action.",
    "Good job at avoiding the {avoid_action} direction in your last action.",
    "Not going towards the {avoid_action} direction was a good idea in your last action."
]

hn_fail_descp = [
    "You made a mistake by following the {avoid_action} direction in your last move.",
    "You should not have followed the {avoid_action} direction in the last move.",
    "In your last action, you should not have gone towards the {avoid_action} direction.",
    "You should have not gone towards the {avoid_action} direction in the last step."
]

hp_fail_descp = [
    "You should have taken the {old_gold_action} direction in {room}.",
    "You made a mistake by not following the {old_gold_action} direction in {room}",
    "In your last move when you are in {room}, you should have gone towards {old_gold_action} direction.",
    "Anytime you are in {room}, you must follow the {old_gold_action} direction."
]

hp_succ_descp = [
    "Good job. You followed the right direction {old_gold_action} in {room}.",
    "You did the right thing by following the {old_gold_action} direction in {room}.",
    "You were totally right in following {old_gold_action} direction in {room}. Good job!",
    "Following {old_gold_action} direction in {room} was the right thing to do.",
]

fp = [
    "You should go towards the {gold_action} direction in {new_room}.",
    "Make sure to go in the {gold_action} direction in {new_room}.",
    "You should go towards the {gold_action} direction from {new_room}.",
    "Now that you are in {new_room}, make sure to follow the {gold_action} direction."
]

fn = [
    "You should avoid taking the action {avoid_action} in this {new_room}.",
    "You should not follow the {avoid_action} direction in this {new_room}.",
    "Now that you are in {new_room}, dont go in the direction of {avoid_action}",
    "You are now in {new_room} and must not go in the direction of {avoid_action} while you are here.",
]
