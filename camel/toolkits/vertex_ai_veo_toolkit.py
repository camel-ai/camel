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

import asyncio
import base64
import os
from typing import Any, Dict, List, Optional, Tuple

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import api_keys_required, dependencies_required

logger = get_logger(__name__)


@api_keys_required(
    [("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS")]
)
class VertexAIVeoToolkit(BaseToolkit):
    r"""A toolkit for interacting with Google Vertex AI Veo video generation.

    This toolkit provides methods for generating videos using Google's Veo,
    supporting both text-to-video and image-to-video generation with various
    customization options.
    """

    @dependencies_required('google-cloud-aiplatform')
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the Vertex AI Veo toolkit.

        Args:
            project_id (Optional[str]): Google Cloud project ID. If not
                provided,
                will use the default project from environment.
                (default: :obj:`None`)
            location (str): Google Cloud location for the API calls.
                (default: :obj:`"us-central1"`)
            timeout (Optional[float]): Request timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout)

        from google.cloud import aiplatform

        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location

        if not self.project_id:
            raise ValueError(
                "Project ID must be provided either as parameter or "
                "GOOGLE_CLOUD_PROJECT environment variable"
            )

        aiplatform.init(project=self.project_id, location=self.location)
        self.client = aiplatform.gapic.PredictionServiceClient()

    def generate_video_from_text(
        self,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        response_count: int = 1,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        person_generation: str = "allow_adult",
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Generate video from text prompt using Vertex AI Veo.

        Args:
            text_prompt (str): The text prompt to guide video generation.
            model_id (str): The Veo model ID to use. Options include
                "veo-2.0-generate-001" or "veo-3.0-generate-preview".
                (default: :obj:`"veo-2.0-generate-001"`)
            response_count (int): Number of videos to generate (1-4).
                (default: :obj:`1`)
            duration (int): Video duration in seconds (5-8).
                (default: :obj:`5`)
            aspect_ratio (str): Video aspect ratio. Options: "16:9", "9:16".
                (default: :obj:`"16:9"`)
            negative_prompt (Optional[str]): What to avoid in the video.
                (default: :obj:`None`)
            person_generation (str): Person safety setting. Options:
                "allow_adult", "dont_allow". (default: :obj:`"allow_adult"`)
            output_storage_uri (Optional[str]): Cloud Storage URI to save
                output videos. If not provided, returns video bytes.
                (default: :obj:`None`)

        Returns:
            Dict: Video generation response containing video data or URIs.
        """
        try:
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value

            # Construct the request
            endpoint = (
                f"projects/{self.project_id}/locations/{self.location}/"
                f"publishers/google/models/{model_id}"
            )

            # Build parameters
            parameters = {
                "aspectRatio": aspect_ratio,
                "personGeneration": person_generation,
            }

            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt

            # Build request body
            request_body = {
                "contents": [
                    {"role": "user", "parts": [{"text": text_prompt}]}
                ],
                "generationConfig": {
                    "responseCount": response_count,
                    "duration": duration,
                },
                "parameters": parameters,
            }

            if output_storage_uri:
                generation_config = request_body.setdefault(
                    "generationConfig", {}
                )
                if isinstance(generation_config, dict):
                    generation_config["outputStorageUri"] = output_storage_uri

            # Convert to protobuf format
            request_value = json_format.ParseDict(request_body, Value())

            # Make the API call
            response = self.client.predict(
                endpoint=endpoint,
                instances=[request_value],
                timeout=self.timeout,
            )

            return self._parse_video_response(response)

        except Exception as e:
            logger.error(f"Error generating video from text: {e}")
            return {"error": str(e)}

    def generate_video_from_image(
        self,
        image_path: str,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        response_count: int = 1,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        person_generation: str = "allow_adult",
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Generate video from image and text prompt using Vertex AI Veo.

        Args:
            image_path (str): Path to the input image file (local or GCS URI).
            text_prompt (str): The text prompt to guide video generation.
            model_id (str): The Veo model ID to use.
                (default: :obj:`"veo-2.0-generate-001"`)
            response_count (int): Number of videos to generate (1-4).
                (default: :obj:`1`)
            duration (int): Video duration in seconds (5-8).
                (default: :obj:`5`)
            aspect_ratio (str): Video aspect ratio. Options: "16:9", "9:16".
                (default: :obj:`"16:9"`)
            negative_prompt (Optional[str]): What to avoid in the video.
                (default: :obj:`None`)
            person_generation (str): Person safety setting.
                (default: :obj:`"allow_adult"`)
            output_storage_uri (Optional[str]): Cloud Storage URI to save
                output videos. (default: :obj:`None`)

        Returns:
            Dict: Video generation response containing video data or URIs.
        """
        try:
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value

            # Read and encode image
            image_data, mime_type = self._process_image(image_path)

            # Construct the request
            endpoint = (
                f"projects/{self.project_id}/locations/{self.location}/"
                f"publishers/google/models/{model_id}"
            )

            # Build parameters
            parameters = {
                "aspectRatio": aspect_ratio,
                "personGeneration": person_generation,
            }

            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt

            # Build request body with image
            request_body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": image_data,
                                }
                            },
                            {"text": text_prompt},
                        ],
                    }
                ],
                "generationConfig": {
                    "responseCount": response_count,
                    "duration": duration,
                },
                "parameters": parameters,
            }

            if output_storage_uri:
                generation_config = request_body.setdefault(
                    "generationConfig", {}
                )
                if isinstance(generation_config, dict):
                    generation_config["outputStorageUri"] = output_storage_uri

            # Convert to protobuf format
            request_value = json_format.ParseDict(request_body, Value())

            # Make the API call
            response = self.client.predict(
                endpoint=endpoint,
                instances=[request_value],
                timeout=self.timeout,
            )

            return self._parse_video_response(response)

        except Exception as e:
            logger.error(f"Error generating video from image: {e}")
            return {"error": str(e)}

    def extend_video(
        self,
        video_uri: str,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Extend an existing video using Vertex AI Veo.

        Args:
            video_uri (str): Cloud Storage URI of the video to extend.
            text_prompt (str): The text prompt to guide video extension.
            model_id (str): The Veo model ID to use.
                (default: :obj:`"veo-2.0-generate-001"`)
            duration (int): Duration to extend in seconds (5-8).
                (default: :obj:`5`)
            aspect_ratio (str): Video aspect ratio.
                (default: :obj:`"16:9"`)
            negative_prompt (Optional[str]): What to avoid in the extension.
                (default: :obj:`None`)
            output_storage_uri (Optional[str]): Cloud Storage URI to save
                extended video. (default: :obj:`None`)

        Returns:
            Dict: Video extension response containing video data or URIs.
        """
        try:
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value

            # Construct the request
            endpoint = (
                f"projects/{self.project_id}/locations/{self.location}/"
                f"publishers/google/models/{model_id}"
            )

            # Build parameters
            parameters = {
                "aspectRatio": aspect_ratio,
                "videoToExtend": video_uri,
            }

            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt

            # Build request body
            request_body = {
                "contents": [
                    {"role": "user", "parts": [{"text": text_prompt}]}
                ],
                "generationConfig": {
                    "duration": duration,
                },
                "parameters": parameters,
            }

            if output_storage_uri:
                generation_config = request_body.setdefault(
                    "generationConfig", {}
                )
                if isinstance(generation_config, dict):
                    generation_config["outputStorageUri"] = output_storage_uri

            # Convert to protobuf format
            request_value = json_format.ParseDict(request_body, Value())

            # Make the API call
            response = self.client.predict(
                endpoint=endpoint,
                instances=[request_value],
                timeout=self.timeout,
            )

            return self._parse_video_response(response)

        except Exception as e:
            logger.error(f"Error extending video: {e}")
            return {"error": str(e)}

    async def agenerate_video_from_text(
        self,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        response_count: int = 1,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        person_generation: str = "allow_adult",
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Async version of generate_video_from_text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_video_from_text,
            text_prompt,
            model_id,
            response_count,
            duration,
            aspect_ratio,
            negative_prompt,
            person_generation,
            output_storage_uri,
        )

    async def agenerate_video_from_image(
        self,
        image_path: str,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        response_count: int = 1,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        person_generation: str = "allow_adult",
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Async version of generate_video_from_image."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_video_from_image,
            image_path,
            text_prompt,
            model_id,
            response_count,
            duration,
            aspect_ratio,
            negative_prompt,
            person_generation,
            output_storage_uri,
        )

    async def aextend_video(
        self,
        video_uri: str,
        text_prompt: str,
        model_id: str = "veo-2.0-generate-001",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        output_storage_uri: Optional[str] = None,
    ) -> Dict:
        r"""Async version of extend_video."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.extend_video,
            video_uri,
            text_prompt,
            model_id,
            duration,
            aspect_ratio,
            negative_prompt,
            output_storage_uri,
        )

    def _process_image(self, image_path: str) -> Tuple[str, str]:
        r"""Process image file and return base64 encoded data and MIME type."""
        if image_path.startswith('gs://'):
            # Handle Google Cloud Storage URIs
            from google.cloud import storage

            # Parse GCS URI
            parts = image_path[5:].split('/', 1)
            bucket_name = parts[0]
            blob_name = parts[1]

            # Download image from GCS
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            image_bytes = blob.download_as_bytes()

            # Determine MIME type from file extension
            if blob_name.lower().endswith('.png'):
                mime_type = "image/png"
            elif blob_name.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            else:
                raise ValueError("Unsupported image format. Use PNG or JPEG.")

        else:
            # Handle local file paths
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Determine MIME type from file extension
            if image_path.lower().endswith('.png'):
                mime_type = "image/png"
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            else:
                raise ValueError("Unsupported image format. Use PNG or JPEG.")

        # Encode to base64
        image_data = base64.b64encode(image_bytes).decode('utf-8')

        return image_data, mime_type

    def _parse_video_response(self, response: Any) -> Dict[str, Any]:
        r"""Parse the video generation response."""
        try:
            result: Dict[str, Any] = {
                "success": True,
                "videos": [],
                "metadata": {},
            }

            # Extract prediction results
            if hasattr(response, 'predictions'):
                for prediction in response.predictions:
                    # Convert prediction to dict if needed
                    if hasattr(prediction, 'struct_value'):
                        pred_dict = dict(prediction.struct_value)
                    else:
                        pred_dict = prediction

                    videos_list = result["videos"]
                    if isinstance(videos_list, list):
                        videos_list.append(pred_dict)

            # Extract metadata if available
            if hasattr(response, 'metadata'):
                result["metadata"] = dict(response.metadata)

            return result

        except Exception as e:
            logger.error(f"Error parsing video response: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_response": str(response),
            }

    def get_tools(self) -> List[FunctionTool]:
        r"""Get a list of tools for video generation with Vertex AI Veo.

        Returns:
            List[FunctionTool]: List of available function tools.
        """
        return [
            FunctionTool(self.generate_video_from_text),
            FunctionTool(self.generate_video_from_image),
            FunctionTool(self.extend_video),
        ]

    def get_async_tools(self) -> List[FunctionTool]:
        r"""Get a list of async tools for video generation with Vertex AI Veo.

        Returns:
            List[FunctionTool]: List of available async function tools.
        """
        return [
            FunctionTool(self.agenerate_video_from_text),
            FunctionTool(self.agenerate_video_from_image),
            FunctionTool(self.aextend_video),
        ]
