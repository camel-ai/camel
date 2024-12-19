# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# This is file is modified from the
# evaluators in the original repo
# https://github.com/ShishirPatil/gorilla


# Get all the subtrees given a root_node
def get_all_sub_trees(root_node):
    node_stack = []
    sub_tree_sexp_list = []
    depth = 1
    # text = root_node.text
    node_stack.append([root_node, depth])
    while len(node_stack) != 0:
        cur_node, cur_depth = node_stack.pop()
        if cur_node.child_count > 0:
            sub_tree_sexp_list.append(
                [
                    str(cur_node),
                    cur_depth,
                    cur_node,
                    cur_node.children[0].text,
                ]
            )
        else:
            sub_tree_sexp_list.append(
                [str(cur_node), cur_depth, cur_node, None]
            )
        for child_node in cur_node.children:
            if len(child_node.children) != 0:
                depth = cur_depth + 1
                node_stack.append([child_node, depth])
    return sub_tree_sexp_list


# Parse the program into AST trees
def ast_parse(candidate):
    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)

    candidate_tree = parser.parse(bytes(candidate, "utf8")).root_node
    return candidate_tree


# Get all the arguments in the ast tree
def get_args(node, dataset_name):
    if node.child_count == 0:
        return []
    args_list = []
    if dataset_name == "huggingface":
        for child in node.children[0].children[0].children[1].children:
            if "=" in child.text.decode():
                args_list.append(child.children[2].text)
            elif (
                child.text.decode() != "("
                and child.text.decode() != ")"
                and child.text.decode() != ","
            ):
                args_list.append(child.text)
    elif dataset_name == "tensorflowhub":
        for child in node.children[0].children[0].children[1].children:
            if (
                'model=' in child.text.decode()
                or 'model =' in child.text.decode()
            ):
                args_list.append(child.children[2].text)
            elif (
                child.text.decode() != "("
                and child.text.decode() != ")"
                and child.text.decode() != ","
            ):
                args_list.append(child.text)
    elif dataset_name == "torchhub":
        for child in node.children[0].children[0].children[1].children:
            if (
                "repo_or_dir" in child.text.decode()
                or "model" in child.text.decode()
            ):
                args_list.append(child.children[2].text)
    return args_list


# Check if there is an api match
def ast_check(candidate_subtree_list, base_tree_list, dataset_name):
    for idx, base_tree in enumerate(base_tree_list):
        if base_tree.children[0].children[0].child_count == 0:
            continue
        api_name = base_tree.children[0].children[0].children[0].text
        for candidate_tree in candidate_subtree_list:
            if candidate_tree[3] == api_name:
                break
        # Now we have a sub-tree
        candidate_tree = candidate_tree[2]
        args_list = get_args(base_tree, dataset_name)
        if len(args_list) == 0:
            continue
        ast_match = True
        for arg in args_list:
            if (
                arg.decode().lstrip("'").rstrip("'")
                not in candidate_tree.text.decode()
            ):
                ast_match = False
                break
        if ast_match:
            return idx
    return -1


def evaluate_response(
    response, question_id, dataset_name, api_database, qa_pairs, ast_database
):
    try:
        # Index the "api_call" domain
        output = response.split("api_call")
        if len(output) == 1:
            api_call = output[0]
        else:
            # Parse the output
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

        try:
            ast_tree = ast_parse(api_call)
        except Exception as parse_error:
            print(f"Error parsing api_call: {api_call}, error: {parse_error}")
            return parse_error, False, False
        # Search for a subtree
        ast_subtree_list = get_all_sub_trees(ast_tree)
        # Check which ast tree is matching
        database_index = ast_check(
            ast_subtree_list, ast_database, dataset_name
        )
        # We cannot index this ast in our database
        if database_index == -1:
            halluncination = True
            correct = False
        # We index our reference api_call
        ref_api_call = api_database[database_index]
        # Check for functionality
        if ref_api_call['domain'] == qa_pairs[question_id - 1]['domain']:
            correct = True
            halluncination = False
        else:
            return None, False, False
    except Exception as e:
        print(f'Error parsing response: {response}, error: {e}')
        return e, False, False

    return None, correct, halluncination
