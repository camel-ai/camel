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
import unittest

import examples.evaluation.single_agent
import examples.misalignment.single_agent
import examples.single_agent


class TestSingleAgent(unittest.TestCase):

    def test_single_agent(self):
        examples.single_agent.main()

    def test_misalignment_single_agent(self):
        examples.misalignment.single_agent.main()

    def test_evaluation_single_agent(self):
        examples.evaluation.single_agent.main()
