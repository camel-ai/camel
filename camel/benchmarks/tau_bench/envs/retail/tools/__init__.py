# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Copyright Sierra

import json
from typing import Any, Dict, List

from tau_bench.envs.tool import Tool


class Calculate(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], expression: str) -> str:
        if not all(char in "0123456789+-*/(). " for char in expression):
            return "Error: invalid characters in expression"
        try:
            # Evaluate the mathematical expression safely
            return str(
                round(float(eval(expression, {"__builtins__": None}, {})), 2)
            )
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Calculate the result of a mathematical expression.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces.",
                        },
                    },
                    "required": ["expression"],
                },
            },
        }


class CancelPendingOrder(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], order_id: str, reason: str) -> str:
        # check order exists and is pending
        orders = data["orders"]
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "pending":
            return "Error: non-pending order cannot be cancelled"

        # check reason
        if reason not in ["no longer needed", "ordered by mistake"]:
            return "Error: invalid reason"

        # handle refund
        refunds = []
        for payment in order["payment_history"]:
            payment_id = payment["payment_method_id"]
            refund = {
                "transaction_type": "refund",
                "amount": payment["amount"],
                "payment_method_id": payment_id,
            }
            refunds.append(refund)
            if "gift_card" in payment_id:  # refund to gift card immediately
                payment_method = data["users"][order["user_id"]][
                    "payment_methods"
                ][payment_id]
                payment_method["balance"] += payment["amount"]
                payment_method["balance"] = round(payment_method["balance"], 2)

        # update order status
        order["status"] = "cancelled"
        order["cancel_reason"] = reason
        order["payment_history"].extend(refunds)

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "cancel_pending_order",
                "description": (
                    "Cancel a pending order. If the order is already processed or delivered, "
                    "it cannot be cancelled. The agent needs to explain the cancellation detail "
                    "and ask for explicit user confirmation (yes/no) to proceed. If the user confirms, "
                    "the order status will be changed to 'cancelled' and the payment will be refunded. "
                    "The refund will be added to the user's gift card balance immediately if the payment "
                    "was made using a gift card, otherwise the refund would take 5-7 business days to process. "
                    "The function returns the order details after the cancellation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "reason": {
                            "type": "string",
                            "enum": ["no longer needed", "ordered by mistake"],
                            "description": "The reason for cancellation, which should be either 'no longer needed' or 'ordered by mistake'.",
                        },
                    },
                    "required": ["order_id", "reason"],
                },
            },
        }


class ExchangeDeliveredOrderItems(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> str:
        products, orders, users = (
            data["products"],
            data["orders"],
            data["users"],
        )

        # check order exists and is delivered
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "delivered":
            return "Error: non-delivered order cannot be exchanged"

        # check the items to be exchanged exist
        all_item_ids = [item["item_id"] for item in order["items"]]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                return f"Error: {item_id} not found"

        # check new items exist and match old items and are available
        if len(item_ids) != len(new_item_ids):
            return "Error: the number of items to be exchanged should match"

        diff_price = 0
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next(
                order_item
                for order_item in order["items"]
                if order_item["item_id"] == item_id
            )
            product_id = item["product_id"]
            if not (
                new_item_id in products[product_id]["variants"]
                and products[product_id]["variants"][new_item_id]["available"]
            ):
                return f"Error: new item {new_item_id} not found or available"

            old_price = item["price"]
            new_price = products[product_id]["variants"][new_item_id]["price"]
            diff_price += new_price - old_price

        diff_price = round(diff_price, 2)

        # check payment method exists and can cover the price difference if gift card
        if payment_method_id not in users[order["user_id"]]["payment_methods"]:
            return "Error: payment method not found"

        payment_method = users[order["user_id"]]["payment_methods"][
            payment_method_id
        ]
        if (
            payment_method["source"] == "gift_card"
            and payment_method["balance"] < diff_price
        ):
            return "Error: insufficient gift card balance to pay for the price difference"

        # modify the order
        order["status"] = "exchange requested"
        order["exchange_items"] = sorted(item_ids)
        order["exchange_new_items"] = sorted(new_item_ids)
        order["exchange_payment_method_id"] = payment_method_id
        order["exchange_price_difference"] = diff_price

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "exchange_delivered_order_items",
                "description": (
                    "Exchange items in a delivered order to new items of the same product type. "
                    "For a delivered order, return or exchange can be only done once by the agent. "
                    "The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "item_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": "The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list.",
                        },
                        "new_item_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": (
                                "The item ids to be exchanged for, each such as '1008292230'. "
                                "There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product."
                            ),
                        },
                        "payment_method_id": {
                            "type": "string",
                            "description": (
                                "The payment method id to pay or receive refund for the item price difference, "
                                "such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details."
                            ),
                        },
                    },
                    "required": [
                        "order_id",
                        "item_ids",
                        "new_item_ids",
                        "payment_method_id",
                    ],
                },
            },
        }


