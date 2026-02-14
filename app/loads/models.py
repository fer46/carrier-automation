from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Load(BaseModel):
    """Represents a freight load in the system.

    This is both the database document shape and the API response shape.
    Each load is a shipment that a carrier can search for and potentially book.
    """

    load_id: str  # Unique identifier, e.g. "LD-001"
    origin: str  # Pickup city and state, e.g. "Denver, CO"
    destination: str  # Delivery city and state, e.g. "Chicago, IL"
    pickup_datetime: datetime  # When the carrier needs to pick up the load
    delivery_datetime: datetime  # When the load must arrive at destination
    equipment_type: str  # Truck type needed: "Dry Van", "Reefer", or "Flatbed"
    loadboard_rate: float  # Our listed price in USD for hauling this load
    status: str = "available"  # Load lifecycle: "available" or "booked"
    notes: str = ""  # Special handling instructions or requirements
    weight: float  # Total weight in pounds
    commodity_type: str  # What's being shipped: "Electronics", "Food Products", etc.
    num_of_pieces: int  # Number of individual items/pallets in the shipment
    miles: float  # Distance from origin to destination in miles
    dimensions: str  # Cargo dimensions as "LxWxH" in inches
    target_carrier_rate: Optional[float] = None  # Broker target offer (12% margin)
    cap_carrier_rate: Optional[float] = None  # Max acceptable rate (5% margin)


class LoadSearchParams(BaseModel):
    """Query parameters for searching loads.

    Note: Currently unused — the router defines these as individual Query() params.
    Kept for potential future use with request body-based search.
    """

    origin: Optional[str] = None  # Filter by pickup city (partial match)
    destination: Optional[str] = None  # Filter by delivery city (partial match)
    equipment_type: Optional[str] = None  # Filter by truck type (partial match)
    min_rate: Optional[float] = Field(None, alias="min_rate")  # Minimum rate in USD
    max_rate: Optional[float] = Field(None, alias="max_rate")  # Maximum rate in USD


class LoadResponse(BaseModel):
    """Wrapper for search results returned to the client.

    Contains the list of matching loads and the total count.
    Used by the voice AI to present load options to the carrier.
    """

    loads: list[Load]  # List of loads matching the search criteria
    total: int  # Number of loads returned (len of loads list)
