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

"""Tests for MediaAssetStore."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from camel.memories.media_asset_store import MediaAssetStore
from camel.memories.records import MemoryRecord
from camel.messages import BaseMessage
from camel.storages.key_value_storages import InMemoryKeyValueStorage
from camel.types import OpenAIBackendRole, RoleType


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_record(
    content="test",
    image_list=None,
    video_bytes=None,
    audio_bytes=None,
    audio_format=None,
):
    """Create a MemoryRecord with optional media."""
    return MemoryRecord(
        message=BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=None,
            content=content,
            image_list=image_list,
            video_bytes=video_bytes,
            audio_bytes=audio_bytes,
            audio_format=audio_format,
        ),
        role_at_backend=OpenAIBackendRole.USER,
        agent_id="test_agent",
    )


def make_fake_image():
    """Create a minimal PIL Image for testing."""
    from PIL import Image

    img = Image.new("RGB", (10, 10), color="red")
    return img


def make_metadata_record(agent_id, remote_refs):
    return {
        "kind": MediaAssetStore._METADATA_RECORD_KIND,
        "agent_id": agent_id,
        "remote_refs": remote_refs,
    }


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory, auto-cleaned."""
    d = tmp_path / "media_cache"
    d.mkdir()
    yield d
    # tmp_path auto-cleans


@pytest.fixture
def store(cache_dir):
    return MediaAssetStore(local_cache_dir=str(cache_dir))


@pytest.fixture
def mock_object_storage():
    from camel.storages.object_storages.base import BaseObjectStorage

    return MagicMock(spec=BaseObjectStorage)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestMediaAssetStoreInit:
    """Tests for __init__."""

    def test_init_creates_cache_dir(self, tmp_path):
        d = tmp_path / "new_dir"
        MediaAssetStore(local_cache_dir=str(d))
        assert d.exists()

    def test_init_with_existing_dir(self, cache_dir):
        store = MediaAssetStore(local_cache_dir=str(cache_dir))
        assert store._local_cache_dir == cache_dir

    def test_close_shuts_down_executor(self, cache_dir):
        store = MediaAssetStore(local_cache_dir=str(cache_dir), io_workers=2)
        executor = MagicMock()
        store._executor = executor

        store.close()

        executor.shutdown.assert_called_once_with(
            wait=True, cancel_futures=False
        )
        assert store._executor is None

    def test_close_is_idempotent(self, cache_dir):
        store = MediaAssetStore(local_cache_dir=str(cache_dir), io_workers=2)
        executor = MagicMock()
        store._executor = executor

        store.close()
        store.close()

        executor.shutdown.assert_called_once()


class TestMediaAssetStoreStoreMedia:
    """Tests for store_media."""

    def test_store_image_writes_to_disk(self, store, cache_dir):
        img = make_fake_image()
        record = make_record(content="look", image_list=[img])

        refs = store.store_media(record, agent_id="agent1")

        assert len(refs) == 1
        assert "image_ref_0" in refs
        assert refs["image_ref_0"].startswith("file://")

        # Verify file exists on disk
        uri = refs["image_ref_0"]
        path = Path(uri[len("file://"):])
        assert path.exists()

    def test_store_multiple_images(self, store):
        imgs = [make_fake_image() for _ in range(3)]
        record = make_record(image_list=imgs)

        refs = store.store_media(record)

        assert len(refs) == 3
        for i in range(3):
            assert f"image_ref_{i}" in refs

    def test_store_video(self, store):
        video = b"\x00\x00\x00\x18ftypmp42"
        record = make_record(content="", video_bytes=video)

        refs = store.store_media(record)

        assert "video_ref" in refs
        uri = refs["video_ref"]
        path = Path(uri[len("file://"):])
        assert path.exists()
        assert path.read_bytes() == video

    def test_store_audio(self, store):
        audio = b"RIFF....WAVEfmt "
        record = make_record(content="", audio_bytes=audio, audio_format="wav")

        refs = store.store_media(record)

        assert "audio_ref" in refs
        uri = refs["audio_ref"]
        path = Path(uri[len("file://"):])
        assert path.exists()
        assert path.read_bytes() == audio

    def test_store_empty_record_returns_empty(self, store):
        record = make_record(content="", image_list=None, video_bytes=None)
        refs = store.store_media(record)
        assert refs == {}

    def test_store_text_only_returns_empty(self, store):
        record = make_record(content="hello world")
        refs = store.store_media(record)
        assert refs == {}

    def test_store_agent_namespacing(self, store, cache_dir):
        img = make_fake_image()
        record = make_record(image_list=[img])

        store.store_media(record, agent_id="agent_a")
        store.store_media(record, agent_id="agent_b")

        assert (cache_dir / "agent_a").exists()
        assert (cache_dir / "agent_b").exists()

    def test_store_default_agent(self, store, cache_dir):
        img = make_fake_image()
        record = make_record(image_list=[img])

        store.store_media(record)

        assert (cache_dir / "default").exists()

    def test_store_media_uploads_to_object_storage(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            remote_prefix="camel-media",
        )

        refs = store.store_media(record, agent_id="agent1")

        assert refs["image_ref_0"].startswith("remote://camel-media/agent1/")
        mock_object_storage.upload_file.assert_called_once()
        upload_args = mock_object_storage.upload_file.call_args[0]
        assert upload_args[0].exists()
        assert upload_args[1].as_posix().startswith("camel-media/agent1/")

    def test_store_media_records_remote_manifest(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
        )

        refs = store.store_media(record, agent_id="agent1")

        manifest_path = cache_dir / "agent1" / ".remote_manifest.json"
        assert manifest_path.exists()
        assert refs["image_ref_0"] in manifest_path.read_text()

    def test_store_media_records_remote_refs_in_metadata_storage(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        metadata_storage = InMemoryKeyValueStorage()
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            metadata_storage=metadata_storage,
        )

        refs = store.store_media(record, agent_id="agent1")

        records = metadata_storage.load()
        assert records == [
            make_metadata_record("agent1", [refs["image_ref_0"]])
        ]
        manifest_path = cache_dir / "agent1" / ".remote_manifest.json"
        assert not manifest_path.exists()