class FindUserIdByEmail(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], email: str) -> str:
        users = data["users"]
        for user_id, profile in users.items():
            if profile["email"].lower() == email.lower():
                return user_id
        return "Error: user not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "find_user_id_by_email",
                "description": "Find user id by email. If the user is not found, the function will return an error message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email of the user, such as 'something@example.com'.",
                        },
                    },
                    "required": ["email"],
                },
            },
        }


class FindUserIdByNameZip(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any], first_name: str, last_name: str, zip: str
    ) -> str:
        users = data["users"]
        for user_id, profile in users.items():
            if (
                profile["name"]["first_name"].lower() == first_name.lower()
                and profile["name"]["last_name"].lower() == last_name.lower()
                and profile["address"]["zip"] == zip
            ):
                return user_id
        return "Error: user not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "find_user_id_by_name_zip",
                "description": (
                    "Find user id by first name, last name, and zip code. If the user is not found, the function "
                    "will return an error message. By default, find user id by email, and only call this function "
                    "if the user is not found by email or cannot remember email."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the customer, such as 'John'.",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the customer, such as 'Doe'.",
                        },
                        "zip": {
                            "type": "string",
                            "description": "The zip code of the customer, such as '12345'.",
                        },
                    },
                    "required": ["first_name", "last_name", "zip"],
                },
            },
        }


class GetOrderDetails(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], order_id: str) -> str:
        orders = data["orders"]
        if order_id in orders:
            return json.dumps(orders[order_id])
        return "Error: order not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_order_details",
                "description": "Get the status and details of an order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                    },
                    "required": ["order_id"],
                },
            },
        }


class GetProductDetails(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], product_id: str) -> str:
        products = data["products"]
        if product_id in products:
            return json.dumps(products[product_id])
        return "Error: product not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_product_details",
                "description": "Get the inventory details of a product.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "The product id, such as '6086499569'. Be careful the product id is different from the item id.",
                        },
                    },
                    "required": ["product_id"],
                },
            },
        }


class GetUserDetails(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], user_id: str) -> str:
        users = data["users"]
        if user_id in users:
            return json.dumps(users[user_id])
        return "Error: user not found"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_user_details",
                "description": "Get the details of a user, including their orders.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user id, such as 'sara_doe_496'.",
                        },
                    },
                    "required": ["user_id"],
                },
            },
        }


class ListAllProductTypes(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any]) -> str:
        products = data["products"]
        product_dict = {
            product["name"]: product["product_id"]
            for product in products.values()
        }
        product_dict = dict(sorted(product_dict.items()))
        return json.dumps(product_dict)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "list_all_product_types",
                "description": "List the name and product id of all product types. Each product type has a variety of different items with unique item ids and options. There are only 50 product types in the store.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }


class ModifyPendingOrderAddress(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        order_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> str:
        # Check if the order exists and is pending
        orders = data["orders"]
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "pending":
            return "Error: non-pending order cannot be modified"

        # Modify the address
        order["address"] = {
            "address1": address1,
            "address2": address2,
            "city": city,
            "state": state,
            "country": country,
            "zip": zip,
        }
        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "modify_pending_order_address",
                "description": "Modify the shipping address of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "address1": {
                            "type": "string",
                            "description": "The first line of the address, such as '123 Main St'.",
                        },
                        "address2": {
                            "type": "string",
                            "description": "The second line of the address, such as 'Apt 1' or ''.",
                        },
                        "city": {
                            "type": "string",
                            "description": "The city, such as 'San Francisco'.",
                        },
                        "state": {
                            "type": "string",
                            "description": "The state, such as 'CA'.",
                        },
                        "country": {
                            "type": "string",
                            "description": "The country, such as 'USA'.",
                        },
                        "zip": {
                            "type": "string",
                            "description": "The zip code, such as '12345'.",
                        },
                    },
                    "required": [
                        "order_id",
                        "address1",
                        "address2",
                        "city",
                        "state",
                        "country",
                        "zip",
                    ],
                },
            },
        }


