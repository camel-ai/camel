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
import pytest
import requests
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from camel.embeddings import VisionLanguageEmbedding

pytestmark = pytest.mark.skip(
    reason="Temporarily skipping tests due to Huggingface "
    "credentials not available"
)


@pytest.fixture
def VLM_instance() -> VisionLanguageEmbedding:
    return VisionLanguageEmbedding()


def test_CLIPEmbedding_initialization(VLM_instance):
    assert VLM_instance is not None
    assert isinstance(VLM_instance.model, CLIPModel)
    assert isinstance(VLM_instance.processor, CLIPProcessor)


def test_image_embed_list_with_valid_input(VLM_instance):
    url = "http://images.cocodataset.org/val2017/000000039769.jpg"
    image = Image.open(requests.get(url, stream=True).raw)
    test_images = [image, image]
    embeddings = VLM_instance.embed_list(test_images)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    for e in embeddings:
        assert len(e) == VLM_instance.get_output_dim()


def test_image_embed_list_with_empty_input(VLM_instance):
    with pytest.raises(ValueError):
        VLM_instance.embed_list([])


def test_text_embed_list_with_valid_input(VLM_instance):
    test_texts = ['Hello world', 'Testing sentence embeddings']
    embeddings = VLM_instance.embed_list(test_texts)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    for e in embeddings:
        assert len(e) == VLM_instance.get_output_dim()


def test_text_embed_list_with_empty_input(VLM_instance):
    with pytest.raises(ValueError):
        VLM_instance.embed_list([])


def test_mixed_embed_list_with_valid_input(VLM_instance):
    test_list = ['Hello world', 'Testing sentence embeddings']
    url = "http://images.cocodataset.org/val2017/000000039769.jpg"
    image = Image.open(requests.get(url, stream=True).raw)
    test_list.append(image)
    embeddings = VLM_instance.embed_list(test_list)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 3
    for e in embeddings:
        assert len(e) == VLM_instance.get_output_dim()


def test_get_output_dim(VLM_instance):
    output_dim = VLM_instance.get_output_dim()
    assert isinstance(output_dim, int)
    assert output_dim > 0
