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
    "id": {"type": "string"},
    "title": {"type": "string"},
    "price": {"type": "string"},
    "location": {"type": "string"},
    "is_sold": {"type": "boolean"},
    "is_pending": {"type": "boolean"},
    "creation_time": {"type": ["string", "integer"], "nullable": True},
    "image_url": {"type": "string", "nullable": True},
    "delivery_types": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "category_id": {"type": "string", "nullable": True},
    "seller": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "name": {"type": "string"},
            "id": {"type": "string", "nullable": True},
        },
    },
}

event_schema = {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "date": {"type": "string"},
    "location": {"type": "string"},
    "url": {"type": "string"},
    "start_timestamp": {"type": "integer", "nullable": True},
    "is_online": {"type": "boolean"},
    "event_kind": {"type": "string", "nullable": True},
    "is_past": {"type": "boolean"},
    "is_happening_now": {"type": "boolean"},
    "is_hosted_by_ticket_master": {"type": "boolean"},
    "location_details": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "name": {"type": "string", "nullable": True},
            "id": {"type": "string", "nullable": True},
        },
    },
    "cover_photo": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "url": {"type": "string", "nullable": True},
            "accessibility_caption": {"type": "string", "nullable": True},
            "id": {"type": "string", "nullable": True},
        },
    },
    "social_context": {"type": "string", "nullable": True},
    "price_range": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
async def test_marketplace_scraping():
    """Test scraping Facebook Marketplace listings"""
    marketplace_data = await facebook.scrape_marketplace_listings(query="electronics")
    validator = Validator(marketplace_listing_schema, allow_unknown=True)
    for item in marketplace_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(marketplace_data) >= 1


@pytest.mark.asyncio
async def test_events_scraping():
    """Test scraping Facebook Events"""
    events_data = await facebook.scrape_facebook_events(event_name="New York, NY")
    validator = Validator(event_schema, allow_unknown=True)
    for item in events_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(events_data) >= 1
