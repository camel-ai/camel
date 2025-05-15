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
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
#
# This file is adapted from:
# https://github.com/code-rag-bench/code-rag-bench/blob/main/generation/eval/
#   tasks/custom_metrics/code_eval.py
# which is based on OpenAI's HumanEval evaluation code:
# https://github.com/openai/human-eval
#
# Original licenses: Apache 2.0 (code-rag-bench), MIT (OpenAI)
# We thank the original authors for their implementation.

import itertools
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from .execute import check_correctness

_WARNING = """
##############################################################################
                                  !!!WARNING!!!
##############################################################################
The "code_eval" metric executes untrusted model-generated code in Python.
Although it is highly unlikely that model-generated code will do something
overtly malicious in response to this test suite, model-generated code may act
destructively due to a lack of model capability or alignment.
Users are strongly encouraged to sandbox this evaluation suite so that it
does not perform destructive actions on their host or network. For more
information on how OpenAI sandboxes its code, see the paper "Evaluating Large
Language Models Trained on Code" (https://arxiv.org/abs/2107.03374).

Once you have read this disclaimer and taken appropriate precautions,
set the environment variable HF_ALLOW_CODE_EVAL="1". Within Python you can to 
this with:

>>> import os
>>> os.environ["HF_ALLOW_CODE_EVAL"] = "1"

##############################################################################
"""


def compute_code_eval(
    predictions, references, k=None, num_workers=4, timeout=3.0
):
    r"""Compute pass@k metric for generated code using test scripts.

    Args:
        predictions (List[List[str]]): Model-generated code candidates.
        references (List[str]): Test scripts for checking correctness.
        k (Union[int, List[int]], optional): Values of k to evaluate.
            Defaults to [1, 10, 100].
        num_workers (int, optional): Number of threads for execution.
            Defaults to 4.
        timeout (float, optional): Timeout (in seconds) per run.
            Defaults to 3.0.

    Returns:
        Tuple[Dict[str, float], Dict[int, List[Tuple[int, Dict]]]]:
            pass@k scores and raw execution results per task.

    Raises:
        ValueError: If HF_ALLOW_CODE_EVAL is not set to "1".
        NotImplementedError: If run on Windows platform.

    Note:
        This function executes untrusted code. Use sandboxing.
    """
    if k is None:
        k = [1, 10, 100]

    if os.getenv("HF_ALLOW_CODE_EVAL", 0) != "1":
        raise ValueError(_WARNING)

    if os.name == "nt":
        raise NotImplementedError(
            "This metric is currently not supported on Windows."
        )

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        completion_id = Counter()
        n_samples = 0
        results = defaultdict(list)

        for task_id, (candidates, test_case) in enumerate(
            zip(predictions, references)
        ):
            for candidate in candidates:
                test_program = candidate + "\n" + test_case
                args = (test_program, timeout, task_id, completion_id[task_id])
                future = executor.submit(check_correctness, *args)
                futures.append(future)
                completion_id[task_id] += 1
                n_samples += 1

        for future in as_completed(futures):
            result = future.result()
            results[result["task_id"]].append(
                (result["completion_id"], result)
            )

    total, correct = [], []
    for result in results.values():
        result.sort()
        passed = [r[1]["passed"] for r in result]
        total.append(len(passed))
        correct.append(sum(passed))
    total = np.array(total)
    correct = np.array(correct)

    ks = k
    if not isinstance(ks, (list, tuple)):
        ks = [ks]
    pass_at_k = {
        f"pass@{k}": estimate_pass_at_k(total, correct, k).mean()
        for k in ks
        if (total >= k).all()
    }

    return pass_at_k, results


def estimate_pass_at_k(num_samples, num_correct, k):
    r"""Estimate pass@k based on sample and correctness statistics.

    Args:
        num_samples (Union[int, Sequence[int]]): Number of candidates.
        num_correct (Sequence[int]): Number of correct candidates.
        k (int): Number of top candidates to consider.

    Returns:
        np.ndarray: Estimated pass@k for each task.
    """

    def estimator(n: int, c: int, k: int) -> float:
        """Calculates 1 - comb(n - c, k) / comb(n, k)."""
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array(
        [
            estimator(int(n), int(c), k)
            for n, c in zip(num_samples_it, num_correct)
        ]
    )
