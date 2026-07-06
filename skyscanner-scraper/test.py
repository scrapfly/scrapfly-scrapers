import os
from datetime import datetime, timedelta

import pytest
from cerberus import Validator

import skyscanner

skyscanner.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"

WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

flight_result_schema = {
    "origin": {"type": "string", "regex": r"[A-Z]{3}"},
    "destination": {"type": "string", "regex": r"[A-Z]{3}"},
    "departure_date": {"type": "string", "regex": r"\d{4}-\d{2}-\d{2}"},
    "trip_type": {"type": "string", "allowed": ["one_way", "round_trip"]},
    "market_country": {"type": "string"},
    "currency": {"type": "string"},
    "carrier": {"type": "string", "nullable": True},
    "operated_by": {"type": "string", "nullable": True},
    "departure_time": {"type": "string", "nullable": True},
    "arrival_time": {"type": "string", "nullable": True},
    "duration": {"type": "string", "nullable": True},
    "stops": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True},
    "provider_deal_count": {"type": "integer", "nullable": True},
    "captured_at": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_flights_oneway():
    result = await skyscanner.scrape_flights(
        origin="JFK",
        destination="LHR",
        departure_date=WEEK_FROM_NOW,
    )
    flights = result["flights"]
    validator = Validator(flight_result_schema, allow_unknown=True)
    for flight in flights:
        assert validator.validate(flight), validator.errors
    assert len(flights) >= 5
