from datetime import datetime, timedelta

import pytest
from cerberus import Validator

import goibibo

TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

hotel_schema = {
    "id": {"type": "string"},
    "name": {"type": "string"},
    "sold_out": {"type": "boolean"},
    "images": {"type": "list"},
    "amenities": {"type": "list"},
}


flight_schema = {
    "flight_number": {"type": "string", "nullable": True},
    "airline_name": {"type": "string", "nullable": True},
    "origin_code": {"type": "string", "nullable": True},
    "destination_code": {"type": "string", "nullable": True},
    "fare": {"type": "number", "nullable": True},
    "legs": {"type": "list"},
}


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {item}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_search_scraping():
    result = await goibibo.scrape_hotel_search(
        search_text="Delhi",
        locus_id="CTDEL",
        checkin=TOMORROW,
        checkout=WEEK_FROM_NOW,
        max_pages=2,
    )
    validator = Validator(hotel_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_flight_search_scraping():
    result = await goibibo.scrape_flight_search(
        origin="DEL",
        destination="BOM",
        departure_date=TOMORROW,
    )
    validator = Validator(flight_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 10
