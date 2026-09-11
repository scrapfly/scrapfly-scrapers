from cerberus import Validator
import pytest
import pinterest
import pprint

pp = pprint.PrettyPrinter(indent=4)
pinterest.BASE_CONFIG["debug"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


pin_schema = {
    "pin_id": {"type": "string"},
    "url": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
    "is_product": {"type": "boolean"},
}

board_schema = {
    "username": {"type": "string"},
    "board_slug": {"type": "string"},
    "board_name": {"type": "string"},
    "url": {"type": "string"},
    "pins": {"type": "list"},
}

profile_schema = {
    "username": {"type": "string"},
    "url": {"type": "string"},
    "pins": {"type": "list"},
}

pin_detail_schema = {
    **pin_schema,
    "images": {"type": "dict"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await pinterest.scrape_search(query="home office desk", max_pages=2)
    pins = result["pins"]
    assert len(pins) >= 5

    validator = Validator(pin_schema, allow_unknown=True)
    for pin in pins:
        assert validator.validate(pin), {"pin": pin, "errors": validator.errors}

    # the search API returns image-only pin stubs unless the request is ungated
    assert sum(1 for pin in pins if pin["title"] or pin["description"]) >= len(pins) * 0.6
    assert all(pin["board"] and pin["owner"] for pin in pins)

    # both pages contributed, without repeating pins
    pin_ids = [pin["pin_id"] for pin in pins]
    assert len(pin_ids) == len(set(pin_ids))
    assert len(pin_ids) > 25


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_board_scraping():
    result = await pinterest.scrape_board("https://www.pinterest.com/nasa/mars/", max_pages=2)
    validator = Validator(board_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    pin_validator = Validator(pin_schema, allow_unknown=True)
    for pin in result["pins"]:
        validate_or_fail(pin, pin_validator)
    assert len(result["pins"]) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_profile_scraping():
    result = await pinterest.scrape_profile("nasa", max_pages=2)
    validator = Validator(profile_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    pin_validator = Validator(pin_schema, allow_unknown=True)
    for pin in result["pins"]:
        validate_or_fail(pin, pin_validator)
    assert len(result["pins"]) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_pin_scraping():
    result = await pinterest.scrape_pin("https://www.pinterest.com/pin/4608941770563535744/")
    validator = Validator(pin_detail_schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_download_images():
    board = await pinterest.scrape_board("https://www.pinterest.com/nasa/mars/", max_pages=1)
    pins = board["pins"][:1]
    results = await pinterest.download_pin_images(pins)
    assert results[0]["image_base64"]
