
# This file contains the prompts for the language instructions and feedback.

loss_b_instruction_template = "You are trying to minimize the output (y) of a function by choosing input (x). The goal is to choose x such that y is as small as possible."
loss_b_instruction = (
    "Your objective is to reduce y's output (y) by selecting an appropriate input (x), aiming to make y as minimal as possible.",
    "You aim to find an input (x) that minimizes the output (y) of a function, striving to achieve the smallest possible value for y.",
    "The task is to identify an input (x) that results in the lowest possible output (y) from a function, minimizing y to the greatest extent possible.",
    "You are working to choose an input (x) that leads to the smallest possible output (y) from a function, with the ultimate goal of minimizing y.",
    "Your goal is to select an input (x) that will minimize y’s output (y), ensuring that y is as low as it can be.",
    "You are in the process of determining the best input (x) to minimize the output (y) of a function, aiming for the smallest y value achievable.",
    "The objective is to find the optimal input (x) that will yield the smallest possible output (y) from a function, in an effort to minimize y.",
    "You're on a quest to choose an input (x) that reduces the function's output (y) to a value as small as possible.",
    "Your mission is to select an input (x) that brings the output (y) of a function to its minimum, ensuring y is as small as it can be.",
    "You are working towards identifying an input (x) that minimizes the output (y) of a function, with the ultimate aim of achieving the smallest y possible."
)

r_feedback_pos_template = "You have reached the minimum!"
r_feedback_pos = (
    "You've arrived at the lowest point!",
    "The minimum has been achieved!",
    "You have attained the smallest possible value!",
    "The lowest level has been reached!",
    "You’ve hit rock bottom!",
    "You’ve successfully reached the minimum value!",
    "The minimal point has been attained!",
    "You have successfully achieved the lowest possible level!",
    "The minimum threshold has been reached!",
    "You’ve reached the lowest possible point!"
)

r_feedback_neg_template = "You have not reached the minimum!"
r_feedback_neg = (
    "You haven't attained the lowest point yet!",
    "The minimum has yet to be achieved!",
    "You are still above the smallest possible value!",
    "The lowest level hasn’t been reached!",
    "You’ve not hit the minimal point!",
    "The minimum value remains elusive!",
    "You haven’t managed to reach the lowest level yet!",
    "The minimal threshold is still ahead!",
    "You are yet to achieve the minimum!",
    "The lowest possible point hasn’t been reached!"
)

hp_feedback_dim1_template = "You chose {action} from {prev_x}. {increasing} the first number {x2} does minimize y."
hp_feedback_dim1 = (
    "Your selection was {action}, starting with {prev_x}. Indeed, {increasing} the first number {x2} results in minimizing y.",
    "Opting for {action} from {prev_x} was your choice, and it’s true that {increasing} the first number in {x2} helps to minimize y.",
    "You went with {action} beginning at {prev_x}, and {increasing} the first number in {x2} indeed leads to a minimization of y.",
    "Your choice was {action} from {prev_x}. It turns out, {increasing} the first number in {x2} does serve to minimize y.",
    "Having chosen {action} starting from {prev_x}, you’ll find that {increasing} the first number in {x2} indeed minimizes y.",
    "Selecting {action} from {prev_x}, you’ve correctly identified that {increasing} the first number in {x2} minimizes y.",
    "You selected {action} from {prev_x}. Correctly, {increasing} the first number in {x2} contributes to minimizing y.",
    "Having decided on {action} from {prev_x}, you’ve made a good call as {increasing} the first number in {x2} does minimize y.",
    "Your decision was {action} from {prev_x}, and it’s accurate that {increasing} the first number in {x2} aids in minimizing y.",
    "You picked {action} from {prev_x}. Indeed, {increasing} the first number in {x2} is effective in minimizing y."
)

