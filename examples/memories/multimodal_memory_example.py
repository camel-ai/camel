# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""Example: Multimodal Agent Memory with text + image support.

This example demonstrates:
1. Setting up MultimodalEmbeddingAdapter with CLIP (text+image unified embedding)
2. Creating MultimodalAgentMemory combining ChatHistoryBlock + MultimodalVectorDBBlock
3. Writing multimodal messages (text + images) to memory
4. Retrieving memories using text queries (cross-modal)
5. Retrieving memories using image queries (cross-modal)

Requirements:
    pip install transformers torch pillow

Usage:
    # Set your OpenAI API key
    export OPENAI_API_KEY="sk-..."

    # Run the example
    python examples/memories/multimodal_memory_example.py
"""

from pathlib import Path

from PIL import Image

from camel.agents import ChatAgent
from camel.embeddings import MultimodalEmbeddingAdapter
from camel.memories import (
    ChatHistoryBlock,
    MediaAssetStore,
    MultimodalAgentMemory,
    MultimodalContextCreator,
    MultimodalVectorDBBlock,
)
from camel.models.model_factory import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


def create_sample_image(text: str, path: Path) -> None:
    """Create a simple sample image for testing."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (400, 100), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except Exception:
        font = None
    draw.text((10, 35), text, fill=(255, 255, 255), font=font)
    img.save(path)


def main():
    data_dir = Path("/tmp/camel_multimodal_example")
    data_dir.mkdir(exist_ok=True)

    # =================================================================== #
    # 1. Setup multimodal embedding (CLIP — no API key needed)
    # =================================================================== #
    # VisionLanguageEmbedding uses OpenAI's CLIP model loaded from HuggingFace.
    # It produces 512-dim vectors for both text and images in the same space.
    mm_embedding = MultimodalEmbeddingAdapter()

    print(f"Embedding dimension: {mm_embedding.get_output_dim()}")

    # =================================================================== #
    # 2. Setup context creator
    # =================================================================== #
    media_store = MediaAssetStore(
        local_cache_dir=str(data_dir / "media_cache")
    )
    context_creator = MultimodalContextCreator(
        token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
        token_limit=8192,
        media_store=media_store,
        max_images_per_context=4,
    )

    # =================================================================== #
    # 3. Setup multimodal vector DB block
    # =================================================================== #
    mm_vector_block = MultimodalVectorDBBlock(
        embedding=mm_embedding,
        media_store=media_store,
        # storage defaults to in-memory Qdrant
    )

    # =================================================================== #
    # 4. Setup multimodal agent memory
    # =================================================================== #
    mm_memory = MultimodalAgentMemory(
        context_creator=context_creator,
        chat_history_block=ChatHistoryBlock(),
        multimodal_vector_block=mm_vector_block,
        retrieve_limit=3,
    )

    # =================================================================== #
    # 5. Setup model and agent
    # =================================================================== #
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    agent = ChatAgent(
        system_message="You are a helpful visual assistant.",
        model=model,
        memory=mm_memory,
        agent_id="multimodal_agent_001",
    )

    # =================================================================== #
    # 6. Create sample images for testing
    # =================================================================== #
    # In a real scenario, you would use actual images:
    #   img = Image.open("your_photo.jpg")
    #
    # For this example, we create synthetic test images.
    create_sample_image("A cute cat sitting on a red mat", data_dir / "cat.jpg")
    create_sample_image("A sunset over the ocean with palm trees", data_dir / "sunset.jpg")
    create_sample_image("A busy city street with cars and people", data_dir / "city.jpg")

    img_cat = Image.open(data_dir / "cat.jpg")
    img_sunset = Image.open(data_dir / "sunset.jpg")
    img_city = Image.open(data_dir / "city.jpg")

    # =================================================================== #
    # 7. Write multimodal messages to memory
    # =================================================================== #
    from camel.messages import BaseMessage

    # Simulate a conversation where the user shares images
    msg_cat = BaseMessage.make_user_message(
        role_name="User",
        content="Look at this cute cat!",
        image_list=[img_cat],
    )

    msg_sunset = BaseMessage.make_user_message(
        role_name="User",
        content="Here is a beautiful sunset photo.",
        image_list=[img_sunset],
    )

    msg_city = BaseMessage.make_user_message(
        role_name="User",
        content="And this is a busy city street.",
        image_list=[img_city],
    )

    # Write records to memory
    from camel.memories.records import MemoryRecord
    from camel.types import OpenAIBackendRole

    records = [
        MemoryRecord(message=msg_cat, role_at_backend=OpenAIBackendRole.USER),
        MemoryRecord(message=msg_sunset, role_at_backend=OpenAIBackendRole.USER),
        MemoryRecord(message=msg_city, role_at_backend=OpenAIBackendRole.USER),
    ]
    agent.memory.write_records(records)

    print(f"Wrote {len(records)} multimodal records to memory")

    # =================================================================== #
    # 8. Cross-modal retrieval: text query -> image results
    # =================================================================== #
    # Use text to find relevant image memories
    retrieved = mm_vector_block.retrieve("something cute and furry", limit=2)
    print(f"\nText query 'something cute and furry' retrieved {len(retrieved)} records:")
    for r in retrieved:
        print(f"  - Score: {r.score:.4f}, Content: {r.memory_record.message.content}")

    # =================================================================== #
    # 9. Cross-modal retrieval: image query -> text/image results
    # =================================================================== #
    # Use an image to find semantically similar memories
    retrieved_by_img = mm_vector_block.retrieve(img_sunset, limit=2)
    print(f"\nImage query (sunset) retrieved {len(retrieved_by_img)} records:")
    for r in retrieved_by_img:
        print(f"  - Score: {r.score:.4f}, Content: {r.memory_record.message.content}")

    # =================================================================== #
    # 10. Full agent interaction with multimodal memory
    # =================================================================== #
    # The agent's step() method automatically uses memory.get_context()
    # which combines ChatHistoryBlock (recency) + MultimodalVectorDBBlock (semantic)

    # Ask about the cat photo (should retrieve the cat memory)
    print("\n--- Agent interaction: asking about the cat ---")
    try:
        response = agent.step(
            "Can you describe the cat photo I showed you earlier?"
        )
        print(f"Agent response: {response.msgs[0].content[:200]}...")
    except Exception as e:
        print(f"Agent step failed (API key may not be set): {e}")

    # =================================================================== #
    # 11. Cleanup
    # =================================================================== #
    # Clean up test images
    for f in data_dir.iterdir():
        f.unlink()
    data_dir.rmdir()

    print("\nDone!")


if __name__ == "__main__":
    main()
