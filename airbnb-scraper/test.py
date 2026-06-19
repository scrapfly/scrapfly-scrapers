from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pprint

import pytest
from cerberus import Validator

import airbnb

pp = pprint.PrettyPrinter(indent=4)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

airbnb.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


search_schema = {
    "id": {"type": "string"},
    "url": {"type": "string", "regex": r"https://www\.airbnb\.com/rooms/\d+"},
    "title": {"type": "string", "nullable": True},
    "room_type": {"type": "string", "nullable": True},
    "rating": {"type": "float", "nullable": True},
    "review_count": {"type": "integer", "nullable": True},
    "price_total": {"type": "string", "nullable": True},
}

property_schema = {
    "url": {"type": "string"},
    "id": {"type": "string"},
    "title": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "room_type": {"type": "string", "nullable": True},
    "overview": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "amenities": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "images": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "host": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "name": {"type": "string"},
            "is_superhost": {"type": "boolean"},
        },
    },
    "coordinates": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "lat": {"type": "float"},
            "lng": {"type": "float"},
        },
    },
    "location": {"type": "string", "nullable": True},
    "person_capacity": {"type": "integer", "nullable": True},
    "rating": {"type": "float", "nullable": True},
    "review_count": {"type": "integer", "nullable": True},
    "price_per_night": {"type": "string", "nullable": True},
    "price_total": {"type": "string", "nullable": True},
    "reviews": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "reviewer": {"type": "string", "nullable": True},
                "rating": {"type": "integer", "nullable": True},
                "date": {"type": "string", "nullable": True},
                "text": {"type": "string", "nullable": True},
                "response": {"type": "string", "nullable": True},
            },
        },
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await airbnb.scrape_listings(
        query="Panama City Beach, Florida",
        check_in=TODAY,
        check_out=WEEK_FROM_NOW,
        adults=1,
        max_pages=1,
    )

    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_property_scraping():
    search_results = await airbnb.scrape_listings(
        query="Panama City Beach, Florida",
        check_in=TODAY,
        check_out=WEEK_FROM_NOW,
        adults=1,
        max_pages=1,
    )
    urls = [item["url"] for item in search_results if item.get("url")][:1]
    assert urls, "scrape_listings returned no usable URLs to feed into scrape_properties"
    result = await airbnb.scrape_properties(urls=urls)

    validator = Validator(property_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1