class TestMediaAssetStoreRestoreMedia:
    """Tests for restore_media."""

    def test_restore_image(self, store):
        img = make_fake_image()
        record = make_record(content="look", image_list=[img])

        refs = store.store_media(record, agent_id="agent1")

        # Create a new record with refs in extra_info
        from camel.memories.multimodal_metadata import MultimodalMetadata

        mmeta = MultimodalMetadata(
            modalities=["text", "image"],
            image_count=1,
            media_refs=list(refs.values()),
        )
        restore_record = make_record(content="look")
        restore_record.extra_info.update(mmeta.to_extra_info())

        result = store.restore_media(restore_record)

        assert result.message.image_list is not None
        assert len(result.message.image_list) == 1

    def test_restore_video(self, store):
        video = b"\x00\x00\x00\x18ftypmp42"
        record = make_record(content="", video_bytes=video)

        refs = store.store_media(record)

        from camel.memories.multimodal_metadata import MultimodalMetadata

        mmeta = MultimodalMetadata(
            modalities=["text"],
            has_video=True,
            media_refs=list(refs.values()),
        )
        restore_record = make_record(content="")
        restore_record.extra_info.update(mmeta.to_extra_info())

        result = store.restore_media(restore_record)

        assert result.message.video_bytes == video

    def test_restore_audio(self, store):
        audio = b"ID3audio"
        record = make_record(content="", audio_bytes=audio, audio_format="mp3")

        refs = store.store_media(record)

        from camel.memories.multimodal_metadata import MultimodalMetadata

        mmeta = MultimodalMetadata(
            modalities=["text", "audio"],
            has_audio=True,
            media_refs=list(refs.values()),
        )
        restore_record = make_record(content="")
        restore_record.extra_info.update(mmeta.to_extra_info())

        result = store.restore_media(restore_record)

        assert result.message.audio_bytes == audio
        assert result.message.audio_format == "mp3"

    def test_restore_no_refs_passthrough(self, store):
        record = make_record(content="hello")
        result = store.restore_media(record)
        assert result is record

    def test_restore_missing_file_raises(self, store):
        from camel.memories.multimodal_metadata import MultimodalMetadata

        mmeta = MultimodalMetadata(
            modalities=["text", "image"],
            image_count=1,
            media_refs=["file:///nonexistent/path.png"],
        )
        record = make_record(content="look")
        record.extra_info.update(mmeta.to_extra_info())

        with pytest.raises(FileNotFoundError, match="Media file not found"):
            store.restore_media(record)

    def test_restore_remote_downloads_and_caches(
        self, cache_dir, mock_object_storage
    ):
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            remote_prefix="camel-media",
        )

        audio_bytes = b"remote-audio"

        def download_file(local_file_path, remote_file_path):
            local_file_path.write_bytes(audio_bytes)

        mock_object_storage.download_file.side_effect = download_file

        from camel.memories.multimodal_metadata import MultimodalMetadata

        mmeta = MultimodalMetadata(
            modalities=["text", "audio"],
            has_audio=True,
            media_refs=["remote://camel-media/agent1/test_audio.mp3"],
        )
        record = make_record(content="")
        record.extra_info.update(mmeta.to_extra_info())

        restored = store.restore_media(record)
        assert restored.message.audio_bytes == audio_bytes
        assert restored.message.audio_format == "mp3"
        mock_object_storage.download_file.assert_called_once()

        second = make_record(content="")
        second.extra_info.update(mmeta.to_extra_info())
        restored_again = store.restore_media(second)
        assert restored_again.message.audio_bytes == audio_bytes
        assert mock_object_storage.download_file.call_count == 1

    def test_metadata_storage_preserves_unrelated_records(
        self, cache_dir, mock_object_storage
    ):
        metadata_storage = InMemoryKeyValueStorage()
        metadata_storage.save(
            [{"kind": "unrelated", "value": "keep-me"}]
        )
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            metadata_storage=metadata_storage,
        )
        img = make_fake_image()
        record = make_record(image_list=[img])
        refs = store.store_media(record, agent_id="agent1")

        assert metadata_storage.load() == [
            {"kind": "unrelated", "value": "keep-me"},
            make_metadata_record("agent1", [refs["image_ref_0"]]),
        ]


