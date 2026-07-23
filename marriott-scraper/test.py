from datetime import datetime, timedelta
import pprint

import pytest
from cerberus import Validator

import marriott

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

search_schema = {
    "marriott_id": {"type": "string"},
    "name": {"type": "string"},
    "url": {"type": "string"},
    "brand": {"type": "string", "nullable": True},
    "latitude": {"type": "float", "nullable": True},
    "longitude": {"type": "float", "nullable": True},
    "lead_price": {"type": "string", "nullable": True},
}

hotel_schema = {
    "marriott_id": {"type": "string"},
    "name": {"type": "string"},
    "url": {"type": "string"},
    "address": {"type": "string", "nullable": True},
    "city": {"type": "string", "nullable": True},
    "phone": {"type": "string", "nullable": True},
    "check_in": {"type": "string", "nullable": True},
    "check_out": {"type": "string", "nullable": True},
    "parking": {"type": "list", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await marriott.scrape_search(
        city="New York, NY, USA",
        from_date=TODAY,
        to_date=WEEK_FROM_NOW,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_scraping():
    result = await marriott.scrape_hotels(["NYCMQ", "NYCMD"])
    validator = Validator(hotel_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
