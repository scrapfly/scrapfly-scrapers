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
    "text": {"type": "string", "minlength": 1},
    "retweet_count": {"type": "integer", "min": 0},
    "reply_count": {"type": "integer", "min": 0},
    "is_reply": {"type": "boolean"},
    "is_quote": {"type": "boolean"},
    "media": {"type": "list"},
    "user": {
        "type": "dict",
        "schema": {
            "screen_name": {"type": "string", "minlength": 1},
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
    url = "https://x.com/robinhanson/status/1872047986873885082"
    result = await twitter.scrape_tweet(url)
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
    validate_or_fail(result["tweets"][0], tweet_validator)