class TestMediaAssetStoreClear:
    """Tests for clear."""

    def test_clear_agent(self, store, cache_dir):
        img = make_fake_image()
        record = make_record(image_list=[img])

        store.store_media(record, agent_id="agent1")
        store.store_media(record, agent_id="agent2")

        store.clear(agent_id="agent1")

        assert not (cache_dir / "agent1").exists()
        assert (cache_dir / "agent2").exists()

    def test_clear_all(self, store, cache_dir):
        img = make_fake_image()
        record = make_record(image_list=[img])

        store.store_media(record, agent_id="agent1")
        store.store_media(record, agent_id="agent2")

        store.clear()

        assert cache_dir.exists()  # dir recreated
        assert not (cache_dir / "agent1").exists()
        assert not (cache_dir / "agent2").exists()

    def test_clear_agent_deletes_remote_refs(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
        )

        refs = store.store_media(record, agent_id="agent1")
        store.clear(agent_id="agent1")

        mock_object_storage.delete_file.assert_called_once()
        delete_arg = mock_object_storage.delete_file.call_args[0][0]
        assert delete_arg.as_posix() == refs["image_ref_0"][len("remote://") :]

    def test_clear_all_deletes_remote_refs_for_all_agents(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
        )

        store.store_media(record, agent_id="agent1")
        store.store_media(record, agent_id="agent2")
        store.clear()

        assert mock_object_storage.delete_file.call_count == 2

    def test_clear_agent_updates_metadata_storage(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        metadata_storage = InMemoryKeyValueStorage()
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            metadata_storage=metadata_storage,
        )

        refs_agent1 = store.store_media(record, agent_id="agent1")
        refs_agent2 = store.store_media(record, agent_id="agent2")

        store.clear(agent_id="agent1")

        assert metadata_storage.load() == [
            make_metadata_record("agent2", [refs_agent2["image_ref_0"]])
        ]
        deleted_refs = [
            call.args[0].as_posix()
            for call in mock_object_storage.delete_file.call_args_list
        ]
        assert refs_agent1["image_ref_0"][len("remote://") :] in deleted_refs
        assert refs_agent2["image_ref_0"][len("remote://") :] not in deleted_refs

    def test_clear_all_clears_metadata_storage(
        self, cache_dir, mock_object_storage
    ):
        img = make_fake_image()
        record = make_record(image_list=[img])
        metadata_storage = InMemoryKeyValueStorage()
        store = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir),
            metadata_storage=metadata_storage,
        )

        store.store_media(record, agent_id="agent1")
        store.clear()

        assert metadata_storage.load() == []

    def test_clear_remote_uses_shared_metadata_storage_across_instances(
        self, cache_dir, mock_object_storage
    ):
        metadata_storage = InMemoryKeyValueStorage()
        writer = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir / "writer"),
            metadata_storage=metadata_storage,
        )
        cleaner = MediaAssetStore(
            object_storage=mock_object_storage,
            local_cache_dir=str(cache_dir / "cleaner"),
            metadata_storage=metadata_storage,
        )

        img = make_fake_image()
        record = make_record(image_list=[img])
        refs = writer.store_media(record, agent_id="agent1")

        cleaner.clear(agent_id="agent1")

        mock_object_storage.delete_file.assert_called_once()
        assert (
            mock_object_storage.delete_file.call_args[0][0].as_posix()
            == refs["image_ref_0"][len("remote://") :]
        )
        assert metadata_storage.load() == []


class TestMediaAssetStoreRepr:
    """Tests for __repr__."""

    def test_repr(self, store):
        r = repr(store)
        assert "MediaAssetStore" in r
        assert "media_cache" in r
