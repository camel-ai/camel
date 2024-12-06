# Copyright 2023 https://github.com/ShishirPatil/gorilla
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
from tree_sitter import Language, Parser
import concurrent.futures
from types import SimpleNamespace
import os

# Get all the subtrees given a root_node
def get_all_sub_trees(root_node):
    node_stack = []
    sub_tree_sexp_list = []
    depth = 1
    text = root_node.text
    node_stack.append([root_node, depth])
    while len(node_stack) != 0:
        cur_node, cur_depth = node_stack.pop()
        if cur_node.child_count > 0:
            sub_tree_sexp_list.append(
                [cur_node.sexp(), cur_depth, cur_node, cur_node.children[0].text]
            )
        else:
            sub_tree_sexp_list.append([cur_node.sexp(), cur_depth, cur_node, None])
        for child_node in cur_node.children:
            if len(child_node.children) != 0:
                depth = cur_depth + 1
                node_stack.append([child_node, depth])
    return sub_tree_sexp_list


# Parse the program into AST trees
def ast_parse(candidate, lang="python"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lang_path = os.path.join(current_dir, "codebleu/parser/my-languages.so")
    LANGUAGE = Language(lang_path, lang)
    parser = Parser()
    parser.set_language(LANGUAGE)

    candidate_tree = parser.parse(bytes(candidate, "utf8")).root_node
    return candidate_tree


# Get all the arguments in the ast tree
def get_args(node):
    if node.child_count == 0:
        return []
    args_list = []
    for child in node.children[0].children[0].children[1].children:
        if "repo_or_dir" in child.text.decode() or "model" in child.text.decode():
            args_list.append(child.children[2].text)
    return args_list


# Check if there is an api match
def ast_check(candidate_subtree_list, base_tree_list):
    for idx, base_tree in enumerate(base_tree_list):
        if base_tree.children[0].children[0].child_count == 0:
            continue
        api_name = base_tree.children[0].children[0].children[0].text
        for candidate_tree in candidate_subtree_list:
            if candidate_tree[3] == api_name:
                break
        # Now we have a sub-tree
        candidate_tree = candidate_tree[2]
        args_list = get_args(base_tree)
        if len(args_list) == 0:
            continue
        ast_match = True
        for arg in args_list:
            if arg.decode().lstrip("'").rstrip("'") not in candidate_tree.text.decode():
                ast_match = False
                break
        if ast_match:
            return idx
    return -1


# Parse the dataset
def parse_dataset(args):
    # Read the api dataset
    api_database = []
    with open(args.api_dataset, "r") as f:
        for line in f:
            api_database.append(json.loads(line))

    # Read the question answer pair dataset
    qa_pairs = []
    with open(args.apibench, "r") as f:
        for line in f:
            qa_pairs.append(json.loads(line)["api_data"])

    # Read the language model response dataset
    llm_responses = []
    with open(args.llm_responses, "r") as f:
        for line in f:
            llm_responses.append(json.loads(line))

    # Parse all APIs to AST trees
    ast_database = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        ast_trees = executor.map(ast_parse, (data["api_call"] for data in api_database))
        for ast_tree in ast_trees:
            ast_database.append(ast_tree)

    return api_database, qa_pairs, llm_responses, ast_database


def process_response(response, api_database, qa_pairs, ast_database):
    # Read the line from JSON file
    try:
        output = response["text"]
    except:
        print("Error: cannot parse line ", response)
        return False, False

    # Index the "api_call" domain
    output = output.split("api_call")
    if len(output) == 1:
        return False, False
    else:
        output = output[1].split("api_provider")[0]
        if ":" not in output:
            start = 0
        else:
            start = output.index(":")
        if ")" not in output:
            end = -2
        else:
            end = output.rindex(")")
        api_call = output[start + 2 : end + 1]

    # Parse the api_call into AST tree
    ast_tree = ast_parse(api_call)
    # Search for a subtree
    ast_subtree_list = get_all_sub_trees(ast_tree)
    # Check which ast tree is matching
    database_index = ast_check(ast_subtree_list, ast_database)
    # We cannot index this ast in our database
    if database_index == -1:
        return False, True
    # We index our reference api_call
    ref_api_call = api_database[database_index]
    # Check for functionality
    if ref_api_call["domain"] == qa_pairs[response["question_id"] - 1]["domain"]:
        return True, False
    else:
        return False, False



def eval_ast(dataset):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if dataset == "torchhub":
        api_dataset = "../../data/api/torchhub_api.jsonl"
        apibench = "../../data/apibench/torchhub_eval.json"
        llm_responses= "torchhub_llm_output.jsonl"
        
    elif dataset == "tensorhub":
        api_dataset = "../../data/api/tensorflowhub_api.jsonl"
        apibench = "../../data/apibench/tensorflow_eval.json"
        llm_responses= "tensorhub_llm_output.jsonl"

    elif dataset == "huggingface":    
        api_dataset = "../../data/api/huggingface_api.jsonl"
        apibench = "../../data/apibench/huggingface_eval.json"
        llm_responses= "huggingface_llm_output.jsonl"


    args = SimpleNamespace(
        api_dataset= os.path.join(current_dir, api_dataset),
        apibench = os.path.join(current_dir, apibench),
        llm_responses = os.path.join(current_dir, llm_responses)
    )
    # Read datasets
    api_database, qa_pairs, llm_responses, ast_database = parse_dataset(args)

    # Check correctness
    total_correct = 0
    total_hallucination = 0
    num_responses = len(llm_responses)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [
            executor.submit(
                process_response,
                response,
                api_database,
                qa_pairs,
                ast_database,
            )
            for response in llm_responses
        ]

        for result in concurrent.futures.as_completed(results):
            correct, hallucination = result.result()
            if correct:
                total_correct += 1
            if hallucination:
                total_hallucination += 1

    print("Final Functionality accuracy:", total_correct / num_responses)
    print("Final hallucination:", total_hallucination / num_responses)
    return total_correct / num_responses

