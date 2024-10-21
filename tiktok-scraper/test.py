from cerberus import Validator
import pytest
import tiktok
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


comment_schema = {
    "text": {"type": "string"},
    "comment_language": {"type": "string"},
    "digg_count": {"type": "integer"},
    "reply_comment_total": {"type": "integer"},
    "author_pin": {"type": "boolean"},
    "create_time": {"type": "integer"},
    "cid": {"type": "string"},
    "nickname": {"type": "string"},
    "unique_id": {"type": "string"},
    "aweme_id": {"type": "string"}
}

post_schema = {
    "text": {"type": "string"},
    "desc": {"type": "string"},
    "createTime": {"type": "string"},
    "video": {
        "type": "dict",
        "schema": {
            "duration": {"type": "integer"},
            "ratio": {"type": "string"},
            "cover": {"type": "string"},
            "playAddr": {"type": "string"},
            "downloadAddr": {"type": "string"},
            "bitrate": {"type": "integer"},
        }
    },
    "author": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "uniqueId": {"type": "string"},
            "nickname": {"type": "string"},
            "avatarLarger": {"type": "string"},
            "signature": {"type": "string"},
        }
    }
}


profile_schema = {
    "user": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "id": {"type": "string"},
            "id": {"type": "string"}
        }
    },
    "stats": {
        "type": "dict",
        "schema": {
            "followerCount": {"type": "integer"},
            "followingCount": {"type": "integer"},
            "heart": {"type": "integer"},
            "heartCount": {"type": "integer"},
            "videoCount": {"type": "integer"},
            "diggCount": {"type": "integer"},
            "friendCount": {"type": "integer"},
        }
    }
}

search_schema = {
    "id": {"type": "string"},
    "desc": {"type": "string"},
    "author": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "uniqueId": {"type": "string"},
            "nickname": {"type": "string"},
            "signature": {"type": "string"},
        }
    },
    "stats": {
        "type": "dict",
        "schema": {
            "diggCount": {"type": "integer"},
            "shareCount": {"type": "integer"},
            "commentCount": {"type": "integer"},
            "playCount": {"type": "integer"},
            "collectCount": {"type": "integer"},
        }
    }
}

channel_schema = {
    "createTime": {"type": "integer"},
    "desc": {"type": "string"},
    "id": {"type": "string"},
    "stats": {
        "type": "dict",
        "schema": {
            "diggCount": {"type": "integer"},
            "shareCount": {"type": "integer"},
            "commentCount": {"type": "integer"},
            "playCount": {"type": "integer"},
            "collectCount": {"type": "integer"},
        }
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_comment_scraping():
    commnets_data = await tiktok.scrape_comments(
        post_url='https://www.tiktok.com/@oddanimalspecimens/video/7198206283571285294',
        max_comments=24,
        comments_count=20
    )    
    validator = Validator(comment_schema, allow_unknown=True)
    for item in commnets_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(commnets_data) >= 24


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_post_scraping():
    posts_data = await tiktok.scrape_posts(
        urls=[
            "https://www.tiktok.com/@oddanimalspecimens/video/7198206283571285294"
        ]
    )
    validator = Validator(post_schema, allow_unknown=True)
    for item in posts_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(posts_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_profile_scraping():
    profiles_data = await tiktok.scrape_profiles(
        urls=[
            "https://www.tiktok.com/@oddanimalspecimens"
        ]
    )    
    validator = Validator(profile_schema, allow_unknown=True)
    for item in profiles_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(profiles_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await tiktok.scrape_search(
        keyword="whales",
        max_search=20
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(search_data) >= 18


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_channel_scraping():
    channel_data = await tiktok.scrape_channel(
        url="https://www.tiktok.com/@oddanimalspecimens"        
    )
    validator = Validator(channel_schema, allow_unknown=True)
    for item in channel_data:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    assert len(channel_data) >= 5