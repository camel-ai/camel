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

"""Tests for MultimodalContextCreator."""

from unittest.mock import MagicMock, patch

import pytest

from camel.memories.context_creators.multimodal import MultimodalContextCreator
from camel.memories.records import ContextRecord, MemoryRecord
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, RoleType
from camel.utils import BaseTokenCounter


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_memory_record(
    content="hello", image_list=None, role_backend=OpenAIBackendRole.USER
):
    return MemoryRecord(
        message=BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=None,
            content=content,
            image_list=image_list,
        ),
        role_at_backend=role_backend,
        agent_id="test_agent",
    )


def make_context_record(content="hello", score=1.0, image_list=None, role_backend=OpenAIBackendRole.USER):
    return ContextRecord(
        memory_record=make_memory_record(content, image_list, role_backend),
        score=score,
        timestamp=1000.0,
    )


def make_fake_image():
    from PIL import Image
    return Image.new("RGB", (10, 10), color="blue")


@pytest.fixture
def mock_token_counter():
    counter = MagicMock(spec=BaseTokenCounter)
    counter.count_tokens_from_messages.return_value = 100
    return counter


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestMultimodalContextCreatorInit:
    """Tests for __init__."""

    def test_init_defaults(self, mock_token_counter):
        creator = MultimodalContextCreator(mock_token_counter, token_limit=4096)
        assert creator.token_limit == 4096
        assert creator._max_images == 10
        assert creator._detail_fallback == "low"
        assert creator._media_store is None

    def test_init_custom(self, mock_token_counter):
        mock_store = MagicMock()
        creator = MultimodalContextCreator(
            mock_token_counter,
            token_limit=8192,
            media_store=mock_store,
            max_images_per_context=5,
            image_detail_fallback="high",
        )
        assert creator.token_limit == 8192
        assert creator._max_images == 5
        assert creator._detail_fallback == "high"
        assert creator._media_store is mock_store


class TestMultimodalContextCreatorCreateContext:
    """Tests for create_context."""

    def test_create_context_delegates_to_parent(self, mock_token_counter):
        """create_context calls parent and returns messages + token count."""
        records = [
            make_context_record("hello", score=1.0),
            make_context_record("world", score=0.9),
        ]
        creator = MultimodalContextCreator(mock_token_counter, token_limit=4096)

        messages, token_count = creator.create_context(records)

        assert len(messages) == 2
        assert token_count == 100  # mock return value

    def test_create_context_with_media_store_restores(
        self, mock_token_counter
    ):
        """Media store is called to restore media on each record."""
        mock_store = MagicMock()
        mock_store.restore_media.side_effect = lambda r: r  # passthrough

        records = [make_context_record("hello", score=1.0)]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=4096, media_store=mock_store
        )

        creator.create_context(records)

        mock_store.restore_media.assert_called_once()

    def test_create_context_system_message_first(self, mock_token_counter):
        """System message appears first regardless of score."""
        records = [
            make_context_record("user msg", score=0.9, role_backend=OpenAIBackendRole.USER),
            make_context_record("system msg", score=0.5, role_backend=OpenAIBackendRole.SYSTEM),
        ]
        creator = MultimodalContextCreator(mock_token_counter, token_limit=4096)

        messages, _ = creator.create_context(records)

        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_create_context_does_not_mutate_input_records(
        self, mock_token_counter
    ):
        """Image trimming and detail downgrade do not mutate caller records."""
        image = make_fake_image()
        records = [
            make_context_record("keep", score=0.9, image_list=[image]),
            make_context_record("trim", score=0.1, image_list=[image]),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter,
            token_limit=100,
            max_images_per_context=1,
            image_detail_fallback="low",
        )
        creator._estimate_message_tokens = MagicMock(return_value=90)

        creator.create_context(records)

        assert len(records[0].memory_record.message.image_list) == 1
        assert len(records[1].memory_record.message.image_list) == 1
        assert records[0].memory_record.message.image_detail == "auto"
        assert records[1].memory_record.message.image_detail == "auto"


class TestMultimodalContextCreatorTrimImages:
    """Tests for _trim_images."""

    def test_trim_images_within_budget(self, mock_token_counter):
        """No trimming when image count <= max_images."""
        records = [
            make_context_record("a", image_list=[make_fake_image()]),
            make_context_record("b", image_list=[make_fake_image()]),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=4096, max_images_per_context=5
        )

        result = creator._trim_images(records)

        assert len(result) == 2
        for r in result:
            assert len(r.memory_record.message.image_list) == 1

    def test_trim_images_over_budget(self, mock_token_counter):
        """Images removed from lowest-scored records when over budget."""
        records = [
            make_context_record("high", score=0.95, image_list=[make_fake_image()]),
            make_context_record("low", score=0.3, image_list=[make_fake_image()]),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=4096, max_images_per_context=1
        )

        result = creator._trim_images(records)

        assert len(result) == 2
        # High-score record keeps image
        assert len(result[0].memory_record.message.image_list) == 1
        # Low-score record loses image
        assert len(result[1].memory_record.message.image_list) == 0

    def test_trim_images_no_images(self, mock_token_counter):
        """Records without images pass through unchanged."""
        records = [
            make_context_record("a"),
            make_context_record("b"),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=4096, max_images_per_context=0
        )

        result = creator._trim_images(records)
        assert len(result) == 2


class TestMultimodalContextCreatorAdjustDetail:
    """Tests for _adjust_image_detail."""

    def test_no_adjustment_under_budget(self, mock_token_counter):
        """No detail change when tokens < 80% of limit."""
        mock_token_counter.count_tokens_from_messages.return_value = 100
        records = [
            make_context_record("a", image_list=[make_fake_image()]),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=10000, image_detail_fallback="low"
        )

        result = creator._adjust_image_detail(records)

        # Detail should not be changed
        assert result[0].memory_record.message.image_detail == "auto"

    def test_adjustment_over_budget(self, mock_token_counter):
        """Detail downgraded when tokens > 80% of limit."""
        records = [
            make_context_record("a", image_list=[make_fake_image()]),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=100, image_detail_fallback="low"
        )
        # Mock _estimate_message_tokens to return high value
        creator._estimate_message_tokens = MagicMock(return_value=90)

        result = creator._adjust_image_detail(records)

        assert result[0].memory_record.message.image_detail == "low"

    def test_adjustment_skips_text_only_records(self, mock_token_counter):
        """Text-only records are not modified during detail adjustment."""
        records = [
            make_context_record("text only", image_list=None),
        ]
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=100, image_detail_fallback="low"
        )
        creator._estimate_message_tokens = MagicMock(return_value=90)

        result = creator._adjust_image_detail(records)

        # image_list should remain None
        assert result[0].memory_record.message.image_list is None


class TestMultimodalContextCreatorRepr:
    """Tests for __repr__."""

    def test_repr(self, mock_token_counter):
        creator = MultimodalContextCreator(
            mock_token_counter, token_limit=4096, max_images_per_context=5
        )
        r = repr(creator)
        assert "MultimodalContextCreator" in r
        assert "4096" in r
        assert "max_images=5" in r
