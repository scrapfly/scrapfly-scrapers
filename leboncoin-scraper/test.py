from cerberus import Validator
import pytest
import leboncoin
import pprint


pp = pprint.PrettyPrinter(indent=4)

# enable cache
leboncoin.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


ad_schema = {
    "list_id": {"type": "integer"},
    "first_publication_date": {"type": "string"},
    "index_date": {"type": "string"},
    "status": {"type": "string"},
    "category_id": {"type": "string"},
    "category_name": {"type": "string"},
    "subject": {"type": "string"},
    "url": {"type": "string"},
    "price": {"type": "list", "schema": {"type": "integer"}},
    "price_cents": {"type": "integer"},
    "images": {
        "type": "dict",
        "schema": {
            "thumb_url": {"type": "string"},
            "small_url": {"type": "string"},
            "nb_images": {"type": "integer"},
            "urls": {"type": "list", "schema": {"type": "string"}},
        },
    },
    "attributes": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    "location": {
        "type": "dict",
        "schema": {
            "country_id": {"type": "string"},
            "region_id": {"type": "string"},
            "region_name": {"type": "string"},
            "department_id": {"type": "string"},
            "department_name": {"type": "string"},
            "city": {"type": "string"},
        },
    },
    "owner": {
        "type": "dict",
        "schema": {
            "store_id": {"type": "string"},
            "user_id": {"type": "string"},
            "type": {"type": "string"},
            "name": {"type": "string"},
            "no_salesmen": {"type": "boolean"},
        },
    },
    "options": {
        "type": "dict",
        "schema": {
            "has_option": {"type": "boolean"},
            "booster": {"type": "boolean"},
            "photosup": {"type": "boolean"},
            "urgent": {"type": "boolean"},
            "gallery": {"type": "boolean"},
            "sub_toplist": {"type": "boolean"},
        },
    },
    "has_phone": {"type": "boolean"},
}


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await leboncoin.scrape_search(
        url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=2, scrape_all_pages=False
    )
    validator = Validator(ad_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_ad_scraping():
    ad_data = await leboncoin.scrape_ad(url="https://www.leboncoin.fr/arts_de_la_table/2426724825.htm")
    validator = Validator(ad_schema, allow_unknown=True)
    validate_or_fail(ad_data, validator)
    