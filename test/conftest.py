import pytest
from _pytest.config import Config
from _pytest.nodes import Item


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--full-test-mode", action="store_true",
                     help="Enable full test mode")
    parser.addoption("--fast-test-mode", action="store_true",
                     help="Enable fast test mode")


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    # Skip full test only tests if not in full test mode
    if not config.getoption("--full-test-mode"):
        skip_full_test = pytest.mark.skip(
            reason="Test runs only in full test mode")
        for item in items:
            if "full_test_only" in item.keywords:
                item.add_marker(skip_full_test)

    # Skip slow tests if fast test mode is enabled
    if config.getoption("--fast-test-mode"):
        skip_slow = pytest.mark.skip(reason="Skipped for fast test mode")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
