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
