from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from tau2.domains.airline.utils import AIRLINE_DB_PATH
from tau2.environment.db import DB

FlightType = Literal["round_trip", "one_way"]
CabinClass = Literal["business", "economy", "basic_economy"]
Insurance = Literal["yes", "no"]


MembershipLevel = Annotated[
    Literal["gold", "silver", "regular"], Field(description="Membership level")
]


class AirportCode(BaseModel):
    iata: str = Field(description="IATA code")
    city: str = Field(description="City name")


AirportInfo = Annotated[list[AirportCode], Field(description="Airport information")]


class Name(BaseModel):
    first_name: str = Field(description="The person's first name")
    last_name: str = Field(description="The person's last name")


class Address(BaseModel):
    address1: str = Field(description="Primary address line")
    address2: Optional[str] = Field(
        None, description="Secondary address line (optional)"
    )
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    state: str = Field(description="State or province name")
    zip: str = Field(description="Postal code")


# Payment Related Models
class Payment(BaseModel):
    payment_id: str = Field(description="Unique identifier for the payment")
    amount: int = Field(description="Payment amount in dollars")


class PaymentMethodBase(BaseModel):
    source: str = Field(description="Type of payment method")
    id: str = Field(description="Unique identifier for the payment method")


class CreditCard(PaymentMethodBase):
    source: Literal["credit_card"] = Field(
        description="Indicates this is a credit card payment method"
    )
    brand: str = Field(description="Credit card brand (e.g., visa, mastercard)")
    last_four: str = Field(description="Last four digits of the credit card")


class GiftCard(PaymentMethodBase):
    source: Literal["gift_card"] = Field(
        description="Indicates this is a gift card payment method"
    )
    amount: float = Field(description="Gift card value amount")
    id: str = Field(description="Unique identifier for the gift card")


class Certificate(PaymentMethodBase):
    source: Literal["certificate"] = Field(
        description="Indicates this is a certificate payment method"
    )
    amount: float = Field(description="Certificate value amount")


PaymentMethod = Union[CreditCard, GiftCard, Certificate]


class Passenger(BaseModel):
    first_name: str = Field(description="Passenger's first name")
    last_name: str = Field(description="Passenger's last name")
    dob: str = Field(description="Date of birth in YYYY-MM-DD format")


SeatPrices = Annotated[
    dict[CabinClass, int], Field(description="Prices for different cabin classes")
]
AvailableSeats = Annotated[
    dict[CabinClass, int],
    Field(description="Available seats for different cabin classes"),
]


class FlightDateStatusAvailable(BaseModel):
    status: Literal["available"] = Field(
        description="Indicates flight is available for booking"
    )
    available_seats: AvailableSeats = Field(description="Available seats by class")
    prices: SeatPrices = Field(description="Current prices by class")


class FlightDataStatusOnTime(BaseModel):
    status: Literal["on time"] = Field(description="Indicates flight is on time")
    estimated_departure_time_est: str = Field(
        description="Estimated departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00"
    )
    estimated_arrival_time_est: str = Field(
        description="Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00"
    )


class FlightDataStatusFlying(BaseModel):
    status: Literal["flying"] = Field(description="Indicates flight is in flight")
    actual_departure_time_est: str = Field(
        description="Actual departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00"
    )
    estimated_arrival_time_est: str = Field(
        description="Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00"
    )


class FlightDateStatusLanded(BaseModel):
    status: Literal["landed"] = Field(description="Indicates flight has landed")
    actual_departure_time_est: str = Field(
        description="Actual departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00"
    )
    actual_arrival_time_est: str = Field(
        description="Actual arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00"
    )


class FlightDateStatusCancelled(BaseModel):
    status: Literal["cancelled"] = Field(description="Indicates flight was cancelled")


class FlightDateStatusDelayed(BaseModel):
    status: Literal["delayed"] = Field(description="Indicates flight was delayed")
    estimated_departure_time_est: str = Field(
        description="Estimated departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00"
    )
    estimated_arrival_time_est: str = Field(
        description="Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00"
    )


FlightDateStatus = Union[
    FlightDateStatusAvailable,
    FlightDateStatusLanded,
    FlightDateStatusCancelled,
    FlightDateStatusDelayed,
    FlightDataStatusFlying,
    FlightDataStatusOnTime,
]


