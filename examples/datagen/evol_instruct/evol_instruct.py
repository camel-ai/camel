# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========


from camel.agents import ChatAgent
from camel.datagen.evol_instruct import EvolInstructPipeline

def main():
    """
    Example usage of EvolInstructPipeline with iterative and parallel evolution.
    """
    agent = ChatAgent()
    
    pipeline = EvolInstructPipeline()
    
    # Define evolution parameters
    num_generations = 2  # (width) number of generations per evolution
    num_evolutions = 3  # (depth) number of iterative evolutions
    method_dict = {
        0: 'in-breadth', 
        1: 'in-breadth', 
        2: 'in-depth'
    }
    keep_original = True  # keep original prompt in results
    chunk_size = 1  # control processing rate
    
    # setup pipeline
    pipeline = EvolInstructPipeline(
        agent=agent,
        seed='seed_tasks.jsonl',
        data_output_path='./data_output.json',
        method=method_dict,
        num_generations=num_generations,
        num_evolutions=num_evolutions,
        keep_original=keep_original,
        chunk_size=chunk_size,
    )
    
    # generate instructions
    pipeline.generate()


if __name__ == "__main__":
    main()
