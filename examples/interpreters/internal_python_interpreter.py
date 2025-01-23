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

from camel.interpreters import InternalPythonInterpreter

safe_interpreter = InternalPythonInterpreter()
unsafe_interpreter = InternalPythonInterpreter(unsafe_mode=True)

safe_result = safe_interpreter.execute(
    "x = input_variable", state={"input_variable": 10}
)
print(safe_result)

'''
===============================================================================
10
===============================================================================
'''

unsafe_result = unsafe_interpreter.run(
    "[x * 2 for x in range(3)]", code_type="python"
)
print(unsafe_result)

'''
===============================================================================
[0, 2, 4]
===============================================================================
'''
