# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import os
from functools import wraps
from typing import Callable, List


def create_function_cacher(
    cache_file: str,
) -> Callable[[List[Callable]], List[Callable]]:
    def load_cache() -> dict:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(cache: dict):
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    cache = load_cache()

    def cache_wrapper(func: Callable) -> Callable:
        @wraps(func)
        def wrapped(*args, **kwargs):
            # Create a unique key for this function call
            key = f"{func.__name__}:{args!s}:{kwargs!s}"

            if key in cache:
                print(f"Cache hit for {func.__name__}")
                return cache[key]

            result = func(*args, **kwargs)
            cache[key] = result
            save_cache(cache)
            print(f"Cache miss for {func.__name__}, result cached")
            return result

        return wrapped

    def wrap_functions(functions: List[Callable]) -> List[Callable]:
        return [cache_wrapper(func) for func in functions]

    return wrap_functions
