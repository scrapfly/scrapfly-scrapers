import os
from datetime import datetime, timedelta

import pytest
from cerberus import Validator

import emirates

emirates.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

fare_price_schema = {
    "type": "dict",
    "schema": {
        "amount": {"type": "float"},
        "currency": {"type": "string"},
    },
}

flight_result_schema = {
    "airline": {"type": "string"},
    "flight_number": {"type": "string"},
    "departure_time": {"type": "string"},
    "departure_airport": {"type": "string", "regex": r"[A-Z]{3}"},
    "arrival_time": {"type": "string"},
    "arrival_airport": {"type": "string", "regex": r"[A-Z]{3}"},
    "duration": {"type": "string"},
    "stops": {"type": "integer"},
    "layovers": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "airport": {"type": "string"},
                "duration": {"type": "string", "nullable": True},
            },
        },
    },
    "price": fare_price_schema,
    "cabin_class": {"type": "string"},
    "plane_model": {"type": "string"},
    "fare_brand": {"type": "string"},
    "seats_available": {"type": "integer"},
}


@pytest.mark.asyncio
async def test_scrape_flights():
    result = await emirates.scrape_flights(
        origin="JFK",
        destination="DXB",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
    )
    flights = result["flights"]
    validator = Validator(flight_result_schema, allow_unknown=True)
    for flight in flights:
        assert validator.validate(flight), validator.errors
    assert len(flights) >= 1
