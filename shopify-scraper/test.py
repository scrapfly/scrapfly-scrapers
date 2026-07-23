import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import pprint

import shopify

pp = pprint.PrettyPrinter(indent=4)

class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


product_schema = {
    "store_url": {"type": "string"},
    "source_url": {"type": "string"},
    "product_id": {"type": "string", "nullable": True},
    "handle": {"type": "string", "nullable": True},
    "title": {"type": "string", "nullable": True},
    "vendor": {"type": "string", "nullable": True},
    "product_type": {"type": "string", "nullable": True},
    "variants": {"type": "list"},
    "images": {"type": "list"},
}

sitemap_schema = {
    "url": {"type": "string"},
    "lastmod": {"type": "string", "nullable": True},
    "changefreq": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_catalog_scraping():
    catalog_data = await shopify.scrape_catalog(store_url="https://www.allbirds.com", limit=10, max_pages=2)
    validator = Validator(product_schema, allow_unknown=True)
    for item in catalog_data:
        validate_or_fail(item, validator)
    assert len(catalog_data) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    product_data = await shopify.scrape_products(
        handles=["gymshark-lift-seamless-sports-bra-sports-bras-pink-ss26-b5c9a-kdfw"],
        store_url="https://www.gymshark.com",
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in product_data:
        validate_or_fail(item, validator)
    assert len(product_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping_allbirds():
    product_data = await shopify.scrape_products(
        handles=["mens-cruiser-shadow-blue-natural-white-sole"],
        store_url="https://www.allbirds.com",
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in product_data:
        validate_or_fail(item, validator)
    assert len(product_data) >= 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_sitemap_scraping():
    sitemap_data = await shopify.scrape_sitemap(sitemap_url="https://www.gymshark.com/sitemap_pages_1.xml")
    validator = Validator(sitemap_schema, allow_unknown=True)
    for item in sitemap_data:
        validate_or_fail(item, validator)
    assert len(sitemap_data) >= 10