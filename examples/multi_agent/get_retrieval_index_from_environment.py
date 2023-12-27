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
from colorama import Fore

from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model_type=model_type, model_config=model_config_description)

    target_labels = [
        "apple", "computer", "car", "python", "ocean", "piano", "science",
        "mathematics", "physics", "astronomy", "history", "philosophy",
        "literature", "biology", "chemistry", "art", "music", "theater",
        "architecture", "medicine"
    ]
    labels_sets = [[
        "fruit", "banana", "apple", "orange", "grape", "berry", "mango",
        "kiwi", "cherry", "pineapple"
    ],
                   [
                       "laptop", "PC", "mac", "computer", "tablet",
                       "mainframe", "workstation", "supercomputer",
                       "chromebook", "notebook"
                   ],
                   [
                       "vehicle", "truck", "bike", "motorcycle", "car", "bus",
                       "airplane", "helicopter", "scooter", "boat"
                   ],
                   [
                       "java", "C++", "python", "javascript", "ruby", "perl",
                       "php", "swift", "kotlin", "typescript"
                   ],
                   [
                       "sea", "ocean", "lake", "river", "pond", "bay", "gulf",
                       "stream", "creek", "lagoon"
                   ],
                   [
                       "guitar", "violin", "drums", "piano", "trumpet",
                       "flute", "cello", "harp", "saxophone", "tuba"
                   ],
                   [
                       "biology", "ecology", "botany", "zoology", "genetics",
                       "microbiology", "anatomy", "physiology", "neuroscience",
                       "paleontology"
                   ],
                   [
                       "algebra", "geometry", "calculus", "mathematics",
                       "statistics", "trigonometry", "arithmetic", "analysis",
                       "number theory", "discrete math"
                   ],
                   [
                       "astronomy", "cosmology", "planets", "galaxies",
                       "space", "astrophysics", "meteorology", "geology",
                       "seismology", "climatology"
                   ],
                   [
                       "history", "ancient", "medieval", "renaissance",
                       "modern", "prehistoric", "industrial revolution",
                       "enlightenment", "cold war", "contemporary"
                   ]]

    target_labels_indices, labels_sets_indices, target_retrieved_labels, \
        labels_retrieved_sets = (
            role_assignment_agent.get_retrieval_index_from_environment(
                labels_sets=labels_sets,
                target_labels=target_labels))

    print(Fore.GREEN + f"Target retrieved labels:\n{target_retrieved_labels}")
    print(Fore.GREEN + f"Target labels indices:\n{target_labels_indices}")
    print(Fore.CYAN + f"Labels retrieved sets:\n{labels_retrieved_sets}")
    print(Fore.CYAN + f"Labels sets indices:\n{labels_sets_indices}")


if __name__ == "__main__":
    main()
