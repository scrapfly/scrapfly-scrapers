from datetime import datetime, timedelta

import pytest
from cerberus import Validator

import expedia

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

hotel_schema = {
    "hotel_id": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "url": {"type": "string", "nullable": True},
    "nightly_price": {"type": "string", "nullable": True},
    "total_price": {"type": "string", "nullable": True},
    "star_rating": {"type": "float", "nullable": True},
    "review_score": {"type": "float", "nullable": True},
    "review_count": {"type": "integer", "nullable": True},
    "location": {"type": "string", "nullable": True},
    "market_country": {"type": "string", "nullable": True},
    "captured_at": {"type": "string"},
}

flight_schema = {
    "origin": {"type": "string"},
    "destination": {"type": "string"},
    "airline": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True},
    "departure_time": {"type": "string", "nullable": True},
    "arrival_time": {"type": "string", "nullable": True},
    "duration": {"type": "string", "nullable": True},
    "stops": {"type": "string", "nullable": True},
    "cabin_class": {"type": "string"},
    "captured_at": {"type": "string"},
}

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_hotel_search():
    hotels = await expedia.scrape_hotel_search(
        destination="New York",
        check_in=TODAY,
        check_out=WEEK_FROM_NOW,
        max_pages=1,
    )
    validator = Validator(hotel_schema, allow_unknown=True)
    for hotel in hotels:
        assert validator.validate(hotel), validator.errors
    assert len(hotels) >= 10

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_flight_search():
    flights = await expedia.scrape_flight_search(
        origin="JFK",
        destination="LAX",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
        max_pages=1,
    )
    validator = Validator(flight_schema, allow_unknown=True)
    for flight in flights:
        assert validator.validate(flight), validator.errors
    assert len(flights) >= 5
