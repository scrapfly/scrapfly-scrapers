from cerberus import Validator
import allegro
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
allegro.BASE_CONFIG["cache"] = True

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


product_schema = {
    "product_title": {"type": "string"},
    "price": {"type": "string"},
    "shipping_info": {
        "type": "dict",
        "schema": {
            "shipping_price": {"type": "string"},
            "return_policy": {"type": "string"},
        },
    },
    "images": {"type": "list", "schema": {"type": "string"}},
    "rating": {"type": "string"},
    "reviews_count": {"type": "integer"},
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "author": {"type": "string"},
                "rating": {"type": "integer"},
                "content": {"type": "string"},
                "pros": {"type": "string"},
                "date": {"type": "string"},
            },
        },
    },
    "seller": {"type": "string"},
    "specifications": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    "allegro_smart_badge": {"type": "boolean"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    products_data = await allegro.scrape_product(
        urls=[
            "https://allegro.pl/oferta/procesor-amd-ryzen-5-7500f-tray-17401107639",
            "https://allegro.pl/oferta/procesor-amd-ryzen-7-9800x3d-8-x-4-7-ghz-gen-9-tray-oem-17252109693",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)

    for k in product_schema:
        require_min_presence(products_data, k, min_perc=product_schema[k].get("min_presence", 0.1))

    assert len(products_data) >= 1
