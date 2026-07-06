from datetime import datetime, timedelta

import pytest
from cerberus import Validator
import kayak

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

def _validate_flights(flights):
    validator = Validator(flight_schema, allow_unknown=True)
    for flight in flights:
        assert validator.validate(flight), validator.errors

flight_schema = {
    "origin": {"type": "string", "regex": r"[A-Z]{3}"},
    "destination": {"type": "string", "regex": r"[A-Z]{3}"},
    "departure_date": {"type": "string", "regex": r"\d{4}-\d{2}-\d{2}"},
    "trip_type": {"type": "string", "allowed": ["one_way", "round_trip"]},
    "currency": {"type": "string", "nullable": True},
    "carrier": {"type": "string", "nullable": True},
    "departure_time": {"type": "string", "nullable": True},
    "arrival_time": {"type": "string", "nullable": True},
    "duration": {"type": "string", "nullable": True},
    "stops": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True, "regex": r"\$\d+"},
    "provider_deal_count": {"type": "integer", "min": 0},
    "captured_at": {"type": "string"},
}

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_roundtrip():
    flights = await kayak.scrape_flights(
        origin="JFK",
        destination="LAX",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
        max_pages=2,
    )
    _validate_flights(flights)
    assert len(flights) >= 5
