from cerberus import Validator
import pytest

import twitter
import pprint

pp = pprint.PrettyPrinter(indent=2)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


TWEET_SCHEMA = {
    "id": {"type": "string", "regex": r"^\d+$"},
    "conversation_id": {"type": "string", "regex": r"^\d+$"},
    "url": {"type": "string"},
    "text": {"type": "string", "minlength": 1},
    "lang": {"type": "string", "nullable": True},
    "created_at": {"type": "string"},
    "reply_count": {"type": "integer", "min": 0},
    "retweet_count": {"type": "integer", "min": 0},
    "favorite_count": {"type": "integer", "min": 0, "nullable": True},
    "is_edited": {"type": "boolean", "nullable": True},
    "is_reply": {"type": "boolean"},
    "in_reply_to_url": {"type": "string", "nullable": True},
    "is_quote": {"type": "boolean"},
    "quoted_tweet_url": {"type": "string", "nullable": True},
    "attached_urls": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "tagged_users": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "tagged_hashtags": {"type": "list", "schema": {"type": "string"}, "nullable": True},
    "media": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string"},
                "type": {"type": "string", "nullable": True},
                "width": {"type": "integer", "nullable": True},
                "height": {"type": "integer", "nullable": True},
            },
        },
    },
    "user": {
        "type": "dict",
        "schema": {
            "id": {"type": "string", "nullable": True},
            "name": {"type": "string"},
            "screen_name": {"type": "string", "minlength": 1},
            "url": {"type": "string"},
            "profile_image_url": {"type": "string"},
            "verified": {"type": "boolean", "nullable": True},
            "business_label": {"type": "string", "nullable": True},
        },
    },
}

PROFILE_SCHEMA = {
    "id": {"type": "string"},
    "rest_id": {"type": "string", "regex": r"^\d+$"},
    "screen_name": {"type": "string", "minlength": 1},
    "verified": {"type": "boolean"},
    "followers_count": {"type": "integer", "min": 0},
    "friends_count": {"type": "integer", "min": 0},
    "statuses_count": {"type": "integer", "min": 0},
    "description": {"type": "string", "minlength": 50},
    "tweets": {"type": "list", "minlength": 1},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_tweet_scraping():
    tweet_id = "1872047986873885082"
    result = await twitter.scrape_tweet(tweet_id)
    validator = Validator(TWEET_SCHEMA, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_user_scraping():
    url = "https://x.com/robinhanson"
    result = await twitter.scrape_profile(url)
    profile_validator = Validator(PROFILE_SCHEMA, allow_unknown=True)
    validate_or_fail(result, profile_validator)
    tweet_validator = Validator(TWEET_SCHEMA, allow_unknown=True)
    for tweet in result["tweets"]:
        validate_or_fail(tweet, tweet_validator)
