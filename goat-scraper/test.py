from cerberus import Validator
import goat
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
goat.BASE_CONFIG["cache"] = True


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
    "brandName": {"type": "string"},
    "color": {"type": "string"},
    "designer": {"type": "string"},
    "details": {"type": "string"},
    "forAuction": {"type": "boolean", "nullable": True},
    "id": {"type": "integer"},
    "internalShot": {"type": "string"},
    "maximumOfferCents": {"type": "integer"},
    "midsole": {"type": "string"},
    "minimumOfferCents": {"type": "integer"},
    "name": {"type": "string"},
    "productCategory": {"type": "string"},
    "productType": {"type": "string"},
    "silhouette": {"type": "string"},
    "sizeBrand": {"type": "string"},
    "sizeRange": {"type": "list", "schema": {"type": "float"}},
    "sizeBrand": {"type": "string"},
    "sku": {"type": "string"},
    "slug": {"type": "string"},
    "specialDisplayPriceCents": {"type": "integer"},
    "specialType": {"type": "string"},
    "status": {"type": "string"},
    "upperMaterial": {"type": "string"},
}

search_schema = {
    "id": {"type": "string"},
    "sku": {"type": "string"},
    "slug": {"type": "string"},
    "color": {"type": "string"},
    "category": {"type": "string"},
    "image_url": {"type": "string"},
    "product_type": {"type": "string"},
    "release_date": {"type": "integer"},
    "release_date_year": {"type": "integer"},
    "retail_price_cents": {"type": "integer"},
    "variation_id": {"type": "string"},
    "box_condition": {"type": "string"},
    "product_condition": {"type": "string"},
}


@pytest.mark.asyncio
async def test_product_scraping():
    products_data = await goat.scrape_products(
        urls=[
            "https://www.goat.com/sneakers/air-jordan-3-retro-white-cement-reimagined-dn3707-100",
            "https://www.goat.com/sneakers/travis-scott-x-air-jordan-1-retro-high-og-cd4487-100",
            "https://www.goat.com/sneakers/travis-scott-x-wmns-air-jordan-1-low-og-olive-dz4137-106",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
    assert len(products_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await goat.scrape_search("pumar dark", max_pages=3)
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 3
