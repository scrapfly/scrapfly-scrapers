from cerberus import Validator
import pytest
import imdb
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


title_schema = {
    "id": {"type": "string"},
    "url": {"type": "string"},
    "name": {"type": "string"},
    "type": {"type": "string", "nullable": True},
    "rating_value": {"type": "float", "nullable": True},
    "rating_count": {"type": "integer", "nullable": True},
    "description": {"type": "string", "nullable": True},
}

review_schema = {
    "id": {"type": "string"},
    "author": {"type": "string", "nullable": True},
    "summary": {"type": "string", "nullable": True},
    "text": {"type": "string", "nullable": True},
    "rating": {"type": "integer", "nullable": True},
    "spoiler": {"type": "boolean"},
}

search_schema = {
    "id": {"type": "string"},
    "url": {"type": "string"},
    "name": {"type": "string", "nullable": True},
    "type": {"type": "string", "nullable": True},
    "year": {"type": "integer", "nullable": True},
    "rating_value": {"type": "float", "nullable": True},
    "rating_count": {"type": "integer", "nullable": True},
}

chart_schema = {
    "rank": {"type": "integer", "nullable": True},
    "id": {"type": "string"},
    "url": {"type": "string"},
    "name": {"type": "string", "nullable": True},
    "type": {"type": "string", "nullable": True},
    "rating_value": {"type": "float", "nullable": True},
    "rating_count": {"type": "integer", "nullable": True},
    "year": {"type": "integer", "nullable": True},
}

person_schema = {
    "id": {"type": "string", "nullable": True},
    "url": {"type": "string"},
    "name": {"type": "string", "nullable": True},
    "bio": {"type": "string", "nullable": True},
    "birth_date": {"type": "string", "nullable": True},
    "professions": {"type": "list", "nullable": True, "schema": {"type": "string"}},
    "filmography": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "name": {"type": "string", "nullable": True},
                "type": {"type": "string", "nullable": True},
                "category": {"type": "string", "nullable": True},
            },
        },
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_title_scraping():
    data = await imdb.scrape_titles(urls=["https://www.imdb.com/title/tt0111161/"])
    validator = Validator(title_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    data = await imdb.scrape_reviews(title_id="tt0111161")
    validator = Validator(review_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    data = await imdb.scrape_search(query="shawshank")
    validator = Validator(search_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_chart_scraping():
    data = await imdb.scrape_chart(chart_type="top")
    validator = Validator(chart_schema, allow_unknown=True)
    for item in data:
        validate_or_fail(item, validator)
    assert len(data) >= 50


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_person_scraping():
    data = await imdb.scrape_person(person_id="nm0000209")
    validator = Validator(person_schema, allow_unknown=True)
    validate_or_fail(data, validator)