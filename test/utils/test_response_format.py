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
import unittest

from pydantic import BaseModel, ValidationError

from camel.utils.response_format import model_from_json_schema


class TestModelFromJsonSchema(unittest.TestCase):
    def test_simple_types(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["name", "age"],
        }
        Model = model_from_json_schema("SimpleUser", schema)

        # Test successful instantiation with required fields.
        instance = Model(name="Alice", age=30)
        self.assertEqual(instance.name, "Alice")
        self.assertEqual(instance.age, 30)
        # Optional fields should default to None.
        self.assertIsNone(getattr(instance, "score", None))
        self.assertIsNone(getattr(instance, "active", None))

        # Missing required field "name" should raise a validation error.
        with self.assertRaises(ValidationError):
            Model(age=30)

    def test_defaults_and_constraints(self):
        schema = {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 10,
                    "default": "user123",
                },
                "rating": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 5,
                    "default": 3.0,
                },
            },
            "required": [],
        }
        Model = model_from_json_schema("UserWithDefaults", schema)
        instance = Model()
        self.assertEqual(instance.username, "user123")
        self.assertEqual(instance.rating, 3.0)

        # Constraint violation for username (too short)
        with self.assertRaises(ValidationError):
            Model(username="ab")

        # Constraint violation for rating (exceeds maximum)
        with self.assertRaises(ValidationError):
            Model(rating=6)

    def test_enum_values_are_enforced(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive"],
                },
                "priority": {
                    "type": "integer",
                    "enum": [1, 2, 3],
                    "default": 2,
                },
            },
            "required": ["status"],
        }
        Model = model_from_json_schema("TaskModel", schema)

        # Values listed in ``enum`` are accepted.
        instance = Model(status="active")
        self.assertEqual(instance.status, "active")
        # The optional field keeps its default, which is itself valid.
        self.assertEqual(instance.priority, 2)

        # A value outside ``enum`` must be rejected for a required field.
        with self.assertRaises(ValidationError):
            Model(status="archived")

        # ... and for an optional field as well.
        with self.assertRaises(ValidationError):
            Model(status="active", priority=99)

        # The generated JSON schema still advertises the allowed values.
        properties = Model.model_json_schema()["properties"]
        self.assertEqual(properties["status"]["enum"], ["active", "inactive"])

    def test_enum_on_nullable_field(self):
        schema = {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["free", "pro"],
                    "nullable": True,
                }
            },
            "required": ["tier"],
        }
        Model = model_from_json_schema("TierModel", schema)
        self.assertIsNone(Model(tier=None).tier)
        self.assertEqual(Model(tier="pro").tier, "pro")
        with self.assertRaises(ValidationError):
            Model(tier="enterprise")

    def test_nested_objects(self):
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "zipcode": {"type": "integer"},
                    },
                    "required": ["street"],
                }
            },
            "required": ["address"],
        }
        Model = model_from_json_schema("UserWithAddress", schema)
        # Correct usage with nested object.
        instance = Model(address={"street": "Main St", "zipcode": 12345})
        self.assertEqual(instance.address.street, "Main St")
        self.assertEqual(instance.address.zipcode, 12345)

        # Missing required nested field "street" should raise an error.
        with self.assertRaises(ValidationError):
            Model(address={"zipcode": 12345})

    def test_array_items(self):
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["tags"],
        }
        Model = model_from_json_schema("UserWithTags", schema)
        instance = Model(tags=["python", "pydantic"])
        self.assertIsInstance(instance.tags, list)
        self.assertEqual(instance.tags, ["python", "pydantic"])

        # Passing a non-list should raise a validation error.
        with self.assertRaises(ValidationError):
            Model(tags="not a list")

    def test_nullable_fields(self):
        schema = {
            "type": "object",
            "properties": {"nickname": {"type": "string", "nullable": True}},
            "required": [],
        }
        Model = model_from_json_schema("UserNullable", schema)
        # Test explicit None value.
        instance = Model(nickname=None)
        self.assertIsNone(instance.nickname)

        # Test valid string value.
        instance = Model(nickname="Sam")
        self.assertEqual(instance.nickname, "Sam")

    def test_array_of_objects(self):
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                        "required": ["name", "age"],
                    },
                },
            },
            "required": ["items"],
        }
        Model = model_from_json_schema("UserWithArrayOfObjects", schema)
        instance = Model(
            items=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        )
        self.assertIsInstance(instance.items, list)
        self.assertEqual(len(instance.items), 2)
        self.assertIsInstance(instance.items[0], BaseModel)
        self.assertIsInstance(instance.items[1], BaseModel)
        self.assertEqual(instance.items[0].name, "Alice")
        self.assertEqual(instance.items[1].name, "Bob")
        self.assertEqual(instance.items[0].age, 30)
        self.assertEqual(instance.items[1].age, 25)

        # Passing a non-list should raise a validation error.
        with self.assertRaises(ValidationError):
            Model(items="not a list")


if __name__ == "__main__":
    unittest.main()
