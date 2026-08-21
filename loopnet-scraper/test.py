import pytest
from cerberus import Validator
import pprint

import loopnet

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


listing_schema = {
    "id": {"type": "string", "nullable": True},
    "name": {"type": "string"},
    "url": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True},
    "address": {"type": "string", "nullable": True},
    "city": {"type": "string", "nullable": True},
    "state": {"type": "string", "nullable": True},
    "zip_code": {"type": "string", "nullable": True},
    "property_type": {"type": "string", "nullable": True},
    "property_subtype": {"type": "string", "nullable": True},
    "images": {"type": "list", "schema": {"type": "string"}},
    "video_url": {"type": "string", "nullable": True},
    "broker": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "name": {"type": "string", "nullable": True},
            "company": {"type": "string", "nullable": True},
            "phone": {"type": "string", "nullable": True},
            "profile_url": {"type": "string", "nullable": True},
        },
    },
    "details": {"type": "dict"},
}

search_schema = {
    "id": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "url": {"type": "string"},
    "address": {"type": "string", "nullable": True},
    "city": {"type": "string", "nullable": True},
    "state": {"type": "string", "nullable": True},
    "zip_code": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True},
    "property_type": {"type": "string", "nullable": True},
    "listing_type": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
    "data_points": {"type": "list", "schema": {"type": "string"}},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_listing_scraping():
    listings_data = await loopnet.scrape_listings(
        urls=[
            "https://www.loopnet.com/Listing/611-W-Oglethorpe-Ave-Savannah-GA/39001150/",
            "https://www.loopnet.com/Listing/1410-Dean-Forest-Rd-Savannah-GA/41166496/",
        ]
    )
    validator = Validator(listing_schema, allow_unknown=True)
    for item in listings_data:
        validate_or_fail(item, validator)
    assert len(listings_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_results = await loopnet.scrape_search(
        search_url="https://www.loopnet.com/search/commercial-real-estate/savannah-ga/for-sale/",
        max_pages=1,
    )
    search_data = search_results["data"]
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert search_results["total_pages"] >= 1
    assert len(search_data) >= 10
