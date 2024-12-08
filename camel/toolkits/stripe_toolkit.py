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

import json
import logging
import os
from typing import Any, Dict, List, Union

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class StripeBaseAdapter:
    def __init__(self, toolkit: 'StripeToolkit'):
        self.logger = toolkit.logger.getChild(self.__class__.__name__)

    def handle_exception(self, func_name: str, error: Exception) -> str:
        r"""Handle exceptions by logging and returning an error message.

        Args:
            func_name (str): The name of the function where the exception occurred.
            error (Exception): The exception instance.

        Returns:
            str: An error message string.
        """
        import stripe

        if isinstance(error, stripe.error.StripeError):
            message = error.user_message or str(error)
            self.logger.error(f"Stripe error in {func_name}: {message}")
            return f"Stripe error in {func_name}: {message}"
        else:
            self.logger.error(f"Unexpected error in {func_name}: {error!s}")
            return f"Unexpected error in {func_name}: {error!s}"


class StripeToolkit(BaseToolkit):
    r"""A class representing a toolkit for Stripe operations.
    have to config "stripe.api_key" in the file .env

    This toolkit provides methods to interact with the Stripe  API,
    allowing users to operate stripe core resources, including Balance,
    Charges, Customers, Payout, Refunds

    Attributes:
        retries (int): Number of retries for API requests in case of failure.
        version (str): API version.
    """

    def __init__(self, retries: int = 3):
        r"""Initializes the WhatsAppToolkit with the specified number of
        retries and delay.

        Args:
            retries (int): Number of times to retry the request in case of
                failure. (default: :obj:`3`)
        """
        import stripe

        stripe.log = 'info'
        stripe.max_network_retries = retries
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(handler)

        stripe.api_key = os.environ.get("STRIPE_API_KEY", None)
        if not stripe.api_key:
            raise ValueError(
                "stripe.api_key credentials are not set. "
                "Please set the stripe.api_key environment variables."
            )
        else:
            self.logger.info(
                "StripeToolkit initialized with provided API key."
            )
            
    def get_customer(self, customer_id: str) -> str:
        r"""Retrieve a customer by ID.

        Args:
            customer_id (str): The ID of the customer to retrieve.

        Returns:
            str: The customer data as a dictionary.
        """
        import stripe
        try:
            self.logger.info(f"Retrieving customer with ID: {customer_id}")
            customer = stripe.Customer.retrieve(customer_id)
            self.logger.info(f"Retrieved customer: {customer.id}")
            json_string = json.dumps(customer)
            return json_string
        except Exception as e:
            return self.handle_exception("get_customer", e)
    
    def list_customers(self, limit: int = 100) -> str:
        r"""List customers.

        Args:
            limit (int, optional): Number of customers to retrieve. Defaults to 100.

        Returns:
            str: An output str if successful, or an error message string if failed.
        """
        try:
            self.logger.info(f"Listing customers with limit={limit}")
            customers = stripe.Customer.list(limit=limit).data
            self.logger.info(
                f"Successfully retrieved {len(customers)} customers."
            )
            return json.dumps([customer for customer in customers])
        except Exception as e:
            return self.handle_exception("list_customers", e)

    def get_balance(self) -> str:
        r"""Retrieve the account balance.

        Returns:
            str: A str containing the account balance if successful, or an
                error message string if failed.
        """
        try:
            self.logger.info("Retrieving account balance.")
            balance = stripe.Balance.retrieve()
            self.logger.info(
                f"Successfully retrieved account balance: {balance}."
            )
            return json.dumps(balance)
        except Exception as e:
            return self.handle_exception("get_balance", e)

    def list_balance_transactions(self, limit: int = 100) ->str:
            r"""List balance transactions.

            Args:
                limit (int, optional): Number of balance transactions to retrieve. Defaults to 100.

            Returns:
                Union[List[Dict[str, Any]], str]: A list of balance transaction data dictionaries
                if successful, or an error message string if failed.
            """
            import stripe
            try:
                self.logger.info(
                    f"Listing balance transactions with limit={limit}"
                )
                transactions = stripe.BalanceTransaction.list(limit=limit).data
                self.logger.info(
                    f"Successfully retrieved {len(transactions)} balance transactions."
                )
                return json.dumps(
                    [transaction for transaction in transactions]
                )
            except Exception as e:
                return self.handle_exception("list_balance_transactions", e)

    def get_payment(self, payment_id: str) -> str:
            r"""Retrieve a payment by ID.

            Args:
                payment_id (str): The ID of the payment to retrieve.

            Returns:
                Union[Dict[str, Any], str]: The payment data as a dictionary if successful,
                or an error message string if failed.
            """
            import stripe
            try:
                self.logger.info(f"Retrieving payment with ID: {payment_id}")
                payment = stripe.PaymentIntent.retrieve(payment_id)
                self.logger.info(f"Retrieved payment: {payment.id}")
                return json.dumps(payment)
            except Exception as e:
                return self.handle_exception("get_payment", e)

    def list_payments(self, limit: int = 100) -> str:
        r"""List payments.

        Args:
            limit (int, optional): Number of payments to retrieve. Defaults to 100.

        Returns:
            Union[List[Dict[str, Any]], str]: A list of payment data dictionaries
            if successful, or an error message string if failed.
        """
        try:
            self.logger.info(f"Listing payments with limit={limit}")
            payments = stripe.PaymentIntent.list(limit=limit).data
            self.logger.info(
                f"Successfully retrieved {len(payments)} payments."
            )
            return json.dumps([payment for payment in payments])
        except Exception as e:
            return self.handle_exception("list_payments", e)

    def get_refund(self, refund_id: str) -> str:
        r"""Retrieve a refund by ID.

        Args:
            refund_id (str): The ID of the refund to retrieve.

        Returns:
            Union[Dict[str, Any], str]: The refund data as a dictionary if successful,
            or an error message string if failed.
        """
        try:
            self.logger.info(f"Retrieving refund with ID: {refund_id}")
            refund = stripe.Refund.retrieve(refund_id)
            self.logger.info(f"Retrieved refund: {refund.id}")
            return json.dumps(refund)
        except Exception as e:
            return self.handle_exception("get_refund", e)

    def list_refunds( self, limit: int = 100) -> str:
        r"""List refunds.

        Args:
            limit (int, optional): Number of refunds to retrieve. Defaults to 100.

        Returns:
            Union[List[Dict[str, Any]], str]: A list of refund data dictionaries
            if successful, or an error message string if failed.
        """
        try:
            self.logger.info(f"Listing refunds with limit={limit}")
            refunds = stripe.Refund.list(limit=limit).data
            self.logger.info(
                f"Successfully retrieved {len(refunds)} refunds."
            )
            return json.dumps([refund for refund in refunds])
        except Exception as e:
            return self.handle_exception("list_refunds", e)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for the
                toolkit methods.
        """
        return [
            FunctionTool(self.customers.get_customer),
            FunctionTool(self.customers.list_customers),
            FunctionTool(self.balance.get_balance),
            FunctionTool(self.balance.list_balance_transactions),
            FunctionTool(self.payments.get_payment),
            FunctionTool(self.payments.list_payments),
            FunctionTool(self.refunds.get_refund),
            FunctionTool(self.refunds.list_refunds),
        ]
