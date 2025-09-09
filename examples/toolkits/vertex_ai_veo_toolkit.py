#!/usr/bin/env python3
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
"""
Example usage of VertexAIVeoToolkit for video generation.

This example demonstrates how to use Google's Vertex AI Veo models to generate
videos from text prompts, images, and extend existing videos.

Prerequisites:
1. Install google-cloud-aiplatform: pip install google-cloud-aiplatform
2. Set up Google Cloud authentication:
   - gcloud auth login
   - gcloud config set project YOUR_PROJECT_ID
   Or set GOOGLE_APPLICATION_CREDENTIALS environment variable
3. Enable Vertex AI API in your Google Cloud project
4. Set up billing for your project (video generation incurs costs)

Environment Variables:
- GOOGLE_CLOUD_PROJECT: Your Google Cloud project ID
- GOOGLE_APPLICATION_CREDENTIALS: Path to service account key (optional)
"""

import asyncio


def basic_text_to_video_example():
    r"""Basic example of generating video from text prompt."""
    from camel.toolkits import VertexAIVeoToolkit

    print("🎬 Basic Text-to-Video Generation Example")

    # Initialize toolkit
    toolkit = VertexAIVeoToolkit(
        project_id="your-project-id",  # Replace with your project ID
        location="us-central1",
    )

    # Generate video from text
    result = toolkit.generate_video_from_text(
        text_prompt="A peaceful sunset over a calm ocean with gentle waves",
        model_id="veo-2.0-generate-001",
        duration=5,
        aspect_ratio="16:9",
        response_count=1,
    )

    print(f"Generation result: {result}")
    return result


def advanced_text_to_video_example():
    r"""Advanced example with more parameters."""
    from camel.toolkits import VertexAIVeoToolkit

    print("🎬 Advanced Text-to-Video Generation Example")

    toolkit = VertexAIVeoToolkit(project_id="your-project-id")

    # Generate video with advanced settings
    result = toolkit.generate_video_from_text(
        text_prompt="A futuristic city with flying cars and neon lights, cyberpunk style",  # noqa: E501
        model_id="veo-3.0-generate-preview",  # Using latest model
        duration=8,  # Longer duration
        aspect_ratio="9:16",  # Vertical format for mobile
        response_count=2,  # Generate 2 variations
        negative_prompt="low quality, blurry, distorted",
        person_generation="dont_allow",  # No people in the video
        output_storage_uri="gs://your-bucket/videos/",  # Save to GCS
    )

    print(f"Advanced generation result: {result}")
    return result


def image_to_video_example():
    r"""Example of generating video from an image."""
    from camel.toolkits import VertexAIVeoToolkit

    print("🖼️ Image-to-Video Generation Example")

    toolkit = VertexAIVeoToolkit(project_id="your-project-id")

    # Generate video from image
    result = toolkit.generate_video_from_image(
        image_path="/path/to/your/image.jpg",  # Local path or GCS URI
        text_prompt="The scene comes to life with gentle movement and animation",  # noqa: E501
        model_id="veo-2.0-generate-001",
        duration=6,
        aspect_ratio="16:9",
    )

    print(f"Image-to-video result: {result}")
    return result


def video_extension_example():
    r"""Example of extending an existing video."""
    from camel.toolkits import VertexAIVeoToolkit

    print("🎞️ Video Extension Example")

    toolkit = VertexAIVeoToolkit(project_id="your-project-id")

    # Extend an existing video
    result = toolkit.extend_video(
        video_uri="gs://your-bucket/videos/original_video.mp4",
        text_prompt="The scene continues with more dramatic action",
        duration=5,
        aspect_ratio="16:9",
    )

    print(f"Video extension result: {result}")
    return result


async def async_video_generation_example():
    r"""Example of using async methods for concurrent video generation."""
    from camel.toolkits import VertexAIVeoToolkit

    print("⚡ Async Video Generation Example")

    toolkit = VertexAIVeoToolkit(project_id="your-project-id")

    # Generate multiple videos concurrently
    tasks = [
        toolkit.agenerate_video_from_text(
            "A serene mountain landscape at sunrise", duration=5
        ),
        toolkit.agenerate_video_from_text(
            "An underwater coral reef with colorful fish", duration=5
        ),
        toolkit.agenerate_video_from_text(
            "A bustling city street at night with traffic", duration=5
        ),
    ]

    # Wait for all videos to be generated
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        print(f"Video {i+1} result: {result}")

    return results


def agent_integration_example():
    r"""Example of using VertexAIVeoToolkit with CAMEL agents."""
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.toolkits import VertexAIVeoToolkit

    print("🤖 Agent Integration Example")

    # Initialize model and toolkit
    model = ModelFactory.create(
        model_platform="openai", model_type="gpt-4o-mini"
    )

    toolkit = VertexAIVeoToolkit(project_id="your-project-id")

    # Create agent with video generation tools
    agent = ChatAgent(
        model=model,
        tools=toolkit.get_tools(),
        system_message="""You are a video generation assistant. 
        You can help users create videos using Google's Vertex AI Veo models.
        Always explain the video generation process and parameters to users.""",  # noqa: E501
    )

    # Example conversation
    response = agent.step(
        "Create a 5-second video of a cat playing in a garden"
    )

    print(f"Agent response: {response.content}")
    return response


async def fastapi_integration_example():
    r"""Example of using the toolkit in a FastAPI application."""
    print("🌐 FastAPI Integration Example")

    # This shows how you would use it in FastAPI
    example_code = '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from camel.toolkits import VertexAIVeoToolkit

app = FastAPI()
toolkit = VertexAIVeoToolkit(project_id="your-project-id")

class VideoRequest(BaseModel):
    text_prompt: str
    duration: int = 5
    aspect_ratio: str = "16:9"
    model_id: str = "veo-2.0-generate-001"

@app.post("/generate-video")
async def generate_video(request: VideoRequest):
    try:
        result = await toolkit.agenerate_video_from_text(
            text_prompt=request.text_prompt,
            duration=request.duration,
            aspect_ratio=request.aspect_ratio,
            model_id=request.model_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-video-from-image")
async def generate_video_from_image(
    image_path: str,
    text_prompt: str,
    duration: int = 5
):
    try:
        result = await toolkit.agenerate_video_from_image(
            image_path=image_path,
            text_prompt=text_prompt,
            duration=duration
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    '''

    print("FastAPI integration code:")
    print(example_code)


def main():
    r"""Run all examples."""
    print("🎥 Vertex AI Veo Toolkit Examples")
    print("=" * 50)

    # Note: These examples require proper Google Cloud setup
    print("⚠️  Note: These examples require:")
    print("   1. Google Cloud project with Vertex AI API enabled")
    print("   2. Proper authentication setup")
    print("   3. Billing enabled (video generation incurs costs)")
    print()

    # Uncomment these lines when you have proper setup:
    # basic_text_to_video_example()
    # advanced_text_to_video_example()
    # image_to_video_example()
    # video_extension_example()
    # agent_integration_example()

    # These can be run without actual API calls:
    asyncio.run(fastapi_integration_example())

    print("\n🎯 Key Features:")
    print("- ✅ Text-to-video generation")
    print("- ✅ Image-to-video generation")
    print("- ✅ Video extension/continuation")
    print("- ✅ Multiple Veo model support (2.0, 3.0 preview)")
    print("- ✅ Async/await support for FastAPI")
    print("- ✅ Configurable video parameters")
    print("- ✅ Google Cloud Storage integration")
    print("- ✅ CAMEL agent integration")


if __name__ == "__main__":
    main()