hp_feedback_dim2_template = "You chose {action} from {prev_x}. {increasing} the second number {x2} does minimize y."
hp_feedback_dim2 = (
    "Your selection was {action}, starting with {prev_x}. Indeed, {increasing} the second number in {x2} results in minimizing y.",
    "Opting for {action} from {prev_x} was your choice, and it’s true that {increasing} the second number in {x2} helps to minimize y.",
    "You went with {action} beginning at {prev_x}, and {increasing} the second number in {x2} indeed leads to a minimization of y.",
    "Your choice was {action} from {prev_x}. It turns out, {increasing} the second number in {x2} does serve to minimize y.",
    "Having chosen {action} starting from {prev_x}, you’ll find that {increasing} the second number in {x2} indeed minimizes y.",
    "Selecting {action} from {prev_x}, you’ve correctly identified that {increasing} the second number in {x2} minimizes y.",
    "You selected {action} from {prev_x}. Correctly, {increasing} the second number in {x2} contributes to minimizing y.",
    "Having decided on {action} from {prev_x}, you’ve made a good call as {increasing} the second number in {x2} does minimize y.",
    "Your decision was {action} from {prev_x}, and it’s accurate that {increasing} the second number in {x2} aids in minimizing y.",
    "You picked {action} from {prev_x}. Indeed, {increasing} the second number in {x2} is effective in minimizing y."
)

hn_feedback_dim1_template = "You chose {action} from {prev_x}. {increasing} the first number {x2} does not minimize y."
hn_feedback_dim1 = (
    "Your selection was {action}, starting from {prev_x}. However, {increasing} the first value in {x2} doesn’t lead to a minimized y.",
    "Opting for {action} with the starting point at {prev_x}, it’s clear that {increasing} the first element in {x2} is not minimizing y.",
    "You went with {action} beginning with {prev_x}, but {increasing} the first number in {x2} fails to minimize y.",
    "Your choice of {action} from {prev_x} was noted, but be aware that {increasing} the first value in {x2} does not reduce y.",
    "Having chosen {action} and starting from {prev_x}, it’s evident that {increasing} the first number in {x2} does not contribute to minimizing y.",
    "You picked {action} starting from {prev_x}. Nevertheless, {increasing} the first value in {x2} is not the way to minimize y.",
    "Your decision to go with {action} from {prev_x} is taken, but know that {increasing} the first element in {x2} won’t minimize y.",
    "You selected {action} from {prev_x}, yet {increasing} the first number in {x2} does not achieve function minimization.",
    "Given your choice of {action} from {prev_x}, it’s important to realize that {increasing} the first value in {x2} is not effective for minimizing y.",
    "You’ve chosen {action} starting from {prev_x}, but unfortunately, {increasing} the first number in {x2} doesn’t lead to a minimized y."
)

hn_feedback_dim2_template = "You chose {action} from {prev_x}. {increasing} the second number {x2} does not minimize y."
hn_feedback_dim2 = (
    "Your selection was {action}, starting from {prev_x}. However, {increasing} the second value in {x2} doesn’t lead to a minimized y.",
    "Opting for {action} with the starting point at {prev_x}, it’s clear that {increasing} the second element in {x2} is not minimizing y.",
    "You went with {action} beginning with {prev_x}, but {increasing} the second number in {x2} fails to minimize y.",
    "Your choice of {action} from {prev_x} was noted, but be aware that {increasing} the second value in {x2} does not reduce y.",
    "Having chosen {action} and starting from {prev_x}, it’s evident that {increasing} the second number in {x2} does not contribute to minimizing y.",
    "You picked {action} starting from {prev_x}. Nevertheless, {increasing} the second value in {x2} is not the way to minimize y.",
    "Your decision to go with {action} from {prev_x} is taken, but know that {increasing} the second element in {x2} won’t minimize y.",
    "You selected {action} from {prev_x}, yet {increasing} the second number in {x2} does not achieve function minimization.",
    "Given your choice of {action} from {prev_x}, it’s important to realize that {increasing} the second value in {x2} is not effective for minimizing y.",
    "You’ve chosen {action} starting from {prev_x}, but unfortunately, {increasing} the second number in {x2} doesn’t lead to a minimized y."
)

fp_feedback_dim1_template = "You chose {x}. Choose a {smaller} number than {x2} to minimize y."
fp_feedback_dim1 = (
    "Your selection was {x}. To minimize y, provide a {smaller} number than the first value in {x2}.",
    "Having chosen {x}, you should now issue a {smaller} number than the first element of {x2} to reduce y.",
    "You went with {x}. Now, aim to output a {smaller} number than what is at the start of {x2} to achieve a smaller y.",
    "Given your choice of {x}, for minimizing y, you need to select a {smaller} number than the first entry in {x2}.",
    "You decided on {x}. To minimize y, you should output a {smaller} number than the first number in your chosen list.",
    "Your pick was {x}. Minimize y by issuing a {smaller} number than the first element of {x2}.",
    "You've opted for {x}. To ensure y is minimized, aim to produce a {smaller} number than the starting value of {x2}.",
    "Your choice fell on {x}. Now, to bring y down, provide a {smaller} number than the first in the list {x2}.",
    "You picked {x}. In order to minimize y, you should output a {smaller} number than the first number in your chosen set.",
    "Your selection was {x}, and to minimize y, you need to output a {smaller} number than the first value from {x2}."
)

