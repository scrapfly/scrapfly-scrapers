"""Tests for Mouser.com scraper"""
from cerberus import Validator as _Validator
import imovelweb
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
imovelweb.BASE_CONFIG["cache"] = True

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


# property schema checks for the property data that always found
property_schema = {
    "id": {"type": "integer", "required": True, "min_presence": 1.0},
    "type": {"type": "string", "required": True, "min_presence": 1.0},
    "link": {"type": "string", "required": True, "min_presence": 1.0},
    "price": {"type": "number", "required": True, "min_presence": 1.0},
    "images": {"type": "list", "schema": {"type": "string"}, "required": True, "min_presence": 1.0},
    "image_count": {"type": "integer", "required": True, "min_presence": 1.0},
}

@pytest.mark.asyncio
async def test_property_scraping():
    """Test property scraping"""
    property_data = await imovelweb.scrape_properties(
        urls=[
            "https://www.immoweb.be/en/classified/apartment/for-rent/wemmel/1780/21247396",
            "https://www.immoweb.be/en/classified/apartment/for-rent/strombeek-bever/1853/21246666",
            "https://www.immoweb.be/en/classified/apartment/for-rent/merchtem/1785/21225730"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in property_data:
        validate_or_fail(item, validator)
    for k in property_schema:
        require_min_presence(property_data, k, min_perc=property_schema[k].get("min_presence", 0.1))

    assert len(property_data) >= 1