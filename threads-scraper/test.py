import asyncio
from cerberus import Validator as _Validator
import pytest

import threads
import pprint

pp = pprint.PrettyPrinter(indent=2)

threads.BASE_CONFIG["debug"] = True


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


THREAD_SCHEMA = {
    "id": {"type": "string", "regex": r"^\d+_\d+$"},
    "pk": {"type": "string", "regex": r"^\d+$"},
    "published_on": {"type": "integer", "min": 1672531200, "max": 1704067200},
    "code": {"type": "string"},
    "username": {"type": "string"},
    # the scontent is custom pic while https:/instagram ones are default pics
    "user_pic": {"type": "string", "regex": r"^(https://scontent.+|https://instagram.+?)"},
    "user_verified": {"type": "boolean"},
    "user_pk": {"type": "string"},
    "user_id": {"type": "string", "nullable": True, "min_presence": 0},  # this seems to be always null?
    "has_audio": {"type": "boolean", "nullable": True, "min_presence": 0},  # audio videos hard to find for now
    "reply_count": {"type": "integer", "min": 0, "max": 100_000, "nullable": True, "min_presence": 0.01},  # not many posts have replies yet
    "like_count": {"type": "integer", "min": 0, "max": 10_000_000, "nullable": True},
    "image_count": {"type": "integer", "min": 0, "max": 10, "nullable": True, "min_presence": 0.01},  # rare field for now too
}

USER_SCHEMA = {
    "is_private": {"type": "boolean"},
    "is_verified": {"type": "boolean"},
    # the scontent is custom pic while https:/instagram ones are default pics
    "profile_pic": {"type": "string", "regex": r"^(https://scontent.+|https://instagram.+?)"},
    "username": {"type": "string"},
    "full_name": {"type": "string"},
    "bio": {"type": "string"},
    "bio_links": {"type": "list", "schema": {"type": "string"}},
    "followers": {"type": "integer", "min": 0, "max": 100_000_000},
}


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key) is not None)
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


@pytest.mark.asyncio
async def test_thread_scraping():
    urls = [
        "https://www.threads.net/t/CuVdfsNtmvh/",  # example with media
        "https://www.threads.net/t/CuV1UcwLCQD",  # example without media
    ]
    results = await asyncio.gather(*[threads.scrape_thread(url) for url in urls])
    all_threads = [result["thread"] for result in results] + [
        reply for result in results for reply in result["replies"]
    ]
    assert len(all_threads) > 10
    validator = Validator(THREAD_SCHEMA, allow_unknown=True)
    for result in results:
        validate_or_fail(result["thread"], validator)
        for reply in result["replies"]:
            validate_or_fail(reply, validator)
    for key in THREAD_SCHEMA:
        require_min_presence(all_threads, key, THREAD_SCHEMA[key].get("min_presence", 0.1))


@pytest.mark.asyncio
async def test_user_scraping():
    urls = [
        "https://www.threads.net/@discoverocean",
        # "https://www.threads.net/t/CuV1UcwLCQD",  # example without media
    ]
    results = await asyncio.gather(*[threads.scrape_profile(url) for url in urls])
    # threads
    all_threads = [thread for result in results for thread in result["threads"] ]
    assert len(all_threads) > 5
    validator = Validator(THREAD_SCHEMA, allow_unknown=True)
    for thread in all_threads:
        validate_or_fail(thread, validator)
    # user
    validator = Validator(USER_SCHEMA, allow_unknown=True)
    for result in results:
        validate_or_fail(result['user'], validator)

    for key in USER_SCHEMA:
        require_min_presence([r['user'] for r in results], key, USER_SCHEMA[key].get("min_presence", 0.1))
    for key in THREAD_SCHEMA:
        require_min_presence(all_threads, key, THREAD_SCHEMA[key].get("min_presence", 0.1))