class ModifyPendingOrderItems(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> str:
        products, orders, users = (
            data["products"],
            data["orders"],
            data["users"],
        )

        # Check if the order exists and is pending
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "pending":
            return "Error: non-pending order cannot be modified"

        # Check if the items to be modified exist
        all_item_ids = [item["item_id"] for item in order["items"]]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                return f"Error: {item_id} not found"

        # Check new items exist, match old items, and are available
        if len(item_ids) != len(new_item_ids):
            return "Error: the number of items to be exchanged should match"

        diff_price = 0
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next(
                order_item
                for order_item in order["items"]
                if order_item["item_id"] == item_id
            )
            product_id = item["product_id"]
            if not (
                new_item_id in products[product_id]["variants"]
                and products[product_id]["variants"][new_item_id]["available"]
            ):
                return f"Error: new item {new_item_id} not found or available"

            old_price = item["price"]
            new_price = products[product_id]["variants"][new_item_id]["price"]
            diff_price += new_price - old_price

        # Check if the payment method exists
        if payment_method_id not in users[order["user_id"]]["payment_methods"]:
            return "Error: payment method not found"

        # If the new item is more expensive, check if the gift card has enough balance
        payment_method = users[order["user_id"]]["payment_methods"][
            payment_method_id
        ]
        if (
            payment_method["source"] == "gift_card"
            and payment_method["balance"] < diff_price
        ):
            return (
                "Error: insufficient gift card balance to pay for the new item"
            )

        # Handle the payment or refund
        order["payment_history"].append(
            {
                "transaction_type": "payment" if diff_price > 0 else "refund",
                "amount": abs(diff_price),
                "payment_method_id": payment_method_id,
            }
        )
        if payment_method["source"] == "gift_card":
            payment_method["balance"] -= diff_price
            payment_method["balance"] = round(payment_method["balance"], 2)

        # Modify the order
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next(
                order_item
                for order_item in order["items"]
                if order_item["item_id"] == item_id
            )
            item["item_id"] = new_item_id
            item["price"] = products[item["product_id"]]["variants"][
                new_item_id
            ]["price"]
            item["options"] = products[item["product_id"]]["variants"][
                new_item_id
            ]["options"]
        order["status"] = "pending (item modified)"

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "modify_pending_order_items",
                "description": "Modify items in a pending order to new items of the same product type. For a pending order, this function can only be called once. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "item_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": "The item ids to be modified, each such as '1008292230'. There could be duplicate items in the list.",
                        },
                        "new_item_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": "The item ids to be modified for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product.",
                        },
                        "payment_method_id": {
                            "type": "string",
                            "description": "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.",
                        },
                    },
                    "required": [
                        "order_id",
                        "item_ids",
                        "new_item_ids",
                        "payment_method_id",
                    ],
                },
            },
        }


class ModifyPendingOrderPayment(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        order_id: str,
        payment_method_id: str,
    ) -> str:
        orders = data["orders"]

        # Check if the order exists and is pending
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "pending":
            return "Error: non-pending order cannot be modified"

        # Check if the payment method exists
        if (
            payment_method_id
            not in data["users"][order["user_id"]]["payment_methods"]
        ):
            return "Error: payment method not found"

        # Check that the payment history should only have one payment
        if (
            len(order["payment_history"]) > 1
            or order["payment_history"][0]["transaction_type"] != "payment"
        ):
            return "Error: there should be exactly one payment for a pending order"

        # Check that the payment method is different
        if (
            order["payment_history"][0]["payment_method_id"]
            == payment_method_id
        ):
            return "Error: the new payment method should be different from the current one"

        amount = order["payment_history"][0]["amount"]
        payment_method = data["users"][order["user_id"]]["payment_methods"][
            payment_method_id
        ]

        # Check if the new payment method has enough balance if it is a gift card
        if (
            payment_method["source"] == "gift_card"
            and payment_method["balance"] < amount
        ):
            return "Error: insufficient gift card balance to pay for the order"

        # Modify the payment method
        order["payment_history"].extend(
            [
                {
                    "transaction_type": "payment",
                    "amount": amount,
                    "payment_method_id": payment_method_id,
                },
                {
                    "transaction_type": "refund",
                    "amount": amount,
                    "payment_method_id": order["payment_history"][0][
                        "payment_method_id"
                    ],
                },
            ]
        )

        # If payment is made by gift card, update the balance
        if payment_method["source"] == "gift_card":
            payment_method["balance"] -= amount
            payment_method["balance"] = round(payment_method["balance"], 2)

        # If refund is made to a gift card, update the balance
        if "gift_card" in order["payment_history"][0]["payment_method_id"]:
            old_payment_method = data["users"][order["user_id"]][
                "payment_methods"
            ][order["payment_history"][0]["payment_method_id"]]
            old_payment_method["balance"] += amount
            old_payment_method["balance"] = round(
                old_payment_method["balance"], 2
            )

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "modify_pending_order_payment",
                "description": "Modify the payment method of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.",
                        },
                        "payment_method_id": {
                            "type": "string",
                            "description": "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.",
                        },
                    },
                    "required": [
                        "order_id",
                        "payment_method_id",
                    ],
                },
            },
        }


