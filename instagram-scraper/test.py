from cerberus import Validator
import pytest

import instagram
import pprint

pp = pprint.PrettyPrinter(indent=2)

# enable cache?
instagram.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_user_scraping():
    result = await instagram.scrape_user("google")
    schema = {
        "name": {"type": "string"},
        "username": {"type": "string"},
        "category": {"type": "string"},
        "bio": {"type": "string"},
        "followers": {"type": "integer"},
        "follows": {"type": "integer"},
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_post_scraping():
    result = await instagram.scrape_post("https://www.instagram.com/p/Csthn7EO99u/")
    schema = {
        "id": {"type": "string"},
        "shortcode": {"type": "string"},
        "src": {"type": "string"},
        "src_attached": {"type": "list", "schema": {"type": "string"}},
        "likes": {"type": "integer"},
        "taken_at": {"type": "integer"},
        "comments_count": {"type": "integer"},
        "captions": {"type": "list", "schema": {"type": "string"}},
        "comments": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "owner": {"type": "string"},
                    "created_at": {"type": "integer"},
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_user_post_scraping():
    schema = {
        "id": {"type": "string"},
        "shortcode": {"type": "string"},
        "caption": {
            "type": "dict",
            "schema": {
                "created_at": {"type": "integer"},
                "text": {"type": "string"},
                "pk": {"type": "string"}
            },
        },
        "taken_at": {"type": "integer"},
        "comment_count": {"type": "integer"},
        "like_count": {"type": "integer"}
    }

    posts_all = []
    async for post in instagram.scrape_user_posts("google", max_pages=2):
        posts_all.append(post)
    
    for post in posts_all:
        validator = Validator(schema, allow_unknown=True)
        validate_or_fail(post, validator)

    assert len(posts_all) > 12
    