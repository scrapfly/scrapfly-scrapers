from cerberus import Validator
import pytest

import stockx
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
stockx.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
async def test_product_scraping():
    result = await stockx.scrape_product("https://stockx.com/nike-x-stussy-bucket-hat-black")
    _market_schema = {
        "bidAskData": {
            "type": "dict",
            "schema": {
                "lowestAsk": {"type": "integer", "nullable": True},
                "numberOfAsks": {"type": "integer", "nullable": True},
                "highestBid": {"type": "integer", "nullable": True},
                "numberOfBids": {"type": "integer", "nullable": True},
            },
        },
        "salesInformation": {
            "type": "dict",
            "schema": {
                "lastSale": {"type": "integer"},
                "salesLast72Hours": {"type": "integer"},
            },
        },
        "statistics": {
            "type": "dict",
            "schema": {
                "lastSale": {
                    "type": "dict",
                    "schema": {
                        "amount": {"type": "integer"},
                        "changePercentage": {"type": "float"},
                        "changeValue": {"type": "integer"},
                        "sameFees": {"type": "boolean"},
                    },
                },
            },
        },
    }
    schema = {
        "id": {"type": "string"},
        "listingType": {"type": "string"},
        "deleted": {"type": "boolean"},
        "gender": {"type": "string"},
        "title": {"type": "string"},
        "brand": {"type": "string"},
        "description": {"type": "string"},
        "model": {"type": "string"},
        "variants": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "id": {"type": "string"},
                    "market": {"type": "dict", "schema": _market_schema},
                },
            },
        },
        "market": {
            "type": "dict",
            "schema": _market_schema,
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)



@pytest.mark.asyncio
async def test_search_scraping():
    result = await stockx.scrape_search("https://stockx.com/search/sneakers/top-selling?s=indigo", max_pages=2)
    schema = {
       "id": {"type": "string"},
       "name": {"type": "string"},
       "urlKey": {"type": "string"},
       "title": {"type": "string"},
       "brand": {"type": "string"},
       "description": {"type": "string"},
       "model": {"type": "string"},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
