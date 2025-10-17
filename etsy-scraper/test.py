import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import etsy
import pprint

pp = pprint.PrettyPrinter(indent=4)

# Disabled cache
etsy.BASE_CONFIG["cache"] = False


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
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "@type": {"type": "string"},
    "@context": {"type": "string"},
    "url": {"type": "string"},
    "name": {"type": "string"},
    "sku": {"type": "string"},
    "gtin": {"type": "string"},
    "description": {"type": "string"},
    "category": {"type": "string"},
    "logo": {"type": "string"},
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "@type": {"type": "string"},
                "datePublished": {"type": "string"},
                "reviewBody": {"type": "string"},
            }
        }
    },
    "material": {"type": "string"}
}

shop_schema = {
    "@type": {"type": "string"},
    "@context": {"type": "string"},
    "itemListElement": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "@context": {"type": "string"},
                "@type": {"type": "string"},
                "image": {"type": "string"},
                "name": {"type": "string"},
                "url": {"type": "string"},
                "brand": {
                    "type": "dict",
                    "schema": {
                        "@type": {"type": "string"},
                        "name": {"type": "string"},
                    }
                },
                "offers": {
                    "type": "dict",
                    "schema": {
                        "@type": {"type": "string"},
                        "price": {"type": "string"},
                        "priceCurrency": {"type": "string"},
                    }
                },
                "position": {"type": "integer"}
            }
        }
    }
}


search_schema = {
    "productLink": {"type": "string"},
    "productTitle": {"type": "string"},
    "productImage": {"type": "string"},
    "seller": {"type": "string", "nullable": True},
    "listingType": {"type": "string"},
    "productRate": {"type": "float", "nullable": True},
    "numberOfReviews": {"type": "integer", "nullable": True},
    "freeShipping": {"type": "string"},
    "productPrice": {"type": "float"},
    "priceCurrency": {"type": "string"},
    "discount": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    product_data = await etsy.scrape_product(
        urls = [
            "https://www.etsy.com/listing/971370843",
            "https://www.etsy.com/listing/529765307",
            "https://www.etsy.com/listing/949905096"
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in product_data:
        validate_or_fail(item, validator)
    assert len(product_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        product_data.sort(key=lambda x: x["sku"])
        (Path(__file__).parent / 'results/products.json').write_text(json.dumps(product_data, indent=2, ensure_ascii=False, default=str))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_shop_scraping():
    shop_data = await etsy.scrape_shop(
        urls = [
            "https://www.etsy.com/shop/FalkelDesign",
            "https://www.etsy.com/shop/JoshuaHouseCrafts",
            "https://www.etsy.com/shop/Oakywood"
        ]
    )
    validator = Validator(shop_schema, allow_unknown=True)
    for item in shop_data:
        validate_or_fail(item, validator)
    assert len(shop_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        shop_data.sort(key=lambda x: x["url"])
        (Path(__file__).parent / 'results/shops.json').write_text(json.dumps(shop_data, indent=2, ensure_ascii=False, default=str))

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await etsy.scrape_search(
        url="https://www.etsy.com/search?q=wood+laptop+stand", max_pages=2
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(search_data, k, min_perc=search_schema[k].get("min_presence", 0.1))        
    assert len(search_data) >= 48
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        search_data.sort(key=lambda x: x["productLink"])
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(search_data, indent=2, ensure_ascii=False, default=str))
