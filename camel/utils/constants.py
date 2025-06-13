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


class Constants:
    r"""A class containing constants used in CAMEL."""

    # This value defines the default size (both width and height) for images
    # extracted from a video.
    VIDEO_DEFAULT_IMAGE_SIZE = 768

    # This value defines the interval (in number of frames) at which images
    # are extracted from the video.
    VIDEO_IMAGE_EXTRACTION_INTERVAL = 50

    # Default plug of imageio to read video
    VIDEO_DEFAULT_PLUG_PYAV = "pyav"

    # Return response with json format
    FUNC_NAME_FOR_STRUCTURED_OUTPUT = "return_json_response"

    # Default top k value for RAG
    DEFAULT_TOP_K_RESULTS = 1

    # Default similarity threshold value for RAG
    DEFAULT_SIMILARITY_THRESHOLD = 0.7

    # Default timeout threshold value
    TIMEOUT_THRESHOLD = 180.0
