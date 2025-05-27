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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import BohriumToolkit
from camel.types import ModelPlatformType, ModelType

# Convert the example input into audio and store it locally
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)
# Create the BohriumToolkit with our reasoning model
bohrium_toolkit = BohriumToolkit(
    yaml_path="examples/toolkits/bohrium_toolkit_example.yaml",
    api_key="xxx",
    project_id=617833,
)

# Create a ChatAgent with the audio toolkit tools
agent = ChatAgent(
    model=model,
    tools=[*bohrium_toolkit.get_tools()],
)

response = agent.step(
    "Submit a job to Bohrium,and help me check the job status"
)
print(response.msgs[0].content)
print("\n")

"""
==========================================================================
Your job has been submitted successfully with the following details:

- **Job ID**: 18105226
- **Bohr Job ID**: 15485870
- **Job Group ID**: 14695383
- **Project ID**: 617833
- **User ID**: 615385
- **Platform**: Ali
- **Status**: The job is currently in the initial state (status code 0).
- **Create Time**: 2025-05-14 14:36:14
- **Update Time**: 2025-05-14 14:36:15
- **Job Name**: test-bohr-job
- **Project Name**: CAMEL-AI
- **User Name**: CAMEL-AI
- **Image Name**: registry.dp.tech/dptech/lammps:29Sep2021
- **Command**: mpirun -n 2 lmp_mpi -i in.shear
- **Machine Type**: c2_m4_cpu (2 CPU, 4 GB Memory)
- **Region**: cn-zhangjiakou

The job is currently pending or initializing. I will keep you updated on 
its progress. If you need further assistance, feel free to ask!
If you want to monitor the job's status or logs, let me know and I can 
assist you with that as well.
==========================================================================
"""
