"""Tests for imovelweb.com.br scraper"""
from cerberus import Validator as _Validator
import imovelweb
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


property_schema = {
    "url": {"type": "string", "required": True},
    "title": {"type": "string", "nullable": True, "min_presence": 0.1},
    "price": {"nullable": True, "min_presence": 0.1},
    "images": {"type": "list", "schema": {"type": "string"}, "required": True},
}

search_property_schema = {
    "url": {"type": "string"},
    "title": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True, "min_presence": 0.1},
    "area": {"type": "string", "nullable": True},
    "bedrooms": {"type": "string", "nullable": True},
    "bathrooms": {"type": "string", "nullable": True},
    "thumbnail": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    """Test search scraping from imovelweb.com.br"""
    search_data = await imovelweb.scrape_search(
        location="sao-paulo-sp",
        property_type="apartamentos",
        for_sale=False,
        max_pages=1,
    )
    properties_data = search_data["search_properties"]
    validator = Validator(search_property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    for k in search_property_schema:
        require_min_presence(properties_data, k, min_perc=search_property_schema[k].get("min_presence", 0.1))
    assert len(properties_data) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_property_scraping():
    """Test property detail scraping from imovelweb.com.br"""
    search_data = await imovelweb.scrape_search(
        location="sao-paulo-sp",
        property_type="apartamentos",
        for_sale=False,
        max_pages=3,
    )
    urls = [item["url"] for item in search_data["search_properties"] if item.get("url")][:3]
    property_data = await imovelweb.scrape_properties(urls=urls)
    validator = Validator(property_schema, allow_unknown=True)
    for item in property_data:
        validate_or_fail(item, validator)
    for k in property_schema:
        require_min_presence(property_data, k, min_perc=property_schema[k].get("min_presence", 0.1))
    assert len(property_data) >= 1
