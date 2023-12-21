from cerberus import Validator as _Validator
import pytest
import g2
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
g2.BASE_CONFIG["cache"] = True


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


review_schema = {
    "author": {
        "type": "dict",
        "schema": {
            "authorName": {"type": "string", "nullable": True},
            "authorProfile": {"type": "string", "nullable": True},
            "authorPosition": {"type": "string", "nullable": True},
        },
    },
    "review": {
        "type": "dict",
        "schema": {
            "reviewData": {"type": "string"},
            "reviewRate": {"type": "float"},
            "reviewTitle": {"type": "string"},
            "reviewLikes": {"type": "string"},
            "reviewDilikes": {"type": "string"},
        },
    },
}

search_schema = {
    "name": {"type": "string"},
    "link": {"type": "string"},
    "image": {"type": "string", "nullable": True},
    "rate": {"type": "float", "nullable": True},
    "reviewsNumber": {"type": "integer", "nullable": True},
}

alternatives_schema = {
    "name": {"type": "string"},
    "link": {"type": "string"},
    "ranking": {"type": "string"},
    "numberOfReviews": {"type": "integer"},
    "rate": {"type": "float"},
    "description": {"type": "string"},
}


@pytest.mark.asyncio
async def test_review_scraping():
    review_data = await g2.scrape_reviews(
        url="https://www.g2.com/products/digitalocean/reviews", max_review_pages=2
    )
    validator = Validator(review_schema, allow_unknown=True)
    for item in review_data:
        validate_or_fail(item, validator)
    for k in review_schema:
        require_min_presence(
            review_data, k, min_perc=review_schema[k].get("min_presence", 0.1)
        )
    assert len(review_data) >= 20


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await g2.scrape_search(
        url="https://www.g2.com/search?query=Infrastructure", max_scrape_pages=2
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(
            search_data, k, min_perc=search_schema[k].get("min_presence", 0.1)
        )
    assert len(search_data) >= 20


@pytest.mark.asyncio
async def test_alternative_scraping():
    alternatives_data = await g2.scrape_alternatives(product="digitalocean")
    validator = Validator(alternatives_schema, allow_unknown=True)
    for item in alternatives_data:
        validate_or_fail(item, validator)
    for k in alternatives_schema:
        require_min_presence(
            alternatives_data,
            k,
            min_perc=alternatives_schema[k].get("min_presence", 0.1),
        )
    assert len(alternatives_data) == 10
