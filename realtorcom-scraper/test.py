from cerberus import Validator
import pytest

import realtorcom
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
realtorcom.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_property_scraping():
    url = "https://www.realtor.com/realestateandhomes-detail/12355-Attlee-Dr_Houston_TX_77077_M70330-35605"
    result = await realtorcom.scrape_property(url)
    schema = {
        "id": {"type": "string"},
        "href": {"type": "string", "regex": "https://www.realtor.com/realestateandhomes-detail/.+?"},
        "status": {"type": "string"},
        "sold_date": {"type": "string", "regex": "\d+-\d+-\d+", "nullable": True},
        "tags": {"type": "list", "schema": {"type": "string"}},
        "list_price": {"type": "integer"},
        "list_price_last_change": {"type": "integer"},
        "details": {
            "type": "dict",
            "schema": {
                "beds": {"type": "integer"},
                "baths": {"type": "integer"},
            },
        },
        "flags": {"type": "dict"},
        "phones": {"type": "list", "schema": {"type": "dict", "schema": {"number": {"type": "string"}}}},
        "location": {
            "type": "dict",
            "schema": {
                "address": {
                    "type": "dict",
                    "schema": {
                        "city": {"type": "string"},
                        "line": {"type": "string"},
                        "state": {"type": "string"},
                        "postal_code": {"type": "string"},
                    },
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await realtorcom.scrape_search("CA", "San-Francisco", max_pages=2)
    schema = {
        "property_id": {"type": "string"},
        "permalink": {"type": "string"},
        "list_price": {"type": "integer", "nullable": True},  # some propreties can have no price
        "list_date": {"type": "string"},
        "photos": {
            "type": "list",
            "nullable": True,
            "schema": {
                "type": "dict",
                "schema": {
                    "href": {"type": "string"}
                }
            }
        },
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_feed_scraping():
    url = "https://www.realtor.com/realestateandhomes-detail/sitemap-rss-price/rss-price-ca.xml"
    result_feed = await realtorcom.scrape_feed(url)
    assert len(result_feed) > 0
    for url, lastmod in result_feed.items():
        assert url.startswith("https://www.realtor.com/")
        assert lastmod is not None