class FlightBase(BaseModel):
    flight_number: str = Field(description="Unique flight identifier")
    origin: str = Field(description="IATA code for origin airport")
    destination: str = Field(description="IATA code for destination airport")


class Flight(FlightBase):
    scheduled_departure_time_est: str = Field(
        description="Scheduled departure time in EST in the format HH:MM:SS, e.g 06:00:00"
    )
    scheduled_arrival_time_est: str = Field(
        description="Scheduled arrival time in EST in the format HH:MM:SS, e.g 07:00:00"
    )
    dates: Dict[str, FlightDateStatus] = Field(
        description="Flight status by date (YYYY-MM-DD)"
    )


class DirectFlight(FlightBase):
    status: Literal["available"] = Field(
        description="Indicates flight is available for booking"
    )
    scheduled_departure_time_est: str = Field(
        description="Scheduled departure time in EST in the format HH:MM:SS, e.g 06:00:00"
    )
    scheduled_arrival_time_est: str = Field(
        description="Scheduled arrival time in EST in the format HH:MM:SS, e.g 07:00:00"
    )
    date: Optional[str] = Field(
        description="Flight date in YYYY-MM-DD format", default=None
    )
    available_seats: AvailableSeats = Field(description="Available seats by class")
    prices: SeatPrices = Field(description="Current prices by class")


class ReservationFlight(FlightBase):
    date: str = Field(description="Flight date in YYYY-MM-DD format")
    price: int = Field(description="Flight price in dollars.")


class FlightInfo(BaseModel):
    flight_number: str = Field(description="Flight number, such as 'HAT001'.")
    date: str = Field(
        description="The date for the flight in the format 'YYYY-MM-DD', such as '2024-05-01'."
    )


class User(BaseModel):
    user_id: str = Field(description="Unique identifier for the user")
    name: Name = Field(description="User's full name")
    address: Address = Field(description="User's address information")
    email: str = Field(description="User's email address")
    dob: str = Field(
        description="User's date of birth in the format YYYY-MM-DD, e.g 1990-04-05"
    )
    payment_methods: Dict[str, PaymentMethod] = Field(
        description="User's saved payment methods"
    )
    saved_passengers: List[Passenger] = Field(
        description="User's saved passenger information"
    )
    membership: MembershipLevel = Field(description="User's membership level")
    reservations: List[str] = Field(description="List of user's reservation IDs")


# Reservation Models
class Reservation(BaseModel):
    reservation_id: str = Field(description="Unique identifier for the reservation")
    user_id: str = Field(description="ID of the user who made the reservation")
    origin: str = Field(description="IATA code for trip origin")
    destination: str = Field(description="IATA code for trip destination")
    flight_type: FlightType = Field(description="Type of trip")
    cabin: CabinClass = Field(description="Selected cabin class")
    flights: List[ReservationFlight] = Field(
        description="List of flights in the reservation"
    )
    passengers: List[Passenger] = Field(
        description="List of passengers on the reservation"
    )
    payment_history: List[Payment] = Field(
        description="History of payments for this reservation"
    )
    created_at: str = Field(
        description="Timestamp when reservation was created in the format YYYY-MM-DDTHH:MM:SS"
    )
    total_baggages: int = Field(description="Total number of bags in reservation")
    nonfree_baggages: int = Field(description="Number of paid bags in reservation")
    insurance: Insurance = Field(description="Whether travel insurance was purchased")
    status: Optional[Literal["cancelled"]] = Field(
        description="Status of the reservation", default=None
    )


class FlightDB(DB):
    """Database of all flights, users, and reservations."""

    flights: Dict[str, Flight] = Field(
        description="Dictionary of all flights indexed by flight number"
    )
    users: Dict[str, User] = Field(
        description="Dictionary of all users indexed by user ID"
    )
    reservations: Dict[str, Reservation] = Field(
        description="Dictionary of all reservations indexed by reservation ID"
    )

    def get_statistics(self) -> dict[str, Any]:
        """Get the statistics of the database."""
        num_flights = len(self.flights)
        num_flights_instances = sum(
            len(flight.dates) for flight in self.flights.values()
        )
        num_users = len(self.users)
        num_reservations = len(self.reservations)
        return {
            "num_flights": num_flights,
            "num_flights_instances": num_flights_instances,
            "num_users": num_users,
            "num_reservations": num_reservations,
        }


def get_db():
    return FlightDB.load(AIRLINE_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())
