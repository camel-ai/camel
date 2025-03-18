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

import os
import time
import jwt
import json
import base64
import requests
import datetime
from typing import List, Optional, Literal, Union, Dict, Any, Tuple

# from PIL import Image

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import dependencies_required

logger = get_logger(__name__)

class VirtualTryOnToolkit(BaseToolkit):
    r"""A toolkit for virtual try-on using Keling AI API.
    
    This toolkit provides functionality to generate virtual try-on images
    by combining clothing images with model images.

    To generate a virtual try-on image, you need to provide a clothing image path and pass it to the virtual_try_on method.
    The model image and other parameters are pre-configured so you don't need to provide them.
    """
    
    def __init__(
        self,
        access_key: str = "", # get from https://www.klingai.com/dashboard/api (replace with your own)
        secret_key: str = "", # get from https://www.klingai.com/dashboard/api (replace with your own)
        model_image_path: str = "", # your virtual "model" image path (replace with your own)
        output_dir: str = "./tmp/fitting_room", # the directory to save the generated try-on images
        api_domain: str = "https://api.klingai.com", # the API domain
        default_model_name: str = "kolors-virtual-try-on-v1-5" # the default model name
    ):
        """Initialize the VirtualTryOnToolkit.
        
        Args:
            access_key: Keling AI API access key. If not provided, will try to load from 
                environment variable KELING_ACCESS_KEY.
            secret_key: Keling AI API secret key. If not provided, will try to load from
                environment variable KELING_SECRET_KEY.
            model_image_path: Path to the default model image. If not provided, will try
                to load from environment variable KELING_MODEL_IMAGE.
            output_dir: Directory to save the generated images.
            api_domain: Keling AI API domain.
            default_model_name: Default Keling AI model name to use.
        """
        self.access_key = access_key or os.getenv("KELING_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("KELING_SECRET_KEY")
        self.model_image_path = model_image_path or os.getenv("KELING_MODEL_IMAGE")
        self.output_dir = output_dir
        self.api_domain = api_domain
        self.default_model_name = default_model_name
        
        if not self.access_key or not self.secret_key:
            logger.warning(
                "Keling AI API keys not found. Virtual try-on functionality will not work. "
                "Please provide access_key and secret_key or set environment variables "
                "KELING_ACCESS_KEY and KELING_SECRET_KEY."
            )
        
        if not self.model_image_path:
            logger.warning(
                "Default model image path not provided. "
                "Please provide model_image_path or set environment variable "
                "KELING_MODEL_IMAGE."
            )
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _generate_auth_token(self) -> str:
        """Generate JWT authentication token for Keling AI API.
        
        Returns:
            str: The JWT token.
        """
        headers = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + 1800,  # 30 minutes expiration
            "nbf": int(time.time()) - 5      # Valid from 5 seconds ago
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)
        return token
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert an image to base64 encoding.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            str: Base64 encoded image.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _poll_task_status(
        self, 
        task_id: str, 
        headers: Dict[str, str], 
        max_attempts: int = 30,
        poll_interval: int = 6,
    ) -> Dict[str, Any]:
        """Poll for task status until completion.
        
        Args:
            task_id: The ID of the task to poll.
            headers: HTTP headers for the request.
            max_attempts: Maximum number of polling attempts.
            poll_interval: Time between polling attempts in seconds.
            
        Returns:
            Dict[str, Any]: The task result data.
        
        Raises:
            Exception: If polling times out or the task fails.
        """
        status_url = f"{self.api_domain}/v1/images/kolors-virtual-try-on/{task_id}"
        
        attempts = 0
        while attempts < max_attempts:
            time.sleep(poll_interval)
            attempts += 1
            
            response = requests.get(status_url, headers=headers)
            status_data = response.json()
            
            logger.debug(f"Poll attempt {attempts}: {json.dumps(status_data, indent=2)}")
            
            task_status = status_data["data"]["task_status"]
            if task_status == "succeed":
                if "task_result" in status_data["data"] and "images" in status_data["data"]["task_result"]:
                    return status_data
                else:
                    logger.warning("任务成功但未找到图片URL，继续查询...")
            elif task_status == "failed":
                fail_msg = status_data["data"].get("task_status_msg", "未知错误")
                raise Exception(f"虚拟试衣任务失败: {fail_msg}")
            
            logger.debug(f"任务状态: {task_status}，继续等待...")
        
        raise Exception("等待任务完成超时")
    
    def _download_image(self, url: str, save_path: str) -> str:
        """Download an image from a URL and save it to disk.
        
        Args:
            url: URL of the image to download.
            save_path: Path to save the downloaded image.
            
        Returns:
            str: The path where the image was saved.
        
        Raises:
            Exception: If the download fails.
        """
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            logger.debug(f"图片已保存到: {save_path}")
            return save_path
        else:
            raise Exception(f"下载图片失败: HTTP {response.status_code}")
    
    @dependencies_required("jwt", "requests")
    def virtual_try_on(self, clothing_image_path: str) -> Dict[str, str]:
        """Generate a virtual try-on image by combining a clothing image with a model image.
        
        This simplified version only requires the clothing image path, using pre-configured 
        values for the model image and other parameters.
        
        Args:
            clothing_image_path: Path to the clothing image.
            
        Returns:
            Dict[str, str]: A dictionary containing:
                - "result_path": Path to the generated image
                - "status": Status message
                - "message": Detailed message
        
        Raises:
            Exception: If API keys are missing or the API call fails.
        """
        if not self.access_key or not self.secret_key:
            raise ValueError(
                "Keling AI API keys not provided. Please initialize the toolkit with "
                "valid access_key and secret_key or set environment variables."
            )
        
        # Verify model image is set
        if not self.model_image_path:
            raise ValueError(
                "Default model image path not set. Please provide model_image_path in the constructor "
                "or set environment variable KELING_MODEL_IMAGE."
            )
        
        # Verify input file exists
        if not os.path.exists(clothing_image_path):
            raise FileNotFoundError(f"Clothing image not found: {clothing_image_path}")
        
        if not os.path.exists(self.model_image_path):
            raise FileNotFoundError(f"Model image not found: {self.model_image_path}")
        
        # Generate output filename
        timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
        clothing_basename = os.path.basename(clothing_image_path).split('.')[0]
        output_filename = f"try_on_{clothing_basename}_{timestamp}.png"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Generate authentication token
        api_token = self._generate_auth_token()
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare request payload - strictly following test_keling_api.py format
        try:
            # Convert images to base64
            human_image = self._image_to_base64(self.model_image_path)
            cloth_image = self._image_to_base64(clothing_image_path)
            
            # Prepare payload according to API requirements
            payload = {
                "model_name": self.default_model_name,
                "human_image": human_image,
                "cloth_image": cloth_image
            }
            
            # Send API request
            request_url = f"{self.api_domain}/v1/images/kolors-virtual-try-on"
            response = requests.post(request_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"API调用失败: {response.status_code}, {response.text}")
            
            result = response.json()
            task_id = result["data"]["task_id"]
            logger.info(f"虚拟试衣任务已提交，任务ID: {task_id}")
            
            # Poll for task completion
            final_result = self._poll_task_status(task_id, headers)
            
            # Download the result image
            image_url = final_result["data"]["task_result"]["images"][0]["url"]
            saved_path = self._download_image(image_url, output_path)
            
            return {
                "result_path": saved_path,
                "status": "success",
                "message": "虚拟试衣完成"
            }
            
        except Exception as e:
            error_message = f"虚拟试衣失败: {str(e)}"
            logger.error(error_message)
            return {
                "result_path": "",
                "status": "error",
                "message": error_message
            }
    
    def get_tools(self) -> List[FunctionTool]:
        """Get the list of tools provided by this toolkit.
        
        Returns:
            List[FunctionTool]: List of function tools.
        """
        return [FunctionTool(self.virtual_try_on)] 