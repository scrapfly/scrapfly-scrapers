from cerberus import Validator as _Validator
import pytest
import bestbuy
import pprint

pp = pprint.PrettyPrinter(indent=4)

bestbuy.BASE_CONFIG["cache"] = False

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
    "pricing": {
        "type": "dict",
        "schema": {
            "skuId": {"type": "string"},
        }
    },
    "faqs": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "sku": {"type": "string"},
                "questionTitle": {"type": "string"}
            }
        }
    }
}

review_schema = {
    "id": {"type": "string"},
    "topicType": {"type": "string"},
    "rating": {"type": "integer"},
    "title": {"type": "string"},
    "text": {"type": "string"},
    "author": {"type": "string", "nullable": True},
}

search_schema = {
    "name": {"type": "string"},
    "link": {"type": "string"},
    "image": {"type": "string"},
    "sku": {"type": "string"},
    "model": {"type": "string"},
    "price": {"type": "integer"},
    "original_price": {"type": "integer", "nullable": True},
    "save": {"type": "string", "nullable": True},
    "rating": {"type": "float", "nullable": True},
    "rating_count": {"type": "integer", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    product_data = await bestbuy.scrape_products(
        urls=[
            "https://www.bestbuy.com/site/macbook-air-13-6-laptop-apple-m2-chip-8gb-memory-256gb-ssd-midnight/6509650.p"
            "https://www.bestbuy.com/site/apple-geek-squad-certified-refurbished-macbook-pro-16-display-intel-core-i7-16gb-memory-amd-radeon-pro-5300m-512gb-ssd-space-gray/6489615.p",
            "https://www.bestbuy.com/site/apple-macbook-air-15-laptop-m2-chip-8gb-memory-256gb-ssd-midnight/6534606.p",
            "https://www.bestbuy.com/site/apple-macbook-pro-14-laptop-m3-pro-chip-18gb-memory-14-core-gpu-512gb-ssd-latest-model-space-black/6534615.p"
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in product_data:
        validate_or_fail(item, validator)
    assert len(product_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_sitemap_scraping():
    sitemap_data = await bestbuy.scrape_sitemaps(
        url="https://sitemaps.bestbuy.com/sitemaps_promos.0000.xml.gz"
    )
    assert len(sitemap_data) > 100


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


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await bestbuy.scrape_search(
        search_query="macbook",
        max_pages=3        
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    for k in search_schema:
        require_min_presence(search_data, k, min_perc=search_schema[k].get("min_presence", 0.1))    
