from cerberus import Validator
import pytest
import google_play
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
    "installs": {"type": "string", "nullable": True},
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
    "at": {"type": "integer", "nullable": True},
}

search_schema = {
    "appId": {"type": "string"},
    "title": {"type": "string", "nullable": True},
    "developer": {"type": "string", "nullable": True},
    "score": {"type": "float", "nullable": True},
    "icon": {"type": "string", "nullable": True},
    "free": {"type": "boolean", "nullable": True},
    "price": {"type": "float", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_app_scraping():
    apps = await google_play.scrape_apps(app_ids=["com.whatsapp", "com.spotify.music"])
    validator = Validator(app_schema, allow_unknown=True)
    for item in apps:
        validate_or_fail(item, validator)
    assert len(apps) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_reviews_scraping():
    reviews = await google_play.scrape_reviews(app_id="com.whatsapp", max_reviews=50)
    validator = Validator(review_schema, allow_unknown=True)
    for item in reviews:
        validate_or_fail(item, validator)
    assert len(reviews) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    results = await google_play.scrape_search(query="spotify")
    validator = Validator(search_schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    assert len(results) >= 5
