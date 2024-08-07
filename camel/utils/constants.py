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


class Constants:
    # This value defines the default size (both width and height) for images
    # extracted from a video.
    VIDEO_DEFAULT_IMAGE_SIZE = 768

    # This value defines the interval (in number of frames) at which images
    # are extracted from the video.
    VIDEO_IMAGE_EXTRACTION_INTERVAL = 50

    # default plug of imageio to read video
    VIDEO_DEFAULT_PLUG_PYAV = "pyav"

    # return response with json format
    FUNC_NAME_FOR_STRUCTURE_OUTPUT = "return_json_response"