fp_feedback_dim2_template = "You chose {x}. Choose a {smaller} number than {x2} to minimize y."
fp_feedback_dim2 = (
    "Your selection was {x}. To minimize y, provide a {smaller} number than the second value in {x2}.",
    "Having chosen {x}, you should now issue a {smaller} number than the second element of {x2} to reduce y.",
    "You went with {x}. Now, aim to output a {smaller} number than what is at the start of {x2} to achieve a smaller y.",
    "Given your choice of {x}, for minimizing y, you need to select a {smaller} number than the second entry in {x2}.",
    "You decided on {x}. To minimize y, you should output a {smaller} number than the second number in your chosen list.",
    "Your pick was {x}. Minimize y by issuing a {smaller} number than the second element of {x2}.",
    "You've opted for {x}. To ensure y is minimized, aim to produce a {smaller} number than the starting value of {x2}.",
    "Your choice fell on {x}. Now, to bring y down, provide a {smaller} number than the second in the list {x2}.",
    "You picked {x}. In order to minimize y, you should output a {smaller} number than the second number in your chosen set.",
    "Your selection was {x}, and to minimize y, you need to output a {smaller} number than the second value from {x2}."
)

fn_feedback_dim1_template = "You chose {x}. Do not choose a {smaller} number than {x2} to minimize y."
fn_feedback_dim1 = (
    "Your selection was {x}. To achieve a minimized y, you should avoid issuing a {smaller} number than the first value in {x2}.",
    "Having picked {x}, it’s crucial to not provide a {smaller} number than the first element of {x2} in order to reduce y.",
    "You went with {x}. In order to minimize y, make sure not to output a {smaller} number than the initial entry in {x2}.",
    "Given your choice of {x}, to ensure y is minimized, refrain from selecting a {smaller} number than the first in {x2}.",
    "You decided on {x}. Avoid producing a {smaller} number than the first number in {x2} if you want to minimize y.",
    "Your choice was {x}. To bring y down, you shouldn’t output a {smaller} number than the first element of {x2}.",
    "You've chosen {x}. Minimizing y requires not outputting a {smaller} number than the starting value in {x2}.",
    "Your selection fell on {x}. For the purpose of minimizing y, do not provide a {smaller} number than the first from {x2}.",
    "You picked {x}. To minimize y, ensure not to choose a {smaller} number than the first entry in your selected list.",
    "Having chosen {x}, remember that outputting a {smaller} number than the first value in {x} will not help minimize y."
)

fn_feedback_dim2_template = "You chose {x}. Do not choose a {smaller} number than {x2} to minimize y."
fn_feedback_dim2 = (
    "Your selection was {x}. To achieve a minimized y, you should avoid issuing a {smaller} number than the second value in {x2}.",
    "Having picked {x}, it’s crucial to not provide a {smaller} number than the second element of {x2} in order to reduce y.",
    "You went with {x}. In order to minimize y, make sure not to output a {smaller} number than the initial entry in {x2}.",
    "Given your choice of {x}, to ensure y is minimized, refrain from selecting a {smaller} number than the second in {x2}.",
    "You decided on {x}. Avoid producing a {smaller} number than the second number in {x2} if you want to minimize y.",
    "Your choice was {x}. To bring y down, you shouldn’t output a {smaller} number than the second element of {x2}.",
    "You've chosen {x}. Minimizing y requires not outputting a {smaller} number than the starting value in {x2}.",
    "Your selection fell on {x}. For the purpose of minimizing y, do not provide a {smaller} number than the second from {x2}.",
    "You picked {x}. To minimize y, ensure not to choose a {smaller} number than the second entry in your selected list.",
    "Having chosen {x}, remember that outputting a {smaller} number than the second value in {x2} will not help minimize y."
)