"""Tests for camel.utils.commons.BatchProcessor._calculate_optimal_workers."""

from unittest.mock import patch, MagicMock
from camel.utils.commons import BatchProcessor


class TestCalculateOptimalWorkers:
    def test_cpu_count_none(self):
        """psutil.cpu_count() can return None on some systems; should default to 1, not crash."""
        with patch("psutil.cpu_count", return_value=None), \
             patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = MagicMock(percent=50.0)
            # This should not raise TypeError
            bp = BatchProcessor(max_workers=None)
            assert bp.max_workers >= 1

    def test_cpu_count_returns_value(self):
        """Normal case: cpu_count returns a positive integer."""
        with patch("psutil.cpu_count", return_value=8), \
             patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = MagicMock(percent=50.0)
            bp = BatchProcessor(max_workers=None)
            assert bp.max_workers >= 1
