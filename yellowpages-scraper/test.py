import asyncio
from cerberus import Validator as _Validator
import pytest
import yellowpages
import pprint


pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
yellowpages.BASE_CONFIG["cache"] = True


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


page_schema = {
    "name": {"type": "string"},
    "categories": {"type": "list", "schema": {"type": "string"}},
    "rating": {"type": "string"},
    "ratingCount": {"type": "string"},
    "phone": {"type": "string"},
    "website": {"type": "string"},
    "address": {"type": "string"},
}

search_schema = {
    "name": {"type": "string"},
    "address": {
        "type": "dict",
        "schema": {
            "addressCountry": {"type": "string"},
            "streetAddress": {"type": "string"},
            "addressLocality": {"type": "string"},
            "addressRegion": {"type": "string"},
            "postalCode": {"type": "string"},
        },
    },
    "telephone": {"type": "string"},
}


@pytest.mark.asyncio
async def test_page_scraping():
    pages_data = await yellowpages.scrape_pages(
        urls=[
            "https://www.yellowpages.com/los-angeles-ca/mip/casa-bianca-pizza-pie-13519",
            "https://www.yellowpages.com/los-angeles-ca/mip/dulan-soul-food-kitchen-531675984",
            "https://www.yellowpages.com/los-angeles-ca/mip/oyabun-seafood-555210849",
        ]
    )
    validator = Validator(page_schema, allow_unknown=True)
    for item in pages_data:
        validate_or_fail(item, validator)
    for k in page_schema:
        require_min_presence(
            pages_data, k, min_perc=page_schema[k].get("min_presence", 0.1)
        )
    assert len(pages_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await yellowpages.scrape_search(
        query="chinese restaurants", location="San Francisco, CA", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(
            search_data, k, min_perc=search_schema[k].get("min_presence", 0.1)
        )
    assert len(search_data) >= 3