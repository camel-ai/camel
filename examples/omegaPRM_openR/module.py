import torch
import random
import json
import re
import os
import math
from model_utils import LM

class Node:
    def __init__(self, question, partial_answer, correct_answer):
        self.question = question
        self.partial_answer = partial_answer
        self.correct_answer = correct_answer
        self.mc_score = None
        self.visits = 0
        self.rollouts = []
        self.visited_rollouts = []

    def add_rollout(self, result):
        self.rollouts.append(result)
        self.visited_rollouts.append(False)

    def increment_visits(self):
        self.visits += 1

# Evaluation
def check_correctness(expected_answer, generated_response):
    sentences = re.split(
        r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', generated_response.strip()
    )
    last_sentence = sentences[-1] if sentences else ''
    return expected_answer.strip() in last_sentence.strip()

def perform_rollouts(node, model: LM, num_rollouts=None):
    correctness_flags = []
    results = model.generate(node.question, node.partial_answer, num_rollouts)
    for result in results:
        node.add_rollout(result)
        is_correct = check_correctness(node.correct_answer, result)
        correctness_flags.append(int(is_correct))
    return node.rollouts, correctness_flags

def calculate_mc_score(node):
    correct_count = sum(
        check_correctness(node.correct_answer, r) for r in node.rollouts
    )
    return correct_count / len(node.rollouts) if node.rollouts else 0

def select_best_node(nodes):
    best_node = None
    best_rollout_idx = -1
    highest_qu_value = -1
    for node in nodes:
        mc_score = (
            node.mc_score if node.mc_score is not None else calculate_mc_score(node)
        )
        if mc_score in [0, 1]:
            continue
        for idx, rollout in enumerate(node.rollouts):
            if node.visited_rollouts[idx]:
                continue
            q_val = compute_q_value(rollout, mc_score)
            u_val = compute_u_value(node, nodes)
            qu_value = q_val + u_val
            if qu_value > highest_qu_value:
                highest_qu_value = qu_value
                best_node = node
                best_rollout_idx = idx
    if best_rollout_idx != -1 and best_node is not None:
        best_node.visited_rollouts[best_rollout_idx] = True
        return best_node, best_node.rollouts[best_rollout_idx], highest_qu_value
    else:
        return None, None, None

def split_text_middle(text):
    text = text.strip()
    mid_idx = len(text) // 2
    if text[mid_idx] != ' ':
        left_space = text.rfind(' ', 0, mid_idx)
        right_space = text.find(' ', mid_idx)
        if left_space == -1:
            split_idx = right_space
        elif right_space == -1:
            split_idx = left_space
        else:
            split_idx = (
                left_space if (mid_idx - left_space) <= (right_space - mid_idx) else right_space
            )
    else:
        split_idx = mid_idx
    part1 = text[:split_idx].strip()
    part2 = text[split_idx:].strip()
    return part1, part2

def locate_error(node, rollout, model):
    current_span = rollout
    previous_text = ""
    nodes_to_expand = []
    leaf_nodes = []
    while True:
        if len(current_span.split()) < 2:
            break
        left_part, right_part = split_text_middle(current_span)
        print("----")
        print(" Left:", left_part)
        print(" Right:", right_part)
        new_node = Node(
            node.question, previous_text + left_part, node.correct_answer
        )
        perform_rollouts(new_node, model)
        mc_score = calculate_mc_score(new_node)
        new_node.mc_score = mc_score
        if mc_score == 1:
            break
        elif mc_score > 0:
            current_span = right_part
            previous_text += left_part
            nodes_to_expand.append(new_node)
        else:
            current_span = left_part
            leaf_nodes.append(new_node)
    print("----")
    return nodes_to_expand, leaf_nodes

def compute_q_value(rollout_text, mc_score, alpha=0.5, beta=0.9, max_length=500):
    part1 = alpha ** (1 - mc_score)
    part2 = beta ** (len(rollout_text) / max_length)
    return part1 * part2

def compute_u_value(node, all_nodes, exploration_param=0.125):
    total_visits = sum(n.visits for n in all_nodes)
    numerator = math.sqrt(total_visits)
    denominator = 1 + node.visits
    return exploration_param * (numerator / denominator)

def process_annotations(question, nodes, model: LM, filename='nodes_data.json', max_iterations=100):
    print("++++++")
    iteration = 0
    leaf_nodes = []
    while True:
        node, rollout, max_qu = select_best_node(nodes)
        if node is not None and node.partial_answer != '':
            new_entry = {
                "question": question,
                "partial_answer": node.partial_answer,
                "mc_score": node.mc_score,
            }
            append_to_json(filename, new_entry)
            iteration += 1
            if iteration > max_iterations:
                break
        if node is None:
            break
        print()
        print("[Selected Node]")
        print(node)
        print("  Rollout:", rollout, " || QU Value:", max_qu)
        node.increment_visits()
        expanded_nodes, leaves = locate_error(node, rollout, model)
        if not expanded_nodes:
            continue
        nodes.extend(
            n for n in expanded_nodes if n is not None and n.partial_answer != ''
        )
        leaf_nodes.extend(leaves)
    for leaf_node in leaf_nodes:
        new_entry = {
            "question": question,
            "partial_answer": leaf_node.partial_answer,
            "mc_score": leaf_node.mc_score,
        }
        append_to_json(filename, new_entry)
    print("++++++")

# Utils
def append_to_json(filename, data_entry):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
    else:
        data = []
    data.append(data_entry)
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Data appended to {filename}")