from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from tau2.domains.retail.utils import RETAIL_DB_PATH
from tau2.environment.db import DB


class Variant(BaseModel):
    """Represents a specific variant of a product with its options, availability and price"""

    item_id: str = Field(description="Unique identifier for the variant")
    options: Dict[str, str] = Field(
        description="Dictionary of option names to values (e.g. {'color': 'blue', 'size': 'large'})"
    )
    available: bool = Field(description="Whether this variant is currently in stock")
    price: float = Field(description="Price of this variant")


class Product(BaseModel):
    """Represents a product with its variants"""

    name: str = Field(description="Name of the product")
    product_id: str = Field(description="Unique identifier for the product")
    variants: Dict[str, Variant] = Field(
        description="Dictionary of variants indexed by variant ID"
    )


class UserName(BaseModel):
    """Represents a user's full name"""

    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")


class UserAddress(BaseModel):
    """Represents a physical address"""

    address1: str = Field(description="Primary address line")
    address2: str = Field(description="Secondary address line")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    state: str = Field(description="State or province name")
    zip: str = Field(description="Postal code")


class PaymentMethodBase(BaseModel):
    source: str = Field(description="Type of payment method")
    id: str = Field(description="Unique identifier for the payment method")


class CreditCard(PaymentMethodBase):
    source: Literal["credit_card"] = Field(
        description="Indicates this is a credit card payment method"
    )
    brand: str = Field(description="Credit card brand (e.g., visa, mastercard)")
    last_four: str = Field(description="Last four digits of the credit card")


class Paypal(PaymentMethodBase):
    source: Literal["paypal"] = Field(
        description="Indicates this is a paypal payment method"
    )


class GiftCard(PaymentMethodBase):
    source: Literal["gift_card"] = Field(
        description="Indicates this is a gift card payment method"
    )
    balance: float = Field(description="Gift card value amount")
    id: str = Field(description="Unique identifier for the gift card")


PaymentMethod = Union[CreditCard, GiftCard, Paypal]


class User(BaseModel):
    """Represents a user with their personal information, payment methods and order history"""

    user_id: str = Field(description="Unique identifier for the user")
    name: UserName = Field(description="User's full name")
    address: UserAddress = Field(description="User's primary address")
    email: str = Field(description="User's email address")
    payment_methods: Dict[str, PaymentMethod] = Field(
        description="Dictionary of payment methods indexed by payment method ID"
    )
    orders: List[str] = Field(description="List of order IDs associated with this user")


class OrderFullfilment(BaseModel):
    """Represents the fulfillment details for items in an order"""

    tracking_id: list[str] = Field(description="List of tracking IDs for shipments")
    item_ids: list[str] = Field(
        description="List of item IDs included in this fulfillment"
    )


class OrderItem(BaseModel):
    """Represents an item in an order"""

    name: str = Field(description="Name of the product")
    product_id: str = Field(description="ID of the product")
    item_id: str = Field(description="ID of the specific variant")
    price: float = Field(description="Price of the item at time of purchase")
    options: Dict[str, str] = Field(description="Options selected for this item")


OrderPaymentType = Literal["payment", "refund"]


class OrderPayment(BaseModel):
    """Represents a payment or refund transaction for an order"""

    transaction_type: OrderPaymentType = Field(
        description="Type of transaction (payment or refund)"
    )
    amount: float = Field(description="Amount of the transaction")
    payment_method_id: str = Field(description="ID of the payment method used")


OrderStatus = Literal[
    "processed",
    "pending",
    "pending (item modified)",
    "delivered",
    "cancelled",
    "exchange requested",
    "return requested",
]

CancelReason = Literal["no longer needed", "ordered by mistake"]


class BaseOrder(BaseModel):
    """Represents an order with its items, status, fulfillment and payment details"""

    order_id: str = Field(description="Unique identifier for the order")
    user_id: str = Field(description="Unique identifier for the user")
    address: UserAddress = Field(description="Address of the user")
    items: List[OrderItem] = Field(description="Items in the order")
    status: OrderStatus = Field(description="Status of the order")
    fulfillments: List[OrderFullfilment] = Field(
        description="Fulfillments of the order"
    )
    payment_history: List[OrderPayment] = Field(description="Payments of the order")
    cancel_reason: Optional[CancelReason] = Field(
        description="Reason for cancelling the order. Can'no longer needed' or 'ordered by mistake'",
        default=None,
    )
    exchange_items: Optional[List[str]] = Field(
        description="Items to be exchanged", default=None
    )
    exchange_new_items: Optional[List[str]] = Field(
        description="Items exchanged for", default=None
    )
    exchange_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the exchange", default=None
    )
    exchange_price_difference: Optional[float] = Field(
        description="Price difference for the exchange", default=None
    )
    return_items: Optional[List[str]] = Field(
        description="Items to be returned", default=None
    )
    return_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the return", default=None
    )


class Order(BaseModel):
    """Represents an order with its items, status, fulfillment and payment details"""

    order_id: str = Field(description="Unique identifier for the order")
    user_id: str = Field(description="Unique identifier for the user")
    address: UserAddress = Field(description="Address of the user")
    items: List[OrderItem] = Field(description="Items in the order")
    status: OrderStatus = Field(description="Status of the order")
    fulfillments: List[OrderFullfilment] = Field(
        description="Fulfillments of the order"
    )
    payment_history: List[OrderPayment] = Field(description="Payments of the order")
    cancel_reason: Optional[CancelReason] = Field(
        description="Reason for cancelling the order. Should be 'no longer needed' or 'ordered by mistake'",
        default=None,
    )
    exchange_items: Optional[List[str]] = Field(
        description="Items to be exchanged", default=None
    )
    exchange_new_items: Optional[List[str]] = Field(
        description="Items exchanged for", default=None
    )
    exchange_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the exchange", default=None
    )
    exchange_price_difference: Optional[float] = Field(
        description="Price difference for the exchange", default=None
    )
    return_items: Optional[List[str]] = Field(
        description="Items to be returned", default=None
    )
    return_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the return", default=None
    )


class RetailDB(DB):
    """Database containing all retail-related data including products, users and orders"""

    products: Dict[str, Product] = Field(
        description="Dictionary of all products indexed by product ID"
    )
    users: Dict[str, User] = Field(
        description="Dictionary of all users indexed by user ID"
    )
    orders: Dict[str, Order] = Field(
        description="Dictionary of all orders indexed by order ID"
    )

    def get_statistics(self) -> dict[str, Any]:
        """Get the statistics of the database."""
        num_products = len(self.products)
        num_users = len(self.users)
        num_orders = len(self.orders)
        total_num_items = sum(
            len(product.variants) for product in self.products.values()
        )
        return {
            "num_products": num_products,
            "num_users": num_users,
            "num_orders": num_orders,
            "total_num_items": total_num_items,
        }


def get_db():
    return RetailDB.load(RETAIL_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())
