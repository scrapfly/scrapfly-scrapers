from cerberus import Validator
import idealista
import pytest
import pprint
import os
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to Spain
    "country": "ES",
}
pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "location": {"type": "string"},
            "currency": {"type": "string"},
            "price": {"type": "integer"},
            "description": {"type": "string"},
            "updated": {"type": "string"},
            "features": {
                "type": "dict",
                "schema": {
                    "Basic features": {"type": "list", "schema": {"type": "string"}},
                    "Amenities": {"type": "list", "schema": {"type": "string"}},
                    "Energy performance certificate": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                },
            },
            "images": {
                "type": "dict",
                "schema": {
                    "Living room": {"type": "list", "schema": {"type": "string"}},
                    "Kitchen": {"type": "list", "schema": {"type": "string"}},
                    "Bathroom": {"type": "list", "schema": {"type": "string"}},
                    "Bedroom": {"type": "list", "schema": {"type": "string"}},
                },
            },
            "plans": {"type": "list", "schema": {"type": "string"}},
        },
    }
}


@pytest.mark.asyncio
async def test_idealista_scraping():
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://www.idealista.com/en/venta-viviendas/marbella-malaga/con-chalets/",
            asp=True,
            country="ES",
        )
    )
    property_urls = idealista.parse_search(first_page)
    to_scrape = [
        ScrapeConfig(
            first_page.context["url"] + f"pagina-{page}.htm", asp=True, country="ES"
        )
        for page in range(2, 3)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        property_urls.extend(idealista.parse_search(response))
    search_data = await idealista.scrape_properties(urls=property_urls[:3])
    validator = Validator(property_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
    assert len(property_urls) >= 30


@pytest.mark.asyncio
async def test_provinces_scraping():
    urls_data = await idealista.scrape_provinces(
        urls=[
            "https://www.idealista.com/en/venta-viviendas/balears-illes/con-chalets/municipios"
        ]
    )
    assert len(urls_data) >= 2
