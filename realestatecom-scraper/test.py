from cerberus import Validator
import realestate
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
realestate.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "type": {"type": "string", "nullable": True},
    "propertyType": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "propertyLink": {"type": "string", "minlength": 1},
    "address": {
        "type": "dict",
        "schema": {
            "suburb": {"type": "string", "nullable": True},
            "state": {"type": "string", "nullable": True},
            "postcode": {"type": "string", "nullable": True},
            "display": {
                "type": "dict",
                "schema": {
                    "shortAddress": {"type": "string", "nullable": True},
                    "fullAddress": {"type": "string", "nullable": True},
                    "geocode": {
                        "type": "dict",
                        "schema": {
                            "latitude": {"type": "float", "nullable": True},
                            "longitude": {"type": "float", "nullable": True},
                        },
                        "nullable": True,
                    },
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "propertySizes": {
        "type": "dict",
        "schema": {
            "land": {
                "type": "dict",
                "schema": {
                    "displayValue": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "preferred": {
                "type": "dict",
                "schema": {
                    "sizeType": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "generalFeatures": {
        "type": "dict",
        "schema": {
            "bedrooms": {
                "type": "dict",
                "schema": {
                    "value": {"type": "integer", "nullable": True},
                },
                "nullable": True,
            },
            "bathrooms": {
                "type": "dict",
                "schema": {
                    "value": {"type": "integer", "nullable": True},
                },
                "nullable": True,
            },
            "parkingSpaces": {
                "type": "dict",
                "schema": {
                    "value": {"type": "integer", "nullable": True},
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "propertyFeatures": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "featureName": {"type": "string", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
    "images": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "listingCompany": {
        "type": "dict",
        "schema": {
            "name": {"type": "string", "nullable": True},
            "id": {"type": "string", "nullable": True},
            "companyLink": {"type": "string", "nullable": True},
            "phoneNumber": {"type": "string", "nullable": True},
            "address": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "listers": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string", "nullable": True},
                "name": {"type": "string", "nullable": True},
                "phoneNumber": {
                    "type": "dict",
                    "schema": {
                        "display": {"type": "string", "nullable": True},
                    },
                    "nullable": True,
                },
            },
            "nullable": True,
        },
        "nullable": True,
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    search_data = await realestate.scrape_search(
        url="https://www.realestate.com.au/buy/in-melbourne+-+northern+region,+vic/list-1",
        max_scrape_pages=1,
    )
    urls = [item["propertyLink"] for item in search_data if item.get("propertyLink")][:5]
    assert urls, "search returned no property URLs to drive the property test"
    properties_data = await realestate.scrape_properties(urls=urls)
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 3


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await realestate.scrape_search(
        url="https://www.realestate.com.au/buy/in-melbourne+-+northern+region,+vic/list-1",
        max_scrape_pages=2,
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
