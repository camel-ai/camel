import pytest
import os

from camel.toolkits.ask_news_toolkit import AskNewsToolkit


@pytest.fixture(scope="module")
def client_id():
    key = os.environ.get('ASKNEWS_CLIENT_ID')
    if not key:
        pytest.fail("ASKNEWS_CLIENT_ID environment variable is not set.")
    return key


@pytest.fixture(scope="module")
def client_secret():
    key = os.environ.get('ASKNEWS_CLIENT_SECRET')
    if not key:
        pytest.fail("ASKNEWS_CLIENT_SECRET environment variable is not set.")
    return key


@pytest.fixture
def ask_news_toolkit():
    return AskNewsToolkit()


def test_chat_query(ask_news_toolkit):
    try:
        response = ask_news_toolkit.chat_query(
            "What's going on in the latest tech news?"
        )
        assert response is not None
        print("chat_query test passed.")
    except Exception as e:
        pytest.fail(f"chat_query raised an exception: {e}")


def test_get_news(ask_news_toolkit):
    try:
        news = ask_news_toolkit.get_news(
            "Give me the latest news about AI advancements."
        )
        assert news is not None
        print("get_news test passed.")
    except Exception as e:
        pytest.fail(f"get_news raised an exception: {e}")


def test_get_stories(ask_news_toolkit):
    try:
        stories = ask_news_toolkit.get_stories(
            categories=["Technology", "Science"],
            continent="North America",
            sort_by="coverage",
            sort_type="desc",
            reddit=3,
            expand_updates=True,
            max_updates=2,
            max_articles=10,
        )
        assert stories is not None
        print("get_stories test passed.")
    except Exception as e:
        pytest.fail(f"get_stories raised an exception: {e}")


def test_search_reddit(ask_news_toolkit):
    try:
        reddit_response = ask_news_toolkit.search_reddit(
            keywords=["sentiment", "bitcoin", "halving"], return_type="both"
        )
        assert reddit_response is not None
        print("search_reddit test passed.")
    except Exception as e:
        pytest.fail(f"search_reddit raised an exception: {e}")


def test_finance_query(ask_news_toolkit):
    try:
        sentiment_data_string = ask_news_toolkit.finance_query(
            asset="amazon",
            metric="news_positive",
            date_from="2024-03-20T10:00:00Z",
            date_to="2024-03-24T23:00:00Z",
            return_type="string",
        )
        assert sentiment_data_string is not None
        print("finance_query test passed.")
    except Exception as e:
        pytest.fail(f"finance_query raised an exception: {e}")


def test_get_web_search(ask_news_toolkit):
    try:
        search_results = ask_news_toolkit.get_web_search(
            queries=["Eagles vs Falcons"]
        )
        assert search_results is not None
        print("get_web_search test passed.")
    except Exception as e:
        pytest.fail(f"get_web_search raised an exception: {e}")
