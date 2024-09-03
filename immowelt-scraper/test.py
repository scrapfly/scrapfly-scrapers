from cerberus import Validator
import immowelt
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


proeprty_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "brand": {"type": "string"},
            "id": {"type": "string"},
            "title": {"type": "string"},
            "sections": {
                "type": "dict",
                "schema": {
                    "location": {
                        "type": "dict",
                        "schema": {
                            "address": {
                                "type": "dict",
                                "schema": {
                                    "country": {"type": "string"},
                                    "city": {"type": "string"},
                                    "zipCode": {"type": "string"},
                                    "street": {"type": "string"},
                                    "district": {"type": "string"},
                                }
                            }
                        }
                    },
                    "features": {
                        "type": "dict",
                        "schema": {
                            "preview": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "icon": {"type": "string"},
                                        "value": {"type": "string"},                                        
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "brand": {"type": "string"},
            "id": {"type": "string"},
            "status": {"type": "string"},
            "location": {
                "type": "dict",
                "schema": {
                    "address": {
                        "type": "dict",
                        "schema": {
                            "country": {"type": "string"},
                            "city": {"type": "string"},
                            "zipCode": {"type": "string"},
                            "street": {"type": "string"},
                            "district": {"type": "string"},
                        }
                    }
                }
            },

        },
    }
}


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await immowelt.scrape_properties(
        urls=[
            "https://www.immowelt.de/expose/27t9c5f",
            "https://www.immowelt.de/expose/27dgc5f",
            "https://www.immowelt.de/expose/9175275c-9b96-454f-a770-7f4ef0e720be",
            "https://www.immowelt.de/expose/95aba3fb-8449-47d3-8394-9ab71e705160",
            "https://www.immowelt.de/expose/ac9dc8d0-a729-4d79-849e-93ec9d4cf16a"
        ]
    )
    validator = Validator(proeprty_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await immowelt.scrape_search(
        url="https://www.immowelt.de/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08DE6345",
        max_scrape_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
