"""Tests for camel.utils.commons.create_chunks."""

import pytest

from camel.utils.commons import create_chunks


class TestCreateChunks:
    def test_normal_chunking(self):
        text = "Hello world. This is a test.\nNew line."
        chunks = create_chunks(text, 10)
        assert len(chunks) > 0
        assert "".join(chunks) == text

    def test_empty_text(self):
        chunks = create_chunks("", 10)
        assert chunks == []

    def test_n_zero_raises(self):
        """n=0 previously caused an infinite loop; should raise ValueError."""
        with pytest.raises(ValueError, match="must be greater than 0"):
            create_chunks("hello world", 0)

    def test_n_negative_raises(self):
        """Negative n previously caused an infinite loop; should raise ValueError."""
        with pytest.raises(ValueError, match="must be greater than 0"):
            create_chunks("hello world", -1)

    def test_short_text(self):
        chunks = create_chunks("hi", 100)
        assert chunks == ["hi"]

    def test_chunk_sizes_reasonable(self):
        """Each chunk should not be much larger than n."""
        text = "A" * 200
        chunks = create_chunks(text, 20)
        for chunk in chunks:
            assert len(chunk) <= 24  # 1.2 * 20 = 24 max
