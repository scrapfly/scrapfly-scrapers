from cerberus import Validator
import vestiairecollective
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
vestiairecollective.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


product_schema = {
    "id": {"type": "string"},
    "type": {"type": "string"},
    "name": {"type": "string"},
    "price": {
        "type": "dict",
        "schema": {
            "currency": {"type": "string"},
            "cents": {"type": "integer"},
            "formatted": {"type": "string"},
        },
    },
    "description": {"type": "string"},
    "likeCount": {"type": "integer"},
    "path": {"type": "string"},
    "measurementFormatted": {"type": "string"},
    "unit": {"type": "string"},
    "metadata": {
        "type": "dict",
        "schema": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "keywords": {"type": "string"},
        },
    },
    "warehouse": {
        "schema": {
            "name": {"type": "string"},
            "localizedName": {"type": "string"},
        },
    },
    "brand": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "type": {"type": "string"},
            "name": {"type": "string"},
            "localizedName": {"type": "string"},
        },
    },
}

search_schema = {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "description": {"type": "string"},
    "country": {"type": "string"},
    "likes": {"type": "integer"},
    "link": {"type": "string"},
    "pictures": {"type": "list", "schema": {"type": "string"}},
    "price": {
        "type": "dict",
        "schema": {
            "cents": {"type": "integer"},
            "currency": {"type": "string"},
        },
    },
    "seller": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer"},
            "firstname": {"type": "string"},
            "badge": {"type": "string"},
            "picture": {"type": "string"},
            "isOfficialStore": {"type": "boolean"},
        },
    },
    "sold": {"type": "boolean"},
    "stock": {"type": "boolean"},
    "shouldBeGone": {"type": "boolean"},
    "createdAt": {"type": "integer"},
    "universeId": {"type": "integer"},
    "dutyFree": {"type": "boolean"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products_data = await vestiairecollective.scrape_products(
        urls=[
            "https://www.vestiairecollective.com/men-accessories/watches/patek-philippe/metallic-steel-nautilus-patek-philippe-watch-21827899.shtml",
            "https://www.vestiairecollective.com/men-accessories/watches/patek-philippe/brown-pink-gold-nautilus-patek-philippe-watch-46098315.shtml",
            "https://www.vestiairecollective.com/men-accessories/watches/patek-philippe/black-gold-plated-world-time-patek-philippe-watch-45943664.shtml",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
    assert len(products_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await vestiairecollective.scrape_search(
        url="https://www.vestiairecollective.com/search/?q=louis+vuitton", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 48
