from cerberus import Validator
import pytest
import target
import pprint

pp = pprint.PrettyPrinter(indent=4)



def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "tcin": {"type": "string"},
    "title": {"type": "string"},
    "variants": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "tcin": {"type": "string"},
                "free_shipping": {"type": "boolean"},
                "in_stock": {"type": "boolean"},
            },
        },
    },
}

search_schema = {
    "tcin": {"type": "string"},
    "url": {"type": "string"},
    "title": {"type": "string", "nullable": True},
}

availability_schema = {
    "tcin": {"type": "string"},
    "in_stock": {"type": "boolean"},
}

store_location_schema = {
    "url": {"type": "string"},
    "slug": {"type": "string"},
    "store_id": {"type": "string"},
}

store_schema = {
    "store_id": {"type": "string"},
    "location_name": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    product_data = await target.scrape_product(
        "https://www.target.com/p/women-s-lace-godet-tank-top-wild-fable/-/A-95213693"
    )
    validator = Validator(product_schema, allow_unknown=True)
    validate_or_fail(product_data, validator)
    assert len(product_data["variants"]) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await target.scrape_search(keyword="laptop", max_pages=1)
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_availability_scraping():
    availability_data = await target.scrape_availability(
        tcins=["89231676"],
        store_id="1771",
        zip_code="52404",
    )
    validator = Validator(availability_schema, allow_unknown=True)
    for item in availability_data.values():
        validate_or_fail(item, validator)
    assert len(availability_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_store_locations_sitemap():
    store_locations_data = await target.scrape_store_locations_sitemap(
        url="https://www.target.com/sl/sitemap_0001.xml.gz",
    )
    validator = Validator(store_location_schema, allow_unknown=True)
    for item in store_locations_data[:10]:
        validate_or_fail(item, validator)
    assert len(store_locations_data) > 100


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_store_locations():
    store_data = await target.scrape_store_locations(store_ids=["3"])
    validator = Validator(store_schema, allow_unknown=True)
    for item in store_data:
        validate_or_fail(item, validator)
    assert len(store_data) == 1
