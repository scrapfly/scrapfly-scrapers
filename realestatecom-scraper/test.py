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
    "schema": {
        "type": "dict",
        "schema": {
            "type": {"type": "string"},
            "propertyType": {"type": "string"},
            "description": {"type": "string"},
            "propertyLink": {"type": "string"},
            "address": {
                "type": "dict",
                "schema": {
                    "suburb": {"type": "string"},
                    "state": {"type": "string"},
                    "postcode": {"type": "string"},
                    "display": {
                        "type": "dict",
                        "schema": {
                            "shortAddress": {"type": "string"},
                            "fullAddress": {"type": "string"},
                            "geocode": {
                                "type": "dict",
                                "schema": {
                                    "latitude": {"type": "integer"},
                                    "longitude": {"type": "integer"},
                                },
                            },
                        },
                    },
                },
            },
            "propertySizes": {
                "type": "dict",
                "schema": {
                    "land": {
                        "type": "dict",
                        "schema": {"displayValue": {"type": "string"}},
                    },
                    "preferred": {
                        "type": "dict",
                        "schema": {"sizeType": {"type": "string"}},
                    },
                },
            },
            "generalFeatures": {
                "type": "dict",
                "schema": {
                    "bedrooms": {
                        "type": "dict",
                        "schema": {"value": {"type": "integer"}},
                    },
                    "bathrooms": {
                        "type": "dict",
                        "schema": {"value": {"type": "integer"}},
                    },
                    "parkingSpaces": {
                        "type": "dict",
                        "schema": {"value": {"type": "integer"}},
                    },
                },
            },
            "propertyFeatures": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {"featureName": {"type": "string"}},
                },
            },
            "images": {"type": "list", "schema": {"type": "string"}},
            "listingCompany": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "id": {"type": "string"},
                    "companyLink": {"type": "string"},
                    "phoneNumber": {"type": "string"},
                    "address": {"type": "string"},
                },
            },
            "listers": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "phoneNumber": {
                            "type": "dict",
                            "schema": {"display": {"type": "string"}},
                        },
                    },
                },
            },
        },
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    properties_data = await realestate.scrape_properties(
        urls=[
            "https://www.realestate.com.au/property-house-vic-tarneit-143160680",
            "https://www.realestate.com.au/property-house-vic-bundoora-141557712",
            "https://www.realestate.com.au/property-townhouse-vic-glenroy-143556608",
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1


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
