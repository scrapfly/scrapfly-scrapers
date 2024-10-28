from cerberus import Validator as _Validator
import pytest
import google
import pprint

pp = pprint.PrettyPrinter(indent=4)


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
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


serp_schema = {
    "position": {"type": "integer"},
    "title": {"type": "string"},
    "url": {"type": "string"},
    "origin": {"type": "string"},
    "domain": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "date": {"type": "string", "nullable": True},
}

keywords_schema = {
    "related_search": {
        "type": "list",
        "schema": {"type": "string"},
    },
    "people_ask_for": {
        "type": "list",
        "schema": {"type": "string"},
    },
}

map_place_schema = {
    "name": {"type": "string"},
    "category": {"type": "string"},
    "address": {"type": "string"},
    "website": {"type": "string"},
    "phone": {"type": "string"},
    "review_count": {"type": "string"},
    "stars": {"type": "string"},
    "5_stars": {"type": "string"},
    "4_stars": {"type": "string"},
    "3_stars": {"type": "string"},
    "2_stars": {"type": "string"},
    "1_stars": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_serp_scraping():
    serp_data = await google.scrape_serp(
        query="scrapgly blog web scraping",
        max_pages=3,
    )

    validator = Validator(serp_schema)
    for item in serp_data:
        validate_or_fail(item, validator)
    for k in serp_schema:
        require_min_presence(
            serp_data, k, min_perc=serp_schema[k].get("min_presence", 0.1)
        )
    assert len(serp_data) >= 20


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_keyword_scraping():
    keyword_data = await google.scrape_keywords(
        query="web scraping emails",
    )

    validator = Validator(keywords_schema)
    validate_or_fail(keyword_data, validator)
    assert len(keyword_data["related_search"]) > 1
    assert len(keyword_data["people_ask_for"]) > 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_place_url_scraping():
    urls = await google.find_google_map_places(
        query="museum in paris",
    )
    assert len(urls) >= 3


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_place_scraping():
    urls = await google.find_google_map_places(
        query="museum in paris",
    )

    google_map_places = await google.scrape_google_map_places(urls=urls[:3])
    validator = Validator(map_place_schema)
    for item in google_map_places:
        validate_or_fail(item, validator)
    for k in map_place_schema:
        require_min_presence(
            google_map_places, k, min_perc=map_place_schema[k].get("min_presence", 0.1)
        )
    assert len(google_map_places) > 1
