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
"""Tests for structured context compression log events.

Verifies that ``_get_context_with_summarization`` emits structured
``extra`` metadata (``event_type``, ``compression_mode``, token counts)
so downstream tooling can observe compression boundaries without parsing
log message strings.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def _compression_log_records(caplog):
    """Collect WARNING-level log records from camel.agents.chat_agent."""
    with caplog.at_level(logging.WARNING, logger="camel.agents.chat_agent"):
        yield caplog


class TestStructuredCompressionEvents:
    """Structured compression event tests for ChatAgent."""

    def _make_agent(self, summarize_threshold=50, token_limit=1000):
        """Create a minimal ChatAgent with compression enabled."""
        from camel.agents import ChatAgent

        agent = ChatAgent(
            system_message="You are a helpful assistant.",
            summarize_threshold=summarize_threshold,
            token_limit=token_limit,
        )
        return agent

    @patch("camel.agents.chat_agent.ChatAgent.summarize")
    def test_progressive_compression_emits_structured_event(
        self, mock_summarize, _compression_log_records, caplog
    ):
        """Progressive compression should emit event_type and mode in extra."""
        mock_summarize.return_value = {"summary": "[CONTEXT_SUMMARY] test"}

        agent = self._make_agent(summarize_threshold=50, token_limit=1000)

        # Simulate memory returning tokens above threshold but below limit
        threshold = int(1000 * 50 / 100)  # 500
        mock_context = [{"role": "user", "content": "hello"}]
        agent.memory = MagicMock()
        agent.memory.get_context.return_value = (mock_context, threshold + 10)
        agent._summary_token_count = 0

        agent._get_context_with_summarization()

        compression_records = [
            r
            for r in caplog.records
            if getattr(r, "event_type", None) == "context_compression"
        ]
        assert len(compression_records) >= 1, (
            "Expected at least one structured compression log record"
        )
        rec = compression_records[0]
        assert rec.compression_mode == "progressive"
        assert rec.num_tokens == threshold + 10
        assert rec.threshold == threshold
        assert rec.token_limit == 1000

    @patch("camel.agents.chat_agent.ChatAgent.summarize")
    def test_full_compression_emits_structured_event(
        self, mock_summarize, _compression_log_records, caplog
    ):
        """Full compression should emit event_type and mode in extra."""
        mock_summarize.return_value = {"summary": "[CONTEXT_SUMMARY] test"}

        agent = self._make_agent(summarize_threshold=50, token_limit=1000)

        # Simulate summary tokens exceeding the window ratio
        mock_context = [{"role": "user", "content": "hello"}]
        agent.memory = MagicMock()
        agent.memory.get_context.return_value = (mock_context, 800)
        agent._summary_token_count = int(
            1000 * agent.summary_window_ratio + 1
        )

        agent._get_context_with_summarization()

        compression_records = [
            r
            for r in caplog.records
            if getattr(r, "event_type", None) == "context_compression"
        ]
        assert len(compression_records) >= 1, (
            "Expected at least one structured compression log record"
        )
        rec = compression_records[0]
        assert rec.compression_mode == "full"
        assert rec.summary_token_count > 0
        assert rec.token_limit == 1000
