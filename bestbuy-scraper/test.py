import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import bestbuy
import pprint

pp = pprint.PrettyPrinter(indent=4)

bestbuy.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"

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


review_schema = {
    "id": {"type": "string"},
    "topicType": {"type": "string"},
    "rating": {"type": "integer"},
    "title": {"type": "string"},
    "text": {"type": "string"},
    "author": {"type": "string", "nullable": True},
}

product_schema = {
    "product-info": {
        "type": "dict",
        "schema": {
            "brand": {"type": "string"},
            "skuId": {"type": "string"},
            "whatItIs": {
                "type": "list",
                "schema": {"type": "string"}
            }
        }
    },
    "product-features": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "description": {"type": "string"},
                "sequence": {"type": "integer"}
            }
        }
    },
    "buying-options": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "__typename": {"type": "string"},
                "description": {"type": "string"},
                "product": {
                    "type": "dict",
                    "schema": {
                        "brand": {"type": "string"},
                        "skuId": {"type": "string"},
                        "price": {
                            "type": "dict",
                            "schema": {
                                # Changed from integer to number to allow floats
                                "customerPrice": {"type": "number"},
                                "skuId": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    },
    "product-faq": {
        "type": "dict",
        "schema": {
            "results": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "userNickname": {"type": "string", "nullable": True},
                    }
                }
            }
        }
    },
    "product_reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": review_schema
        }
    }
}

search_schema = {
    "name": {"type": "string", "nullable": True},
    "link": {"type": "string", "nullable": True},
    "images": {"type": "list", "schema": {"type": "string"}},
    "sku": {"type": "string"},
    "price": {"type": "string", "regex": r"\d+\.\d{2}"},
    "original_price": {"type": "string", "regex": r"\d+\.\d{2}", "nullable": True},
    "rating": {"type": "string", "nullable": True, "regex": r"\d+\.*\d*"},
    "rating_count": {"type": "integer", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    product_data = await bestbuy.scrape_products(
        urls=[
            "https://www.bestbuy.com/site/apple-macbook-air-13-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/6565862.p",
            "https://www.bestbuy.com/site/apple-geek-squad-certified-refurbished-macbook-pro-16-display-intel-core-i7-16gb-memory-amd-radeon-pro-5300m-512gb-ssd-space-gray/6489615.p",
            "https://www.bestbuy.com/site/apple-macbook-pro-14-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-512gb-ssd-space-black/6602741.p",
            "https://www.bestbuy.com/product/apple-macbook-air-13-inch-laptop-apple-m2-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/JJGCQ8WQR5/sku/6602763",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in product_data:
        validate_or_fail(item, validator)
    assert len(product_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/products.json').write_text(json.dumps(product_data, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_sitemap_scraping():
    sitemap_data = await bestbuy.scrape_sitemaps(
        url="https://sitemaps.bestbuy.com/sitemaps_promos.0000.xml.gz"
    )
    assert len(sitemap_data) > 100
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/promos.json').write_text(json.dumps(sitemap_data, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
async def test_review_scraping():
    review_data = await bestbuy.scrape_reviews(
        skuid="6565065",
        max_pages=3
    )
    validator = Validator(review_schema, allow_unknown=True)
    for item in review_data:
        validate_or_fail(item, validator)
    assert len(review_data) >= 40
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/reviews.json').write_text(json.dumps(review_data, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await bestbuy.scrape_search(
        search_query="macbook",
        max_pages=3        
    )
    assert len(search_data) >= 10
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(search_data, k, min_perc=search_schema[k].get("min_presence", 0.1))    
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(search_data, indent=2, ensure_ascii=False))
