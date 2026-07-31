from cerberus import Validator
import pytest
import app_store
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


app_schema = {
    "appId": {"type": "string"},
    "url": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "developer": {"type": "string", "nullable": True},
    "genre": {"type": "string", "nullable": True},
    "score": {"type": "float", "nullable": True},
    "ratings": {"type": "integer", "nullable": True},
    "icon": {"type": "string", "nullable": True},
    "free": {"type": "boolean", "nullable": True},
    "price": {"type": "float", "nullable": True},
}

review_schema = {
    "reviewId": {"type": "string"},
    "userName": {"type": "string", "nullable": True},
    "content": {"type": "string", "nullable": True},
    "score": {"type": "integer", "nullable": True},
    "updated": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_app_scraping():
    metadata = await app_store.scrape_app_metadata("6448311069")
    validator = Validator(app_schema, allow_unknown=True)
    validate_or_fail(metadata, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_reviews_scraping():
    reviews = await app_store.scrape_reviews("6448311069", max_pages=1)
    validator = Validator(review_schema, allow_unknown=True)
    for item in reviews:
        validate_or_fail(item, validator)
    assert len(reviews) >= 1
