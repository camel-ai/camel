import pytest
from pydantic import ValidationError
from camel.messages.conversion.classification import ClassificationItem


def test_classification_item_valid():
    r"""Test valid ClassificationItem creation."""
    item = ClassificationItem(
        text="This is an amazing product! Highly recommend.",
        label="Positive Sentiment"
    )
    assert item.text == "This is an amazing product! Highly recommend."
    assert item.label == "Positive Sentiment"


def test_classification_item_valid_symbols():
    r"""Test ClassificationItem with a label containing special characters."""
    item = ClassificationItem(
        text="This message contains spam links.",
        label="@@Spam##Alert!!"
    )
    assert item.text == "This message contains spam links."
    assert item.label == "@@Spam##Alert!!"


def test_classification_item_invalid_text():
    r"""Test ClassificationItem with invalid text."""
    with pytest.raises(ValidationError):
        ClassificationItem(text="!!!@@@", label="Neutral")


def test_classification_item_from_string():
    r"""Test parsing a ClassificationItem from a formatted string."""
    text = r"""Text: The app crashes every time I open it.
Label: Bug Report"""

    item = ClassificationItem.from_string(text)

    assert item.text == "The app crashes every time I open it."
    assert item.label == "Bug Report"


def test_classification_item_to_string():
    r"""Test converting a ClassificationItem to a formatted string."""
    item = ClassificationItem(
        text="This book is a must-read for anyone interested in history.",
        label="Book Review"
    )

    text = item.to_string()

    assert "Text:" in text
    assert "This book is a must-read for anyone interested in history." in text
    assert "Label:" in text
    assert "Book Review" in text
