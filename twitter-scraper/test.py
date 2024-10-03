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
}

USER_SCHEMA = {
    "id": {"type": "string"},
    "rest_id": {"type": "string", "regex": r"^\d+$"},
    "verified": {"type": "boolean"},
    "fast_followers_count": {"type": "integer", "min": 0},
    "followers_count": {"type": "integer", "min": 0},
    "friends_count": {"type": "integer", "min": 0},
    "description": {"type": "string", "minlength": 50},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_tweet_scraping():
    url = "https://x.com/robinhanson/status/1621310291030974465"
    result = await twitter.scrape_tweet(url)
    validator = Validator(TWEET_SCHEMA, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_user_scraping():
    url = "https://x.com/scrapfly_dev"
    result = await twitter.scrape_profile(url)
    user_validator = Validator(USER_SCHEMA, allow_unknown=True)
    validate_or_fail(result, user_validator)

