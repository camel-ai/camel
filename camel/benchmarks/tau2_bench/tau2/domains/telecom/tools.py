"""Toolkit for the telecom system."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from tau2.domains.telecom.data_model import (
    Bill,
    BillStatus,
    Customer,
    Device,
    Line,
    LineItem,
    LineStatus,
    Plan,
    TelecomDB,
)
from tau2.domains.telecom.utils import get_today
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool

# TODO: Add an abstract base class for the tools


class IDGenerator:
    def __init__(self) -> None:
        self.id_counter = defaultdict(int)

    def get_id(self, id_type: str, id_name: Optional[str] = None) -> str:
        self.id_counter[id_type] += 1
        id_name = id_name or id_type
        return f"{id_name}_{self.id_counter[id_type]}"


class TelecomTools(ToolKitBase):
    """Tools for the telecom domain implementing the functions described in the PRD."""

    db: TelecomDB

    def __init__(self, db: TelecomDB) -> None:
        """Initialize the telecom tools with a database instance."""
        super().__init__(db)
        self.id_generator = IDGenerator()

    # Customer Lookup
    @is_tool(ToolType.READ)
    def get_customer_by_phone(self, phone_number: str) -> Customer:
        """
        Finds a customer by their primary contact or line phone number.

        Args:
            phone_number: The phone number to search for.

        Returns:
            Customer object if found, None otherwise.
        """
        # Check primary contact number
        for customer in self.db.customers:
            if customer.phone_number == phone_number:
                return customer

            # Check lines
            for line_id in customer.line_ids:
                line = self._get_line_by_id(line_id)
                if line and line.phone_number == phone_number:
                    return customer

        raise ValueError(f"Customer with phone number {phone_number} not found")

    @is_tool(ToolType.READ)
    def get_customer_by_id(self, customer_id: str) -> Customer:
        """
        Retrieves a customer directly by their unique ID.

        Args:
            customer_id: The unique identifier of the customer.

        Returns:
            Customer object if found, None otherwise.
        """
        for customer in self.db.customers:
            if customer.customer_id == customer_id:
                return customer

        raise ValueError(f"Customer with ID {customer_id} not found")

    @is_tool(ToolType.READ)
    def get_customer_by_name(self, full_name: str, dob: str) -> List[Customer]:
        """
        Searches for customers by name and DOB. May return multiple matches if names are similar,
        DOB helps disambiguate.

        Args:
            full_name: The full name of the customer.
            dob: Date of birth for verification, in the format YYYY-MM-DD.

        Returns:
            List of matching Customer objects.
        """
        matching_customers = []

        for customer in self.db.customers:
            if (
                customer.full_name.lower() == full_name.lower()
                and customer.date_of_birth == dob
            ):
                matching_customers.append(customer)

        return matching_customers

    # Helper method to get a line by phone number
    def _get_line_by_phone(self, phone_number: str) -> Line:
        """
        Retrieves a line directly by its phone number.

        Args:
            phone_number: The phone number to search for.

        Returns:
            Line object if found.

        Raises:
            ValueError: If the line with the specified phone number is not found.
        """
        for line in self.db.lines:
            if line.phone_number == phone_number:
                return line
        raise ValueError(f"Line with phone number {phone_number} not found")

    # Helper method to get a line by ID
    def _get_line_by_id(self, line_id: str) -> Line:
        """
        Retrieves a line directly by its unique ID.

        Args:
            line_id: The unique identifier of the line.

        Returns:
            Line object if found.

        Raises:
            ValueError: If the line with the specified ID is not found.
        """
        for line in self.db.lines:
            if line.line_id == line_id:
                return line
        raise ValueError(f"Line with ID {line_id} not found")

    # Helper method to get a plan by ID
    def _get_plan_by_id(self, plan_id: str) -> Plan:
        """
        Retrieves a plan directly by its unique ID.

        Args:
            plan_id: The unique identifier of the plan.

        Returns:
            Plan object if found.

        Raises:
            ValueError: If the plan with the specified ID is not found.
        """
        for plan in self.db.plans:
            if plan.plan_id == plan_id:
                return plan
        raise ValueError(f"Plan with ID {plan_id} not found")

    # Helper method to get a device by ID
    def _get_device_by_id(self, device_id: str) -> Device:
        """
        Retrieves a device directly by its unique ID.

        Args:
            device_id: The unique identifier of the device.

        Returns:
            Device object if found.

        Raises:
            ValueError: If the device with the specified ID is not found.
        """
        for device in self.db.devices:
            if device.device_id == device_id:
                return device
        raise ValueError(f"Device with ID {device_id} not found")

    # Helper method to get a bill by ID
    def _get_bill_by_id(self, bill_id: str) -> Bill:
        """
        Retrieves a bill directly by its unique ID.

        Args:
            bill_id: The unique identifier of the bill.

        Returns:
            Bill object if found.

        Raises:
            ValueError: If the bill with the specified ID is not found.
        """
        for bill in self.db.bills:
            if bill.bill_id == bill_id:
                return bill
        raise ValueError(f"Bill with ID {bill_id} not found")

    def _get_target_line(self, customer_id: str, line_id: str) -> Line:
        """
        Retrieves a line using the customer ID and line ID.

        Args:
            customer_id: The unique identifier of the customer.
            line_id: The unique identifier of the line.

        Returns:
            Line object if found.

        Raises:
            ValueError: If the line with the specified ID is not found.
        """
        customer = self.get_customer_by_id(customer_id)
        if line_id not in customer.line_ids:
            raise ValueError(f"Line {line_id} not found for customer {customer_id}")
        return self._get_line_by_id(line_id)

    def get_available_plan_ids(self) -> List[str]:
        """
        Returns all the plans that are available to the user.
        """
        return [plan.plan_id for plan in self.db.plans]

    @is_tool(ToolType.READ)
    def get_details_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieves the details for a given ID.
        The ID must be a valid ID for a Customer, Line, Device, Bill, or Plan.

        Args:
            id: The ID of the object to retrieve.

        Returns:
            The object corresponding to the ID.

        Raises:
            ValueError: If the ID is not found or if the ID format is invalid.
        """
        if id.startswith("L"):
            return self._get_line_by_id(id)
        elif id.startswith("D"):
            return self._get_device_by_id(id)
        elif id.startswith("B"):
            return self._get_bill_by_id(id)
        elif id.startswith("C"):
            return self.get_customer_by_id(id)
        elif id.startswith("P"):
            return self._get_plan_by_id(id)
        else:
            raise ValueError(f"Unknown ID format or type: {id}")

    @is_tool(ToolType.WRITE)
    def suspend_line(
        self, customer_id: str, line_id: str, reason: str
    ) -> Dict[str, Any]:
        """
        Suspends a specific line (max 6 months).
        Checks: Line status must be Active.
        Logic: Sets line status to Suspended, records suspension_start_date.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to suspend.
            reason: Reason for suspension.

        Returns:
            Dictionary with success status, message, and updated line if applicable.

        Raises:
            ValueError: If customer or line not found, or if line is not active.
        """
        target_line = self._get_target_line(customer_id, line_id)

        if target_line.status != LineStatus.ACTIVE:
            raise ValueError("Line must be active to suspend")

        target_line.status = LineStatus.SUSPENDED
        target_line.suspension_start_date = get_today()

        # Log reason
        logger.info(f"Line {line_id} suspended. Reason: {reason}")

        return {
            "message": "Line suspended successfully. $5/month holding fee will apply.",
            "line": target_line,
        }

    @is_tool(ToolType.WRITE)
    def resume_line(self, customer_id: str, line_id: str) -> Dict[str, Any]:
        """
        Resumes a suspended line.
        Checks: Line status must be Suspended or Pending Activation.
        Logic: Sets line status to Active, clears suspension_start_date.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to resume.

        Returns:
            Dictionary with success status, message, and updated line if applicable.

        Raises:
            ValueError: If customer or line not found, or if line is not suspended or pending activation.
        """
        target_line = self._get_target_line(customer_id, line_id)

        if target_line.status not in [
            LineStatus.SUSPENDED,
            LineStatus.PENDING_ACTIVATION,
        ]:
            raise ValueError("Line must be suspended to resume")

        target_line.status = LineStatus.ACTIVE
        target_line.suspension_start_date = None

        # Log action
        logger.info(f"Line {line_id} resumed")

        return {
            "message": "Line resumed successfully",
            "line": target_line,
        }

    # Billing and Payments
    @is_tool(ToolType.READ)
    def get_bills_for_customer(self, customer_id: str, limit: int = 12) -> List[Bill]:
        """
        Retrieves a list of the customer's bills, most recent first.

        Args:
            customer_id: ID of the customer.
            limit: Maximum number of bills to return.

        Returns:
            List of Bill objects, ordered by issue date (newest first).

        Raises:
            ValueError: If the customer is not found.
        """
        customer = self.get_customer_by_id(customer_id)
        # customer object is guaranteed to be found here, or an error would have been raised.

        bills = [self._get_bill_by_id(bill_id) for bill_id in customer.bill_ids]

        # Sort bills by issue date descending
        sorted_bills = sorted(bills, key=lambda bill: bill.issue_date, reverse=True)

        # Apply limit
        return sorted_bills[:limit]

    @is_tool(ToolType.WRITE)
    def send_payment_request(self, customer_id: str, bill_id: str) -> str:
        """
        Sends a payment request to the customer for a specific bill.
        Checks:
            - Customer exists
            - Bill exists and belongs to the customer
            - No other bills are already awaiting payment for this customer
        Logic: Sets bill status to AWAITING_PAYMENT and notifies customer.
        Warning: This method does not check if the bill is already PAID.
        Always check the bill status before calling this method.

        Args:
            customer_id: ID of the customer who owns the bill.
            bill_id: ID of the bill to send payment request for.

        Returns:
            Message indicating the payment request has been sent.

        Raises:
            ValueError: If customer not found, bill not found, or if another bill is already awaiting payment.
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        bills = self._get_bills_awaiting_payment(customer)
        if len(bills) != 0:
            raise ValueError("A bill is already awaiting payment for this customer")
        if bill_id not in customer.bill_ids:
            raise ValueError(f"Bill {bill_id} not found for customer {customer_id}")
        bill = self._get_bill_by_id(bill_id)
        bill.status = BillStatus.AWAITING_PAYMENT
        return f"Payment request sent to the customer for bill {bill.bill_id}"

    def _get_bills_awaiting_payment(self, customer: Customer) -> List[Bill]:
        """
        Returns the bills in the customer's bill_ids list that are in the AWAITING_PAYMENT status.
        """
        bills = []
        for bill_id in customer.bill_ids:
            bill = self._get_bill_by_id(bill_id)
            if bill and bill.status == BillStatus.AWAITING_PAYMENT:
                bills.append(bill)
        return bills

    def _set_bill_to_paid(self, bill_id: str) -> None:
        """
        Sets the bill to paid.
        """
        bill = self._get_bill_by_id(bill_id)
        bill.status = BillStatus.PAID
        return f"Bill {bill_id} set to paid"

    def _apply_one_time_charge(
        self, customer_id: str, amount: float, description: str
    ) -> None:
        """
        Internal function to add a specific charge LineItem to the customer's next bill.
        Creates a pending bill if none exists.

        Args:
            customer_id: ID of the customer.
            amount: Amount to charge (positive) or credit (negative).
            description: Description of the charge.

        Returns:
            Success status.

        Raises:
            ValueError: If customer is not found (propagated from get_customer_by_id).
        """
        customer = self.get_customer_by_id(customer_id)
        # No need to check `if not customer`, get_customer_by_id raises if not found.

        # Find or create a draft bill
        draft_bill = None
        for bill_id in customer.bill_ids:
            bill = self._get_bill_by_id(bill_id)
            if bill and bill.status == BillStatus.DRAFT:
                draft_bill = bill
                break

        if not draft_bill:
            # Create a new draft bill for next cycle
            today = get_today()
            next_month = today.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)  # First day of next month

            new_bill_id = f"B{uuid.uuid4().hex[:8]}"  # Simple ID generation
            draft_bill = Bill(
                bill_id=new_bill_id,
                customer_id=customer_id,
                period_start=next_month,
                period_end=next_month.replace(
                    month=next_month.month + 1 if next_month.month < 12 else 1,
                    year=(
                        next_month.year
                        if next_month.month < 12
                        else next_month.year + 1
                    ),
                )
                - timedelta(days=1),
                issue_date=next_month,
                total_due=0,
                due_date=next_month + timedelta(days=14),  # 14 days after issue
                status=BillStatus.DRAFT,
            )
            self.db.bills.append(draft_bill)
            customer.bill_ids.append(new_bill_id)

        # Add line item
        line_item = LineItem(
            description=description,
            amount=amount,
            date=get_today(),
            item_type="Credit" if amount < 0 else "Charge",
        )
        draft_bill.line_items.append(line_item)

        # Update total
        draft_bill.total_due += amount

    # Usage and Contract Info
    @is_tool(ToolType.READ)
    def get_data_usage(self, customer_id: str, line_id: str) -> Dict[str, Any]:
        """
        Retrieves current billing cycle data usage for a line, including data
        refueling amount, data limit, and cycle end date.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to check usage for.

        Returns:
            Dictionary with usage information.

        Raises:
            ValueError: If customer, line, or plan not found.
        """
        target_line = self._get_target_line(customer_id, line_id)
        plan = self._get_plan_by_id(target_line.plan_id)

        today = get_today()
        cycle_end_date = date(
            today.year, today.month + 1 if today.month < 12 else 1, 1
        ) - timedelta(days=1)

        return {
            "line_id": line_id,
            "data_used_gb": target_line.data_used_gb,
            "data_limit_gb": plan.data_limit_gb,
            "data_refueling_gb": target_line.data_refueling_gb,
            "cycle_end_date": cycle_end_date,
        }

    def set_data_usage(
        self, customer_id: str, line_id: str, data_used_gb: float
    ) -> str:
        """
        Sets the data usage for a line.
        Note: This method is not decorated as a tool but follows similar error handling.

        Args:
            customer_id: ID of the customer.
            line_id: ID of the line.
            data_used_gb: Amount of data used in GB.

        Returns:
            Message indicating the data usage has been set.

        Raises:
            ValueError: If customer or line not found.
        """
        target_line = self._get_target_line(customer_id, line_id)

        target_line.data_used_gb = data_used_gb
        return f"Data usage set to {data_used_gb} GB for line {line_id}"

    @is_tool(ToolType.WRITE)
    def enable_roaming(self, customer_id: str, line_id: str) -> Dict[str, Any]:
        """
        Enables international roaming on a line.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to enable roaming for.

        Returns:
            Message indicating the roaming has been enabled.

        Raises:
            ValueError: If customer or line not found.
        """
        target_line = self._get_target_line(customer_id, line_id)

        if target_line.roaming_enabled:
            return "Roaming was already enabled"

        target_line.roaming_enabled = True

        logger.info(f"Roaming enabled for line {line_id}")

        return "Roaming enabled successfully"

    @is_tool(ToolType.WRITE)
    def disable_roaming(self, customer_id: str, line_id: str) -> str:
        """
        Disables international roaming on a line.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to disable roaming for.

        Returns:
            Message indicating the roaming has been enabled.

        Raises:
            ValueError: If customer or line not found.
        """
        target_line = self._get_target_line(customer_id, line_id)

        if not target_line.roaming_enabled:
            return "Roaming was already disabled"

        target_line.roaming_enabled = False

        logger.info(f"Roaming disabled for line {line_id}")

        return "Roaming disabled successfully"

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> str:
        """
        Transfer the user to a human agent, with a summary of the user's issue.
        Only transfer if
         -  the user explicitly asks for a human agent
         -  given the policy and the available tools, you cannot solve the user's issue.

        Args:
            summary: A summary of the user's issue.

        Returns:
            A message indicating the user has been transferred to a human agent.
        """
        return "Transfer successful"

    @is_tool(ToolType.WRITE)
    def refuel_data(
        self, customer_id: str, line_id: str, gb_amount: float
    ) -> Dict[str, Any]:
        """
        Refuels data for a specific line, adding to the customer's bill.
        Checks: Line status must be Active, Customer owns the line.
        Logic: Adds data to the line and charges customer based on the plan's refueling rate.

        Args:
            customer_id: ID of the customer who owns the line.
            line_id: ID of the line to refuel data for.
            gb_amount: Amount of data to add in gigabytes.

        Returns:
            Dictionary with success status, message, charge amount, and updated line if applicable.

        Raises:
            ValueError: If customer, line, or plan not found, or if checks fail.
        """
        target_line = self._get_target_line(customer_id, line_id)

        # if target_line.status != LineStatus.ACTIVE:
        #     raise ValueError("Line must be active to refuel data")

        if gb_amount <= 0:
            raise ValueError("Refuel amount must be positive")

        plan = self._get_plan_by_id(target_line.plan_id)
        if not plan:
            raise ValueError("Plan not found for this line")

        charge_amount = gb_amount * plan.data_refueling_price_per_gb

        target_line.data_refueling_gb += gb_amount

        self._apply_one_time_charge(
            customer_id,
            charge_amount,
            f"Data refueling: {gb_amount} GB at ${plan.data_refueling_price_per_gb}/GB",
        )

        logger.info(
            f"Data refueled for line {line_id}: {gb_amount} GB added, charge: ${charge_amount:.2f}"
        )

        return {
            "message": f"Successfully added {gb_amount} GB of data for line {line_id} for ${charge_amount:.2f}",
            "new_data_refueling_gb": target_line.data_refueling_gb,
            "charge": charge_amount,
        }

    ### Break tools
    def suspend_line_for_overdue_bill(
        self, customer_id: str, line_id: str, new_bill_id: str, contract_ended: bool
    ) -> str:
        """
        Suspends a line for an unpaid bill.
        """
        line = self._get_line_by_id(line_id)
        if line.status != LineStatus.ACTIVE:
            raise ValueError("Line must be active to suspend for unpaid bill")

        plan = self._get_plan_by_id(line.plan_id)
        amount = plan.price_per_month
        description = f"Charge for line {line.line_id}"

        if amount <= 0:
            raise ValueError("Amount must be positive for overdue bill")
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        overdue_bill_ids = []
        for bill_id in customer.bill_ids:
            bill = self._get_bill_by_id(bill_id)
            if bill.status == BillStatus.OVERDUE:
                overdue_bill_ids.append(bill_id)
        if len(overdue_bill_ids) > 0:
            raise ValueError("Customer already has an overdue bill")

        today = get_today()

        # Calculate the first day of the previous month using the same method as _apply_one_time_charge
        first_day_of_last_month = today.replace(day=1) - timedelta(days=1)
        first_day_of_last_month = first_day_of_last_month.replace(day=1)

        # Calculate the last day of the previous month
        last_day_of_last_month = today.replace(day=1) - timedelta(days=1)

        overdue_bill = Bill(
            bill_id=new_bill_id,
            customer_id=customer_id,
            period_start=first_day_of_last_month,
            period_end=last_day_of_last_month,
            issue_date=first_day_of_last_month,
            total_due=0,
            due_date=first_day_of_last_month + timedelta(days=14),
            status=BillStatus.OVERDUE,
        )
        line_item = LineItem(
            description=description,
            amount=amount,
            date=get_today(),
            item_type="Charge" if amount > 0 else "Credit",
        )
        overdue_bill.line_items.append(line_item)
        overdue_bill.total_due += amount
        self.db.bills.append(overdue_bill)
        customer.bill_ids.append(new_bill_id)
        line.status = LineStatus.SUSPENDED
        line.suspension_start_date = get_today()
        if contract_ended:
            line.contract_end_date = last_day_of_last_month
        return f"Line {line_id} suspended for unpaid bill {new_bill_id}. Contract ended: {contract_ended}"

    ### Assertions
    def assert_data_refueling_amount(
        self, customer_id: str, line_id: str, expected_amount: float
    ) -> bool:
        """
        Assert that the data refueling amount is as expected.
        """
        target_line = self._get_target_line(customer_id, line_id)
        return abs(target_line.data_refueling_gb - expected_amount) < 1e-6

    def assert_line_status(
        self, customer_id: str, line_id: str, expected_status: LineStatus
    ) -> bool:
        """
        Assert that the line status is as expected.
        """
        target_line = self._get_target_line(customer_id, line_id)
        return target_line.status == expected_status

    def assert_overdue_bill_exists(
        self, customer_id: str, overdue_bill_id: str
    ) -> bool:
        """
        Assert that the overdue bill exists.
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        if overdue_bill_id not in customer.bill_ids:
            raise ValueError(f"Overdue bill {overdue_bill_id} not found")
        bill = self._get_bill_by_id(overdue_bill_id)
        if bill.status != BillStatus.OVERDUE:
            raise ValueError(f"Overdue bill {overdue_bill_id} is not overdue")
        return True

    def assert_no_overdue_bill(self, overdue_bill_id: str) -> bool:
        """
        Assert that either:
        - the overdue bill is not in the database
        - the overdue bill is paid
        """
        try:
            bill = self._get_bill_by_id(overdue_bill_id)
            if bill.status == BillStatus.PAID:
                return True
        except ValueError:
            return True
        return False


if __name__ == "__main__":
    from tau2.domains.telecom.utils import TELECOM_DB_PATH

    telecom = TelecomTools(TelecomDB.load(TELECOM_DB_PATH))
    print(telecom.get_statistics())
