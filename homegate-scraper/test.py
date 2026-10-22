import json
import os
from pathlib import Path
from cerberus import Validator
import homegate
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
homegate.BASE_CONFIG["cache"] = False


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "localization": {
        "type": "dict",
        "schema": {
            "de": {
                "type": "dict",
                "schema": {
                    "text": {
                        "type": "dict",
                        "schema": {
                            "title": {"type": "string", "nullable": True},
                            "description": {"type": "string", "nullable": True},
                        },
                        "nullable": True,
                    },
                    "attachments": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "type": {"type": "string", "nullable": True},
                                "url": {"type": "string", "nullable": True},
                                "file": {"type": "string", "nullable": True},
                            },
                            "nullable": True,
                        },
                        "nullable": True,
                    },
                },
                "nullable": True,
            },
            "primary": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "lister": {
        "type": "dict",
        "schema": {
            "primary": {"type": "string", "nullable": True},
            "website": {
                "type": "dict",
                "schema": {
                    "value": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "id": {"type": "string", "nullable": True},
            "allowToContact": {"type": "boolean", "nullable": True},
        },
        "nullable": True,
    },
    "characteristics": {
        "type": "dict",
        "schema": {
            "livingSpace": {"type": "integer", "nullable": True},
            "numberOfRooms": {"type": "float", "nullable": True},
        },
        "nullable": True,
    },
    "address": {
        "type": "dict",
        "schema": {
            "country": {"type": "string", "nullable": True},
            "geoDistances": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "distance": {"type": "integer", "nullable": True},
                        "geoTag": {"type": "string", "nullable": True},
                    },
                    "nullable": True,
                },
                "nullable": True,
            },
            "geoTags": {
                "type": "list",
                "schema": {"type": "string", "nullable": True},
                "nullable": True,
            },
            "street": {"type": "string", "nullable": True},
            "postalCode": {"type": "string", "nullable": True},
            "locality": {"type": "string", "nullable": True},
            "geoCoordinates": {
                "type": "dict",
                "schema": {
                    "accuracy": {"type": "string", "nullable": True},
                    "manual": {"type": "boolean", "nullable": True},
                    "latitude": {"type": "float", "nullable": True},
                    "longitude": {"type": "float", "nullable": True},
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "externalIds": {
        "type": "dict",
        "schema": {
            "internalReferenceId": {"type": "string", "nullable": True},
            "displayReferenceId": {"type": "string", "nullable": True},
            "refObject": {"type": "string", "nullable": True},
            "displayPropertyReferenceId": {"type": "string", "nullable": True},
            "propertyReferenceId": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "contactForm": {
        "type": "dict",
        "schema": {
            "size": {"type": "string", "nullable": True},
            "deliveryFormat": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "version": {"type": "string", "nullable": True},
    "platform": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "offerType": {"type": "string", "nullable": True},
    "meta": {
        "type": "dict",
        "schema": {
            "createdAt": {"type": "string", "nullable": True},
            "updatedAt": {"type": "string", "nullable": True},
            "source": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "id": {"type": "string", "minlength": 1},
    "categories": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "prices": {
        "type": "dict",
        "schema": {
            "rent": {
                "type": "dict",
                "schema": {
                    "area": {"type": "string", "nullable": True},
                    "interval": {"type": "string", "nullable": True},
                    "net": {"type": "integer", "nullable": True},
                    "gross": {"type": "integer", "nullable": True},
                },
                "nullable": True,
            },
            "currency": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "valueAddedServices": {
        "type": "dict",
        "schema": {
            "isTenantPlusListing": {"type": "boolean", "nullable": True},
        },
        "nullable": True,
    },
}

search_schema = {
    "listingType": {
        "type": "dict",
        "schema": {
            "type": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "listing": {
        "type": "dict",
        "schema": {
            "address": {
                "type": "dict",
                "schema": {
                    "geoCoordinates": {
                        "type": "dict",
                        "schema": {
                            "accuracy": {"type": "string", "nullable": True},
                            "manual": {"type": "boolean", "nullable": True},
                            "latitude": {"type": "float", "nullable": True},
                            "longitude": {"type": "float", "nullable": True},
                        },
                        "nullable": True,
                    },
                    "locality": {"type": "string", "nullable": True},
                    "postalCode": {"type": "string", "nullable": True},
                    "street": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "categories": {
                "type": "list",
                "schema": {"type": "string", "nullable": True},
                "nullable": True,
            },
            "characteristics": {
                "type": "dict",
                "schema": {
                    "hasNiceView": {"type": "boolean", "nullable": True},
                    "hasBalcony": {"type": "boolean", "nullable": True},
                    "hasElevator": {"type": "boolean", "nullable": True},
                    "livingSpace": {"type": "integer", "nullable": True},
                    "numberOfRooms": {"type": "float", "nullable": True},
                    "floor": {"type": "integer", "nullable": True},
                    "isQuiet": {"type": "boolean", "nullable": True},
                    "yearBuilt": {"type": "integer", "nullable": True},
                    "hasGarage": {"type": "boolean", "nullable": True},
                },
                "nullable": True,
            },
            "id": {"type": "string", "nullable": True},
            "localization": {
                "type": "dict",
                "schema": {
                    "de": {
                        "schema": {
                            "text": {
                                "type": "dict",
                                "schema": {
                                    "title": {"type": "string", "nullable": True},
                                    "description": {"type": "string", "nullable": True},
                                },
                                "nullable": True,
                            },
                            "attachments": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "type": {"type": "string", "nullable": True},
                                        "url": {"type": "string", "nullable": True},
                                        "file": {"type": "string", "nullable": True},
                                    },
                                    "nullable": True,
                                },
                                "nullable": True,
                            },
                        },
                    },
                    "primary": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "meta": {
                "type": "dict",
                "schema": {
                    "createdAt": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "offerType": {"type": "string", "nullable": True},
            "platforms": {"type": "list", "nullable": True},
            "prices": {
                "type": "dict",
                "schema": {
                    "rent": {
                        "type": "dict",
                        "schema": {
                            "interval": {"type": "string", "nullable": True},
                            "gross": {"type": "integer", "nullable": True},
                        },
                        "nullable": True,
                    },
                    "currency": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "listingCard": {
        "type": "dict",
        "schema": {
            "size": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "id": {"type": "string", "minlength": 1},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    search_data = await homegate.scrape_search(
        url="https://www.homegate.ch/rent/real-estate/city-bern/matching-list",
        scrape_all_pages=False,
        max_scrape_pages=2,
    )
    urls = [f"https://www.homegate.ch/rent/{item['listing']['id']}" for item in search_data]

    result = await homegate.scrape_properties(
        urls=urls[:5]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/properties.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await homegate.scrape_search(
        url="https://www.homegate.ch/rent/real-estate/city-bern/matching-list",
        scrape_all_pages=False,
        max_scrape_pages=2,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 2
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
