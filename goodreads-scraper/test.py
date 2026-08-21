from cerberus import Validator
import pytest
import goodreads
import pprint

pp = pprint.PrettyPrinter(indent=2)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


BOOK_SCHEMA = {
    "url": {"type": "string"},
    "title": {"type": "string", "minlength": 1},
    "author": {
        "type": "dict",
        "schema": {
            "name": {"type": "string", "minlength": 1},
            "url": {"type": "string"},
        },
    },
    "description": {"type": "string", "nullable": True},
    "image_url": {"type": "string", "nullable": True},
    "genres": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "num_pages": {"type": "integer", "nullable": True},
    "format": {"type": "string", "nullable": True},
    "language": {"type": "string", "nullable": True},
    "isbn": {"type": "string", "nullable": True},
    "awards": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "first_published": {"type": "string", "nullable": True},
    "rating": {
        "type": "dict",
        "schema": {
            "average": {"type": "float", "nullable": True},
            "ratings_count": {"type": "integer", "nullable": True},
            "reviews_count": {"type": "integer", "nullable": True},
        },
    },
}

LIST_ITEM_SCHEMA = {
    "rank": {"type": "integer", "nullable": True},
    "title": {"type": "string", "minlength": 1},
    "url": {"type": "string"},
    "author": {"type": "string", "nullable": True},
    "author_url": {"type": "string", "nullable": True},
    "image_url": {"type": "string", "nullable": True},
    "avg_rating": {"type": "float", "nullable": True},
    "ratings_count": {"type": "integer", "nullable": True},
    "score": {"type": "integer", "nullable": True},
    "votes": {"type": "integer", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_book_scraping():
    url = "https://www.goodreads.com/book/show/4671.The_Great_Gatsby"
    result = await goodreads.scrape_book(url)
    validator = Validator(BOOK_SCHEMA, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_list_scraping():
    url = "https://www.goodreads.com/list/show/264.Books_That_Everyone_Should_Read"
    results = await goodreads.scrape_list(url, enrich=False)
    validator = Validator(LIST_ITEM_SCHEMA, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)
    assert len(results) >= 1