class ModifyUserAddress(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        user_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> str:
        users = data["users"]
        if user_id not in users:
            return "Error: user not found"
        user = users[user_id]
        user["address"] = {
            "address1": address1,
            "address2": address2,
            "city": city,
            "state": state,
            "country": country,
            "zip": zip,
        }
        return json.dumps(user)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "modify_user_address",
                "description": "Modify the default address of a user. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user id, such as 'sara_doe_496'.",
                        },
                        "address1": {
                            "type": "string",
                            "description": "The first line of the address, such as '123 Main St'.",
                        },
                        "address2": {
                            "type": "string",
                            "description": "The second line of the address, such as 'Apt 1' or ''.",
                        },
                        "city": {
                            "type": "string",
                            "description": "The city, such as 'San Francisco'.",
                        },
                        "state": {
                            "type": "string",
                            "description": "The state, such as 'CA'.",
                        },
                        "country": {
                            "type": "string",
                            "description": "The country, such as 'USA'.",
                        },
                        "zip": {
                            "type": "string",
                            "description": "The zip code, such as '12345'.",
                        },
                    },
                    "required": [
                        "user_id",
                        "address1",
                        "address2",
                        "city",
                        "state",
                        "country",
                        "zip",
                    ],
                },
            },
        }


class ReturnDeliveredOrderItems(Tool):
    @staticmethod
    def invoke(
        data: Dict[str, Any],
        order_id: str,
        item_ids: List[str],
        payment_method_id: str,
    ) -> str:
        orders = data["orders"]

        # Check if the order exists and is delivered
        if order_id not in orders:
            return "Error: order not found"
        order = orders[order_id]
        if order["status"] != "delivered":
            return "Error: non-delivered order cannot be returned"

        # Check if the payment method exists and is either the original payment method or a gift card
        if (
            payment_method_id
            not in data["users"][order["user_id"]]["payment_methods"]
        ):
            return "Error: payment method not found"
        if (
            "gift_card" not in payment_method_id
            and payment_method_id
            != order["payment_history"][0]["payment_method_id"]
        ):
            return "Error: payment method should be either the original payment method or a gift card"

        # Check if the items to be returned exist (there could be duplicate items in either list)
        all_item_ids = [item["item_id"] for item in order["items"]]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                return "Error: some item not found"

        # Update the order status
        order["status"] = "return requested"
        order["return_items"] = sorted(item_ids)
        order["return_payment_method_id"] = payment_method_id

        return json.dumps(order)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "return_delivered_order_items",
                "description": (
                    "Return some items of a delivered order. The order status will be changed to 'return requested'. "
                    "The agent needs to explain the return detail and ask for explicit user confirmation (yes/no) to proceed. "
                    "The user will receive follow-up email for how and where to return the item."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": (
                                "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."
                            ),
                        },
                        "item_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "The item ids to be returned, each such as '1008292230'. There could be duplicate items in the list."
                            ),
                        },
                        "payment_method_id": {
                            "type": "string",
                            "description": (
                                "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. "
                                "These can be looked up from the user or order details."
                            ),
                        },
                    },
                    "required": ["order_id", "item_ids", "payment_method_id"],
                },
            },
        }


class Think(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], thought: str) -> str:
        # This method does not change the state of the data; it simply returns an empty string.
        return ""

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "think",
                "description": (
                    "Use the tool to think about something. It will not obtain new information or change the database, "
                    "but just append the thought to the log. Use it when complex reasoning or some cache memory is needed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thought": {
                            "type": "string",
                            "description": "A thought to think about.",
                        },
                    },
                    "required": ["thought"],
                },
            },
        }


class TransferToHumanAgents(Tool):
    @staticmethod
    def invoke(data: Dict[str, Any], summary: str) -> str:
        # This method simulates the transfer to a human agent.
        return "Transfer successful"

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "transfer_to_human_agents",
                "description": (
                    "Transfer the user to a human agent, with a summary of the user's issue. "
                    "Only transfer if the user explicitly asks for a human agent, or if the user's issue cannot be resolved by the agent with the available tools."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A summary of the user's issue.",
                        },
                    },
                    "required": ["summary"],
                },
            },
        }


ALL_TOOLS = [
    Calculate,
    CancelPendingOrder,
    ExchangeDeliveredOrderItems,
    FindUserIdByEmail,
    FindUserIdByNameZip,
    GetOrderDetails,
    GetProductDetails,
    GetUserDetails,
    ListAllProductTypes,
    ModifyPendingOrderAddress,
    ModifyPendingOrderItems,
    ModifyPendingOrderPayment,
    ModifyUserAddress,
    ReturnDeliveredOrderItems,
    Think,
    TransferToHumanAgents,
]
