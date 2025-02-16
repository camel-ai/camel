import pytest
from pydantic import ValidationError

from camel.messages.conversion.entity_recognition import EntityRecognitionItem, EntityItem


def test_entity_recognition_item_valid():
    r"""Test valid EntityRecognitionItem creation."""
    item = EntityRecognitionItem(
        text="Apple Inc. was founded by Steve Jobs and Steve Wozniak in Cupertino, California, in 1976.",
        entities=[
            EntityItem(entity="Apple Inc.", type="Organization"),
            EntityItem(entity="Steve Jobs", type="Person"),
            EntityItem(entity="Steve Wozniak", type="Person"),
            EntityItem(entity="Cupertino, California", type="Location"),
            EntityItem(entity="1976", type="Date"),
        ]
    )
    assert item.text == "Apple Inc. was founded by Steve Jobs and Steve Wozniak in Cupertino, California, in 1976."
    assert len(item.entities) == 5
    assert item.entities[0].entity == "Apple Inc."
    assert item.entities[0].type == "Organization"

def test_entity_recognition_item_invalid_text():
    r"""Test EntityRecognitionItem with invalid text."""
    with pytest.raises(ValidationError):
        EntityRecognitionItem(text="!!!@@@", entities=[])

def test_entity_recognition_item_invalid_entity():
    r"""Test EntityRecognitionItem with an invalid entity."""
    with pytest.raises(ValidationError):
        EntityRecognitionItem(
            text="A sample text.",
            entities=[EntityItem(entity="", type="Person")]
        )

def test_entity_recognition_item_from_string():
    r"""Test parsing an EntityRecognitionItem from a formatted string."""
    text = r"""Text: Apple Inc. was founded by Steve Jobs in Cupertino, California, in 1976.
Entities:
- Apple Inc.: Organization
- Steve Jobs: Person
- Cupertino, California: Location
- 1976: Date"""

    item = EntityRecognitionItem.from_string(text)

    assert item.text == "Apple Inc. was founded by Steve Jobs in Cupertino, California, in 1976."
    assert len(item.entities) == 4
    assert item.entities[1].entity == "Steve Jobs"
    assert item.entities[1].type == "Person"

def test_entity_recognition_item_to_string():
    r"""Test converting an EntityRecognitionItem to a formatted string."""
    item = EntityRecognitionItem(
        text="NASA was established in 1958 in the United States.",
        entities=[
            EntityItem(entity="NASA", type="Organization"),
            EntityItem(entity="1958", type="Date"),
            EntityItem(entity="United States", type="Location")
        ]
    )

    text = item.to_string()

    assert "Text:" in text
    assert "NASA was established in 1958 in the United States." in text
    assert "Entities:" in text
    assert "- NASA: Organization" in text
    assert "- 1958: Date" in text
    assert "- United States: Location" in text
