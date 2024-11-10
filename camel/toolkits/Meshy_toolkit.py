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

import os
from typing import Any, Dict

import requests

from camel.toolkits.base import BaseToolkit

"""
How do you store the task ids?
"""


class MeshyToolkit(BaseToolkit):
    r"""A class representing a toolkit for 3D model generation using Meshy.

    This class provides methods that handle text/image to 3D model
    generation using Meshy.

    Ref: https://docs.meshy.ai/api-text-to-3d-beta#create-a-text-to-3d-preview-task
    """

    def __init__(self):
        """
        Initializes the MeshyToolkit with the API key from the environment.
        """
        self.api_key = os.getenv('MESHY_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key not found. Please set environment variable."
            )

    def generate_3d_preview(
        self, prompt: str, art_style: str, negative_prompt: str
    ) -> Dict[str, Any]:
        """
        Generates a 3D preview using the Meshy API.

        Args:
            prompt (str): Description of the object.
            art_style (str): Art style for the 3D model.
            negative_prompt (str): What the model should not look like.

        Returns:
            Dict[str, Any]: The result property of the response contains the
                task id of the newly created Text to 3D task.
        """
        payload = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": art_style,
            "negative_prompt": negative_prompt,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.post(
            "https://api.meshy.ai/v2/text-to-3d",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def refine_3d_model(self, preview_task_id: str) -> Dict[str, Any]:
        """
        Refines a 3D model using the Meshy API.

        Args:
            preview_task_id (str): The task ID of the preview to refine.

        Returns:
            Dict[str, Any]: The response from the Meshy API.
        """
        payload = {"mode": "refine", "preview_task_id": preview_task_id}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.post(
            "https://api.meshy.ai/v2/text-to-3d",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieves the status or result of a specific 3D model generation task
        using the Meshy API.

        Args:
            task_id (str): The ID of the task to retrieve.

        Returns:
            Dict[str, Any]: The response from the Meshy API.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.get(
            f"https://api.meshy.ai/v2/text-to-3d/{task_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def main():
    # Create an instance of MeshyToolkit
    toolkit = MeshyToolkit()

    # Example data for testing
    prompt = "A figuring of Tin tin the cartoon character"
    art_style = "realistic"
    negative_prompt = "low quality, low resolution, low poly, ugly"

    try:
        # Test generate_3d_preview
        preview_response = toolkit.generate_3d_preview(
            prompt, art_style, negative_prompt
        )
        print("3D Preview Response:", preview_response)

        # Assuming the preview_response contains a task ID for refinement
        preview_task_id = str(preview_response.get("result"))
        print("Preview Task ID:", preview_task_id, type(preview_task_id))
        if preview_task_id:
            get_task_status = toolkit.get_task_status(preview_task_id)
            print("Get Task Status Response:", get_task_status)
            # Test refine_3d_model
            refine_response = toolkit.refine_3d_model(preview_task_id)
            print("Refine Model Response:", refine_response)

            # Test get_task_status
            status_response = toolkit.get_task_status(preview_task_id)
            print("Task Status Response:", status_response)
        else:
            print("No task ID found in preview response.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
