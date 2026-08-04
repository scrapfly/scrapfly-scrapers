from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pprint

import pytest
from cerberus import Validator as _Validator

import airbnb

pp = pprint.PrettyPrinter(indent=4)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

airbnb.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


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
    "price_total": {"type": "string", "nullable": True, "min_presence": 0.1},
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
        "min_presence": 0.1,
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
    "price_per_night": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price_total": {"type": "string", "nullable": True, "min_presence": 0.1},
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
        max_pages=3,
    )

    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(result, k, min_perc=search_schema[k].get("min_presence", 0.1))
    assert len(result) >= 40


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
    urls = [item["url"] for item in search_results if item.get("url")][:4]
    assert urls, "scrape_listings returned no usable URLs to feed into scrape_properties"
    result = await airbnb.scrape_properties(urls=urls, check_in=TODAY, check_out=WEEK_FROM_NOW)

    validator = Validator(property_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    for k in property_schema:
        require_min_presence(result, k, min_perc=property_schema[k].get("min_presence", 0.1))
    assert len(result) >= 2
