from cerberus import Validator
import pytest
import facebook
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


marketplace_listing_schema = {
    "title": {"type": "string"},
    "price": {"type": "string"},
    "location": {"type": "string"},
    "seller": {
        "type": "dict",
        "schema": {
            "name": {"type": "string"},
        },
    },
}

event_schema = {
    "title": {"type": "string"},
    "date": {"type": "string"},
    "location": {"type": "string"},
}


@pytest.mark.asyncio
async def test_marketplace_scraping():
    """Test scraping Facebook Marketplace listings"""
    marketplace_data = await facebook.scrape_marketplace_listings(location="New York, NY")
    validator = Validator(marketplace_listing_schema, allow_unknown=True)
    for item in marketplace_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(marketplace_data) >= 1


@pytest.mark.asyncio
async def test_events_scraping():
    """Test scraping Facebook Events"""
    events_data = await facebook.scrape_facebook_events(location="New York, NY")
    validator = Validator(event_schema, allow_unknown=True)
    for item in events_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(events_data) >= 1
