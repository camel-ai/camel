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

# The code below is adapted from coderag-bench
# https://github.com/code-rag-bench/code-rag-bench/blob/main/retrieval/create/utils.py

import csv
import os

import jsonlines


def load_jsonlines(file):
    with jsonlines.open(file, 'r') as jsonl_f:
        lst = [obj for obj in jsonl_f]
    return lst


def save_file_jsonl(data, fp):
    with jsonlines.open(fp, mode='w') as writer:
        writer.write_all(data)


def save_tsv_dict(data, fp, fields):
    # build dir
    dir_path = os.path.dirname(fp)
    os.makedirs(dir_path, exist_ok=True)

    # writing to csv file
    with open(fp, 'w') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fields,
            delimiter='\t',
        )
        writer.writeheader()
        writer.writerows(data)


def cost_esitmate(path):
    corpus = load_jsonlines(os.path.join(path, "corpus.jsonl"))
    queries = load_jsonlines(os.path.join(path, "queries.jsonl"))
    num_corpus_words = 0
    num_queries_words = 0
    for item in tqdm(corpus):
        num_corpus_words += len(item["text"].split(" "))
    for item in tqdm(queries):
        num_queries_words += len(item["text"].split(" "))
    print(len(corpus))
    print(len(queries))
    print(num_corpus_words)
    print(num_queries_words)
