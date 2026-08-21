from cerberus import Validator
import pytest
import shopify
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


variant_schema = {
    "variant_id": {"type": "string"},
    "title": {"type": "string", "nullable": True},
    "sku": {"type": "string", "nullable": True},
    "options": {"type": "list", "schema": {"type": "string"}},
    "price": {"type": "float", "nullable": True},
    "compare_at_price": {"type": "float", "nullable": True},
    "available": {"type": "boolean", "nullable": True},
}

product_schema = {
    "product_id": {"type": "string"},
    "handle": {"type": "string"},
    "url": {"type": "string"},
    "title": {"type": "string", "nullable": True},
    "vendor": {"type": "string", "nullable": True},
    "product_type": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "tags": {"type": "list", "schema": {"type": "string"}},
    "options": {"type": "dict"},
    "images": {"type": "list", "schema": {"type": "string"}},
    "variants": {"type": "list", "schema": {"type": "dict", "schema": variant_schema}},
    "price_min": {"type": "float", "nullable": True},
    "price_max": {"type": "float", "nullable": True},
    "published_at": {"type": "string", "nullable": True},
    "updated_at": {"type": "string", "nullable": True},
}

preflight_schema = {
    "store_url": {"type": "string"},
    "catalog_url": {"type": "string"},
    "status_code": {"type": "integer"},
    "content_type": {"type": "string", "nullable": True},
    "outcome": {
        "type": "string",
        "allowed": [
            "shopify_catalog",
            "empty_catalog",
            "rate_limited",
            "unavailable",
            "not_json",
            "unexpected_json",
        ],
    },
    "product_count": {"type": "integer", "nullable": True},
    "is_shopify_catalog": {"type": "boolean"},
}

offer_schema = {
    "sku": {"type": "string", "nullable": True},
    "title": {"type": "string", "nullable": True},
    "price": {"type": "float", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "url": {"type": "string", "nullable": True},
}

product_page_schema = {
    "url": {"type": "string"},
    "schema_type": {"type": "string", "allowed": ["Product", "ProductGroup"]},
    "product_id": {"type": "string", "nullable": True},
    "name": {"type": "string", "nullable": True},
    "brand": {"type": "string", "nullable": True},
    "sku": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "images": {"type": "list", "schema": {"type": "string"}},
    "price": {"type": "float", "nullable": True},
    "currency": {"type": "string", "nullable": True},
    "availability": {"type": "string", "nullable": True},
    "offers": {"type": "list", "schema": {"type": "dict", "schema": offer_schema}},
    "variant_urls": {"type": "list", "schema": {"type": "string"}},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_preflight_scraping():
    preflight_data = await shopify.check_shopify_stores(
        store_urls=["https://www.allbirds.com", "https://www.apple.com"]
    )
    validator = Validator(preflight_schema, allow_unknown=True)
    for item in preflight_data:
        validate_or_fail(item, validator)
    assert len(preflight_data) == 2
    by_store = {item["store_url"]: item for item in preflight_data}
    # a Shopify storefront serves catalog JSON, a non Shopify host must not be reported as one
    assert by_store["https://www.allbirds.com"]["is_shopify_catalog"] is True
    assert by_store["https://www.apple.com"]["is_shopify_catalog"] is False


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_catalog_scraping():
    catalog_data = await shopify.scrape_catalog(store_url="https://www.allbirds.com", max_pages=2, limit=20)
    validator = Validator(product_schema, allow_unknown=True)
    for item in catalog_data:
        validate_or_fail(item, validator)
    assert len(catalog_data) >= 30  # two paginated pages of 20, minus any duplicate ids
    assert len({item["product_id"] for item in catalog_data}) == len(catalog_data)
    assert any(item["variants"] for item in catalog_data)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_collection_scraping():
    collection_data = await shopify.scrape_collection(
        store_url="https://www.deathwishcoffee.com", collection="coffee", max_pages=1, limit=20
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in collection_data:
        validate_or_fail(item, validator)
    assert len(collection_data) >= 5


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_page_scraping():
    product_page_data = await shopify.scrape_product_pages(
        urls=[
            "https://www.allbirds.com/products/mens-strider-medium-grey",
            "https://www.deathwishcoffee.com/products/vanilla-10oz",
        ]
    )
    validator = Validator(product_page_schema, allow_unknown=True)
    for item in product_page_data:
        validate_or_fail(item, validator)
    assert len(product_page_data) >= 1
    assert any(item["offers"] for item in product_page_data)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_urls_scraping():
    product_urls = await shopify.scrape_product_urls(store_url="https://www.allbirds.com")
    assert len(product_urls) >= 20
    assert all(url.startswith("https://") and "/products/" in url for url in product_urls)
