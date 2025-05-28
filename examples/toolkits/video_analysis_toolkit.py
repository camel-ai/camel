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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import VideoAnalysisToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

video_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Initialize the VideoAnalysisToolkit with the model
# Note: Audio transcription is disabled for faster processing
video_toolkit = VideoAnalysisToolkit(
    model=video_model,
    use_audio_transcription=False,
)

# Create an agent with the video toolkit's tools
agent = ChatAgent(
    system_message="You are a helpful assistant that can analyze videos.",
    model=model,
    tools=[*video_toolkit.get_tools()],
)

# Example video URL (Very short sample video)
video_url = "https://www.youtube.com/watch?v=kQ_7GtE529M"
question = "What is shown in the first few seconds of this video?"

# Use the toolkit directly for faster processing with fewer frames
print("Analyzing video...")
result = video_toolkit.ask_question_about_video(
    video_path=video_url,
    question=question,
)

print("Video Analysis Result:")
print("-" * 50)
print(result)
print("-" * 50)
"""
==========================================================================
Analyzing video...
[youtube] Extracting URL: https://www.youtube.com/watch?v=kQ_7GtE529M
[youtube] kQ_7GtE529M: Downloading webpage
[youtube] kQ_7GtE529M: Downloading ios player API JSON
[youtube] kQ_7GtE529M: Downloading mweb player API JSON
[youtube] kQ_7GtE529M: Downloading m3u8 information
[info] kQ_7GtE529M: Downloading 1 format(s): 247+251
[download] Destination: /private/var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/
T/tmp4plhd3s3/Douchebag Bison.f247.webm
[download] 100% of    1.95MiB in 00:00:01 at 1.18MiB/s
[download] Destination: /private/var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/
T/tmp4plhd3s3/Douchebag Bison.f251.webm
[download] 100% of  303.08KiB in 00:00:00 at 490.62KiB/s
[Merger] Merging formats into "/private/var/folders/93/
f_71_t957cq9cmq2gsybs4_40000gn/T/tmp4plhd3s3/Douchebag Bison.webm"
Deleting original file /private/var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/
T/tmp4plhd3s3/Douchebag Bison.f251.webm (pass -k to keep)
Deleting original file /private/var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/
T/tmp4plhd3s3/Douchebag Bison.f247.webm (pass -k to keep)
2025-03-09 21:17:08,036 - pyscenedetect - ERROR - VideoManager is deprecated 
and will be removed.
2025-03-09 21:17:08,060 - pyscenedetect - INFO - Loaded 1 video, framerate: 30.
000 FPS, resolution: 1280 x 720
2025-03-09 21:17:08,061 - pyscenedetect - INFO - Duration set, start: None, 
duration: None, end: None.
2025-03-09 21:17:08,061 - pyscenedetect - INFO - Detecting scenes...
2025-03-09 21:17:09,065 - camel.camel.toolkits.video_analysis_toolkit - 
WARNING - No scenes detected in video, capturing frames at regular intervals
Video Analysis Result:
--------------------------------------------------
### Visual Analysis

1. **Identified Entities**:
   - **Wolves**: Multiple wolves are visible in the frames, characterized by 
   their grayish fur, slender bodies, and bushy tails. They appear to be in a 
   pack, indicating social behavior.
   - **Bison**: A bison is present, identifiable by its large size, shaggy 
   brown fur, and distinctive hump on its back. The bison is significantly 
   larger than the wolves.

2. **Key Attributes**:
   - **Wolves**: 
     - Size: Smaller than the bison, typically around 26-32 inches tall at the 
     shoulder.
     - Color: Predominantly gray with some variations in fur color.
     - Behavior: The wolves are shown moving in a coordinated manner, 
     suggesting they are hunting or scavenging.
   - **Bison**:
     - Size: Much larger, can weigh up to 2,000 pounds.
     - Color: Dark brown, with a thick coat.
     - Behavior: The bison appears to be stationary or moving slowly, possibly 
     in a defensive posture.

3. **Groupings and Interactions**:
   - The wolves are seen surrounding the bison, indicating a predatory 
   behavior. The interaction suggests a hunting scenario, where the wolves are 
   attempting to take down or scavenge from the bison.

### Audio Integration
- **No audio transcription available**: Therefore, the analysis relies solely 
on visual observations.

### Detailed Reasoning and Justification
- **Identification of Species**:
  - The wolves are identified by their physical characteristics and social 
  behavior, which is typical of pack animals. Their movement patterns and 
  proximity to the bison indicate a hunting strategy.
  - The bison is easily distinguishable due to its size and unique physical 
  features, such as the hump and thick fur.

### Comprehensive Answer
- **Total Number of Distinct Species**: 2 (Wolves and Bison)
- **Defining Characteristics**:
  - **Wolves**: Gray fur, slender build, social behavior in a pack.
  - **Bison**: Large size, shaggy brown fur, distinctive hump.

### Important Considerations
- The wolves exhibit coordinated movement, which is crucial for hunting, while 
the bison's size and defensive posture highlight its role as prey in this 
scenario. The visual cues of size, color, and behavior effectively distinguish 
these two species in the context of a predatory interaction.
==========================================================================
"""
