# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import os
from typing import Any, Dict, List, Union
import requests
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
import stripe
import logging

class StripeBaseAdapter:
    def __init__(self, toolkit: 'StripeToolkit'):
        self.logger = toolkit.logger.getChild(self.__class__.__name__)
            
    def handle_exception(self, func_name: str, error: Exception) -> str:
        """
        Handle exceptions by logging and returning an error message.
            
        Args:
            func_name (str): The name of the function where the exception occurred.
            error (Exception): The exception instance.

        Returns:
            str: An error message string.
        """
        if isinstance(error, stripe.error.StripeError):
            message = error.user_message or str(error)
            self.logger.error(f"Stripe error in {func_name}: {message}")
            return f"Stripe error in {func_name}: {message}"
        else:
            self.logger.error(f"Unexpected error in {func_name}: {str(error)}")
            return f"Unexpected error in {func_name}: {str(error)}"
            
            
class StripeToolkit(BaseToolkit):
    r"""A class representing a toolkit for Stripe operations.

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
        stripe.log = 'info'
        stripe.max_network_retries = retries
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        
        stripe.api_key = os.environ.get("stripe.api_key", None)
        if not stripe.api_key:
            raise ValueError(
                "stripe.api_key credentials are not set. "
                "Please set the stripe.api_key environment variables."
            )
        else:
            self.logger.info("StripeToolkit initialized with provided API key.")
            
        # Initialize adapter classes
        self.customers = self.CustomerAdapter(self)
        self.balance = self.BalanceAdapter(self)
        self.payments = self.PaymentAdapter(self)
        self.refunds = self.RefundAdapter(self)
    # ------------------------
    # CustomerAdapter
    # ------------------------
    class CustomerAdapter(StripeBaseAdapter):
        """
        Adapter class for handling Stripe Customer operations.
        """
        def get_customer(self, customer_id: str) ->  Union[Dict[str, Any], str]:
            """
            Retrieve a customer by ID.

            Args:
                customer_id (str): The ID of the customer to retrieve.

            Returns:
                Optional[Dict[str, Any]]: The customer data as a dictionary, or None if not found.
            """
            try:
                self.logger.info(f"Retrieving customer with ID: {customer_id}")
                customer = stripe.Customer.retrieve(customer_id)
                self.logger.info(f"Retrieved customer: {customer.id}")
                return customer.json()
            except Exception as e:
                return self.handle_exception("get_customer", e)
        
        def list_customers(self, limit: int = 100) -> Union[List[Dict[str, Any]], str]:
            """
            List customers.

            Args:
                limit (int, optional): Number of customers to retrieve. Defaults to 100.

            Returns:
                Union[List[Dict[str, Any]], str]: A list of customer data dictionaries
                if successful, or an error message string if failed.
            """
            try:
                self.logger.info(f"Listing customers with limit={limit}")
                customers = stripe.Customer.list(limit=limit).data
                self.logger.info(
                    f"Successfully retrieved {len(customers)} customers.")
                return [customer.to_dict() for customer in customers]
            except Exception as e:
                return self.handle_exception("list_customers", e)
    # ------------------------
    # BalanceAdapter
    # ------------------------
    class BalanceAdapter(StripeBaseAdapter):
        """
        Adapter class for handling Stripe Balance operations.
        """
        def get_balance(self) -> Union[Dict[str, Any], str]:
            """
            Retrieve the account balance.

            Returns:
                Union[Dict[str, Any], str]: A dictionary containing
                the account balance if successful, or an error message string if failed.
            """
            try:
                self.logger.info("Retrieving account balance.")
                balance = stripe.Balance.retrieve()
                self.logger.info(f"Successfully retrieved account balance: {response}.")
                return balance.to_dict()
            except Exception as e:
                return self.handle_exception("get_balance", e)

        def list_balance_transactions(self, limit: int = 100) -> Union[List[Dict[str, Any]], str]:
            """
            List balance transactions.

            Args:
                limit (int, optional): Number of balance transactions to retrieve. Defaults to 100.

            Returns:
                Union[List[Dict[str, Any]], str]: A list of balance transaction data dictionaries
                if successful, or an error message string if failed.
            """
            try:
                self.logger.info(f"Listing balance transactions with limit={limit}")
                transactions = stripe.BalanceTransaction.list(limit=limit).data
                self.logger.info(
                    f"Successfully retrieved {len(transactions)} balance transactions.")
                return [transaction.to_dict() for transaction in transactions]
            except Exception as e:
                return self.handle_exception("list_balance_transactions", e)
        
    # ------------------------
    # PaymentAdapter
    # ------------------------
    class PaymentAdapter(StripeBaseAdapter):
        """
        Adapter class for handling Stripe PaymentIntent operations.
        """
        def get_payment(self, payment_id: str) -> Union[Dict[str, Any], str]:
            """
            Retrieve a payment by ID.

            Args:
                payment_id (str): The ID of the payment to retrieve.

            Returns:
                Union[Dict[str, Any], str]: The payment data as a dictionary if successful,
                or an error message string if failed.
            """
            try:
                self.logger.info(f"Retrieving payment with ID: {payment_id}")
                payment = stripe.PaymentIntent.retrieve(payment_id)
                self.logger.info(f"Retrieved payment: {payment.id}")
                return payment.to_dict()
            except Exception as e:
                return self.handle_exception("get_payment", e)

        def list_payments(self, limit: int = 100) -> Union[List[Dict[str, Any]], str]:
            """
            List payments.

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
                    f"Successfully retrieved {len(payments)} payments.")
                return [payment.to_dict() for payment in payments]
            except Exception as e:
                return self.handle_exception("list_payments", e)

    # ------------------------
    # RefundAdapter
    # ------------------------
    class RefundAdapter(StripeBaseAdapter):
        """
        Adapter class for handling Stripe Refund operations.
        """
        def get_refund(self, refund_id: str) -> Union[Dict[str, Any], str]:
            """
            Retrieve a refund by ID.

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
                return refund.to_dict()
            except Exception as e:
                return self.handle_exception("get_refund", e)

        def list_refunds(self, limit: int = 100) -> Union[List[Dict[str, Any]], str]:
            """
            List refunds.

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
                    f"Successfully retrieved {len(refunds)} refunds.")
                return [refund.to_dict() for refund in refunds]
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
            FunctionTool(self.refunds.list_refunds)
        ]
