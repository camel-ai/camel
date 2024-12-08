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
import os
from unittest.mock import MagicMock, patch

import pytest
from stripe import (
    Balance,
    BalanceTransaction,
    Customer,
    PaymentIntent,
    Refund,
)

from camel.toolkits.stripe_toolkit import StripeToolkit


@pytest.fixture(scope="function")
def stripe_toolkit_fixture():
    r"""Fixture to set up the StripeToolkit with a mock API key."""
    with patch.dict(os.environ, {"stripe.api_key": "sk_test_xxxx"}):
        stripe.api_key = os.environ.get("stripe.api_key", None)
        toolkit = StripeToolkit()
        return toolkit


r"""Customer Tests
"""
@pytest.mark.usefixtures("stripe_toolkit_fixture")
class TestCustomer:
    @patch('stripe.Customer.retrieve')
    def test_get_customer_success(
        self, mock_customer_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        customer_id = "cus_abc"
        customer_name = "Jody Telar"
        customer_data = Customer()
        customer_data.id = customer_id
        customer_data.name = customer_name
        mock_customer_retrieve.return_value = customer_data

        result = stripe_toolkit_fixture.customers.get_customer(customer_id)
        # Assert
        mock_customer_retrieve.assert_called_once_with(customer_id)
        expected_result = json.dumps(customer_data)
        assert result == expected_result

    @patch('stripe.Customer.retrieve')
    def test_get_customer_exception(
        self, mock_customer_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        customer_id = "invalid_id"
        exception_message = "Customer not found"
        mock_customer_retrieve.side_effect = Exception(exception_message)
        customer_adapter = stripe_toolkit_fixture.customers
        customer_adapter.logger = MagicMock()
        result = customer_adapter.get_customer(customer_id)
        expected_error = (
            f"Unexpected error in get_customer: {exception_message}"
        )
        assert expected_error in result

    @patch('stripe.Customer.list')
    def test_list_customers_success(
        self, mock_customer_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        customer1 = Customer()
        customer1.id = "cus_123"
        customer1.name = "Alice"

        customer2 = Customer()
        customer2.id = "cus_456"
        customer2.name = "Bob"

        customer_list = MagicMock()
        customer_list.data = [customer1, customer2]
        mock_customer_list.return_value = customer_list

        # Act
        result = stripe_toolkit_fixture.customers.list_customers(limit=limit)

        # Assert
        mock_customer_list.assert_called_once_with(limit=limit)
        expected_result = json.dumps([customer1, customer2])
        assert result == expected_result

    @patch('stripe.Customer.list')
    def test_list_customers_exception(
        self, mock_customer_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        exception_message = "List customers failed"
        mock_customer_list.side_effect = Exception(exception_message)
        customer_adapter = stripe_toolkit_fixture.customers
        customer_adapter.logger = MagicMock()

        # Act
        result = customer_adapter.list_customers(limit=limit)

        # Assert
        expected_error = (
            f"Unexpected error in list_customers: {exception_message}"
        )
        assert expected_error in result


r"""Balance Tests
"""
@pytest.mark.usefixtures("stripe_toolkit_fixture")
class TestBalance:
    @patch('stripe.Balance.retrieve')
    def test_get_balance_success(
        self, mock_balance_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        balance_data = Balance()
        balance_data.object = 'balance'
        balance_data.available = []
        balance_data.pending = []
        mock_balance_retrieve.return_value = balance_data

        # Act
        result = stripe_toolkit_fixture.balance.get_balance()

        # Assert
        mock_balance_retrieve.assert_called_once()
        expected_result = json.dumps(balance_data)
        assert result == expected_result

    @patch('stripe.Balance.retrieve')
    def test_get_balance_exception(
        self, mock_balance_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        exception_message = "Balance retrieval failed"
        mock_balance_retrieve.side_effect = Exception(exception_message)
        balance_adapter = stripe_toolkit_fixture.balance
        balance_adapter.logger = MagicMock()

        # Act
        result = balance_adapter.get_balance()

        # Assert
        expected_error = (
            f"Unexpected error in get_balance: {exception_message}"
        )
        assert expected_error in result

    @patch('stripe.BalanceTransaction.list')
    def test_list_balance_transactions_success(
        self, mock_balance_transaction_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        transaction1 = BalanceTransaction()
        transaction1.id = 'txn_1'
        transaction1.amount = 1000

        transaction2 = BalanceTransaction()
        transaction2.id = 'txn_2'
        transaction2.amount = 2000

        transaction_list = MagicMock()
        transaction_list.data = [transaction1, transaction2]
        mock_balance_transaction_list.return_value = transaction_list

        # Act
        result = stripe_toolkit_fixture.balance.list_balance_transactions(
            limit=limit
        )

        # Assert
        mock_balance_transaction_list.assert_called_once_with(limit=limit)
        expected_result = json.dumps([transaction1, transaction2])
        assert result == expected_result

    @patch('stripe.BalanceTransaction.list')
    def test_list_balance_transactions_exception(
        self, mock_balance_transaction_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        exception_message = "List balance transactions failed"
        mock_balance_transaction_list.side_effect = Exception(
            exception_message
        )
        balance_adapter = stripe_toolkit_fixture.balance
        balance_adapter.logger = MagicMock()

        # Act
        result = balance_adapter.list_balance_transactions(limit=limit)

        # Assert
        expected_error = f"Unexpected error in list_balance_transactions: {exception_message}"
        assert expected_error in result


r"""Payment Tests
"""
@pytest.mark.usefixtures("stripe_toolkit_fixture")
class TestPayment:
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_payment_success(
        self, mock_payment_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        payment_id = "pi_123"
        payment_data = PaymentIntent()
        payment_data.id = payment_id
        payment_data.amount = 1000
        mock_payment_retrieve.return_value = payment_data

        # Act
        result = stripe_toolkit_fixture.payments.get_payment(payment_id)

        # Assert
        mock_payment_retrieve.assert_called_once_with(payment_id)
        expected_result = json.dumps(payment_data)
        assert result == expected_result

    @patch('stripe.PaymentIntent.retrieve')
    def test_get_payment_exception(
        self, mock_payment_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        payment_id = "invalid_id"
        exception_message = "Payment not found"
        mock_payment_retrieve.side_effect = Exception(exception_message)
        payment_adapter = stripe_toolkit_fixture.payments
        payment_adapter.logger = MagicMock()

        # Act
        result = payment_adapter.get_payment(payment_id)

        # Assert
        expected_error = (
            f"Unexpected error in get_payment: {exception_message}"
        )
        assert expected_error in result

    @patch('stripe.PaymentIntent.list')
    def test_list_payments_success(
        self, mock_payment_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        payment1 = PaymentIntent()
        payment1.id = 'pi_123'
        payment1.amount = 1000

        payment2 = PaymentIntent()
        payment2.id = 'pi_456'
        payment2.amount = 2000

        payment_list = MagicMock()
        payment_list.data = [payment1, payment2]
        mock_payment_list.return_value = payment_list

        # Act
        result = stripe_toolkit_fixture.payments.list_payments(limit=limit)

        # Assert
        mock_payment_list.assert_called_once_with(limit=limit)
        expected_result = json.dumps([payment1, payment2])
        assert result == expected_result

    @patch('stripe.PaymentIntent.list')
    def test_list_payments_exception(
        self, mock_payment_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        exception_message = "List payments failed"
        mock_payment_list.side_effect = Exception(exception_message)
        payment_adapter = stripe_toolkit_fixture.payments
        payment_adapter.logger = MagicMock()

        # Act
        result = payment_adapter.list_payments(limit=limit)

        # Assert
        expected_error = (
            f"Unexpected error in list_payments: {exception_message}"
        )
        assert expected_error in result


r"""Refund Tests
"""
@pytest.mark.usefixtures("stripe_toolkit_fixture")
class TestRefund:
    @patch('stripe.Refund.retrieve')
    def test_get_refund_success(
        self, mock_refund_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        refund_id = "re_123"
        refund_data = Refund()
        refund_data.id = refund_id
        refund_data.amount = 500
        mock_refund_retrieve.return_value = refund_data

        # Act
        result = stripe_toolkit_fixture.refunds.get_refund(refund_id)

        # Assert
        mock_refund_retrieve.assert_called_once_with(refund_id)
        expected_result = json.dumps(refund_data)
        assert result == expected_result

    @patch('stripe.Refund.retrieve')
    def test_get_refund_exception(
        self, mock_refund_retrieve, stripe_toolkit_fixture
    ):
        # Arrange
        refund_id = "invalid_id"
        exception_message = "Refund not found"
        mock_refund_retrieve.side_effect = Exception(exception_message)
        refund_adapter = stripe_toolkit_fixture.refunds
        refund_adapter.logger = MagicMock()

        # Act
        result = refund_adapter.get_refund(refund_id)

        # Assert
        expected_error = f"Unexpected error in get_refund: {exception_message}"
        assert expected_error in result

    @patch('stripe.Refund.list')
    def test_list_refunds_success(
        self, mock_refund_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        refund1 = Refund()
        refund1.id = 're_123'
        refund1.amount = 500

        refund2 = Refund()
        refund2.id = 're_456'
        refund2.amount = 1000

        refund_list = MagicMock()
        refund_list.data = [refund1, refund2]
        mock_refund_list.return_value = refund_list

        # Act
        result = stripe_toolkit_fixture.refunds.list_refunds(limit=limit)

        # Assert
        mock_refund_list.assert_called_once_with(limit=limit)
        expected_result = json.dumps([refund1, refund2])
        assert result == expected_result

    @patch('stripe.Refund.list')
    def test_list_refunds_exception(
        self, mock_refund_list, stripe_toolkit_fixture
    ):
        # Arrange
        limit = 2
        exception_message = "List refunds failed"
        mock_refund_list.side_effect = Exception(exception_message)
        refund_adapter = stripe_toolkit_fixture.refunds
        refund_adapter.logger = MagicMock()

        # Act
        result = refund_adapter.list_refunds(limit=limit)

        # Assert
        expected_error = (
            f"Unexpected error in list_refunds: {exception_message}"
        )
        assert expected_error in result