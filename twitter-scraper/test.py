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
async def test_tweet_scraping():
    url = "https://twitter.com/robinhanson/status/1621310291030974465"
    result = await twitter.scrape_tweet(url)
    schema = {
        "tweet": {"type": "dict", "schema": TWEET_SCHEMA},
        "replies": {"type": "list", "schema": {"type": "dict", "schema": TWEET_SCHEMA}},
        "other": {"type": "list", "schema": {"type": "dict", "schema": TWEET_SCHEMA}},
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
async def test_user_scraping():
    url = "https://twitter.com/scrapfly_dev"
    result = await twitter.scrape_profile(url)
    assert len(result['tweets']) > 10
    tweet_validator = Validator(TWEET_SCHEMA, allow_unknown=True)
    for tweet in result['tweets']:
        validate_or_fail(tweet, tweet_validator)
    user_validator = Validator(USER_SCHEMA, allow_unknown=True)
    validate_or_fail(result['users']['Scrapfly_dev'], user_validator)


@pytest.mark.asyncio
async def test_topic_scraping():
    url = "https://twitter.com/i/topics/853980498816679937"
    result = await twitter.scrape_topic(url)
    assert len(result) > 10
    tweet_validator = Validator(TWEET_SCHEMA, allow_unknown=True)
    for tweet in result:
        validate_or_fail(tweet, tweet_validator)
