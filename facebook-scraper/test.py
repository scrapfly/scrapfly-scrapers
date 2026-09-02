from cerberus import Validator
import pytest
import facebook
import pprint

pp = pprint.PrettyPrinter(indent=4)

facebook.BASE_CONFIG["cache"] = False


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


page_schema = {
    "name": {"type": "string"},
    "username": {"type": "string"},
    "url": {"type": "string"},
    "page_id": {"type": "string"},
    "category": {"type": "string"},
    "intro": {"type": "string", "nullable": True},
    "likes": {"type": "integer", "nullable": True},
    "talking_about": {"type": "integer", "nullable": True},
    "were_here": {"type": "integer", "nullable": True},
    "phone": {"type": "string", "nullable": True},
    "email": {"type": "string", "nullable": True},
    "website": {"type": "string", "nullable": True},
    "address": {"type": "string", "nullable": True},
    "address_map_url": {"type": "string", "nullable": True},
    "price_range": {"type": "string", "nullable": True},
    "recommend_percent": {"type": "float", "nullable": True},
    "review_count": {"type": "integer", "nullable": True},
    "confirmed_owner": {"type": "boolean"},
    "profile_picture_url": {"type": "string", "nullable": True},
    "cover_photo_url": {"type": "string", "nullable": True},
    "social_links": {"type": "list", "nullable": True, "schema": {"type": "string"}},
}


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

group_post_schema = {
    "post_url": {"type": "string", "nullable": True},
    "group": {"type": "string"},
    "group_url": {"type": "string"},
    "posted_at": {"type": "string", "nullable": True},
    "text": {"type": "string", "nullable": True},
    "author": {"type": "string"},
    "reactions": {"type": "integer", "nullable": True},
    "comments": {"type": "integer", "nullable": True},
    "shares": {"type": "integer", "nullable": True},
    "link_title": {"type": "string", "nullable": True},
    "link_url": {"type": "string", "nullable": True},
    "media": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "mentions": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "top_comments": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {
                "author": {"type": "string", "nullable": True},
                "text": {"type": "string", "nullable": True},
            },
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
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_page_scraping():
    """Test scraping Facebook pages"""
    pages_data = await facebook.scrape_facebook_page(
        page_urls=[
            "https://www.facebook.com/bbcnews",
            "https://www.facebook.com/adidas",
            "https://www.facebook.com/copperkettleyqr",
        ]
    )
    validator = Validator(page_schema, allow_unknown=True)
    for item in pages_data:
        validate_or_fail(item, validator)
    assert len(pages_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_marketplace_scraping():
    """Test scraping Facebook Marketplace listings"""
    marketplace_data = await facebook.scrape_marketplace_listings(query="electronics")
    validator = Validator(marketplace_listing_schema, allow_unknown=True)
    for item in marketplace_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(marketplace_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_events_scraping():
    """Test scraping Facebook Events"""
    events_data = await facebook.scrape_facebook_events(event_name="New York, NY")
    validator = Validator(event_schema, allow_unknown=True)
    for item in events_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(events_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_group_posts_scraping():
    """Test scraping Facebook group posts"""
    group_data = await facebook.scrape_group_posts(
        group_urls=[
            "https://www.facebook.com/groups/instantpotcommunity",
            "https://www.facebook.com/groups/dotnetdevelopers",
            "https://www.facebook.com/groups/airfryerrecipesuk",
        ]
    )
    validator = Validator(group_post_schema, allow_unknown=True)
    for item in group_data:
        validate_or_fail(item, validator)
    assert len(group_data) >= 1
