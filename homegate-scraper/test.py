from cerberus import Validator
import homegate
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
homegate.BASE_CONFIG["cache"] = True


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
            "localization": {
                "type": "dict",
                "schema": {
                    "de": {
                        "type": "dict",
                        "schema": {
                            "text": {
                                "type": "dict",
                                "schema": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                            },
                            "attachments": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "type": {"type": "string"},
                                        "url": {"type": "string"},
                                        "file": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "primary": {"type": "string"},
                },
            },
            "lister": {
                "type": "dict",
                "schema": {
                    "primary": {"type": "string"},
                    "website": {
                        "type": "dict",
                        "schema": {"value": {"type": "string"}},
                    },
                    "id": {"type": "string"},
                    "allowToContact": {"type": "boolean", "nullable": True},
                },
            },
            "characteristics": {
                "type": "dict",
                "schema": {
                    "livingSpace": {"type": "integer"},
                    "numberOfRooms": {"type": "integer"},
                },
            },
            "address": {
                "type": "dict",
                "schema": {
                    "country": {"type": "string"},
                    "geoDistances": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "distance": {"type": "integer"},
                                "geoTag": {"type": "string"},
                            },
                        },
                    },
                    "geoTags": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "street": {"type": "string"},
                    "postalCode": {"type": "string"},
                    "locality": {"type": "string"},
                    "geoCoordinates": {
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "accuracy": {"type": "string"},
                                "manual": {"type": "boolean"},
                                "latitude": {"type": "integer", "nullable": True},
                                "longitude": {"type": "integer", "nullable": True},
                            },
                        }
                    },
                },
            },
            "externalIds": {
                "type": "dict",
                "schema": {
                    "internalReferenceId": {"type": "string"},
                    "displayReferenceId": {"type": "string"},
                    "refObject": {"type": "string"},
                    "displayPropertyReferenceId": {"type": "string"},
                    "propertyReferenceId": {"type": "string"},
                },
            },
            "contactForm": {
                "type": "dict",
                "schema": {
                    "size": {"type": "string"},
                    "deliveryFormat": {"type": "string"},
                },
            },
            "version": {"type": "string"},
            "platform": {"type": "list", "schema": {"type": "string"}},
            "offerType": {"type": "string"},
            "meta": {
                "type": "dict",
                "schema": {
                    "createdAt": {"type": "string"},
                    "updatedAt": {"type": "string"},
                    "source": {"type": "string"},
                },
            },
            "id": {"type": "string"},
            "categories": {"type": "list", "schema": {"type": "string"}},
            "prices": {
                "type": "dict",
                "schema": {
                    "rent": {
                        "type": "dict",
                        "schema": {
                            "area": {"type": "string"},
                            "interval": {"type": "string"},
                            "net": {"type": "integer"},
                            "gross": {"type": "integer"},
                        },
                    },
                    "currency": {"type": "string"},
                },
            },
            "valueAddedServices": {
                "type": "dict",
                "schema": {"isTenantPlusListing": {"type": "boolean"}},
            },
        },
    },
}

search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "listingType": {
                "type": "dict",
                "schema": {
                    "type": {"type": "string"},
                },
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
                                    "accuracy": {"type": "string"},
                                    "manual": {"type": "boolean"},
                                    "latitude": {"type": "integer", "nullable": True},
                                    "longitude": {"type": "integer", "nullable": True},
                                },
                            },
                            "locality": {"type": "string"},
                            "postalCode": {"type": "string"},
                            "street": {"type": "string"},
                        },
                    },
                    "categories": {"type": "list", "schema": {"type": "string"}},
                    "characteristics": {
                        "type": "dict",
                        "schema": {
                            "hasNiceView": {"type": "boolean"},
                            "hasBalcony": {"type": "boolean"},
                            "hasElevator": {"type": "boolean"},
                            "livingSpace": {"type": "integer"},
                            "numberOfRooms": {"type": "integer"},
                            "floor": {"type": "integer"},
                            "isQuiet": {"type": "boolean"},
                            "yearBuilt": {"type": "integer"},
                            "hasGarage": {"type": "boolean"},
                        },
                    },
                    "id": {"type": "string"},
                    "localization": {
                        "type": "dict",
                        "schema": {
                            "de": {
                                "schema": {
                                    "text": {
                                        "type": "dict",
                                        "schema": {
                                            "title": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                    },
                                    "attachments": {
                                        "type": "list",
                                        "schema": {
                                            "type": "dict",
                                            "schema": {
                                                "type": {"type": "string"},
                                                "url": {"type": "string"},
                                                "file": {"type": "string"},
                                            },
                                        },
                                    },
                                }
                            },
                            "primary": {"type": "string"},
                        },
                    },
                    "meta": {
                        "type": "dict",
                        "schema": {
                            "createdAt": {"type": "string"},
                        },
                    },
                    "offerType": {"type": "string"},
                    "platforms": {"type": "string"},
                    "prices": {
                        "type": "dict",
                        "schema": {
                            "rent": {
                                "type": "dict",
                                "schema": {
                                    "interval": {"type": "string"},
                                    "gross": {"type": "integer"},
                                },
                            },
                            "currency": {"type": "integer"},
                        },
                    },
                },
            },
            "listingCard": {
                "type": "dict",
                "schema": {
                    "size": {"type": "string"},
                },
            },
            "id": {"type": "string"},
        },
    }
}


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await homegate.scrape_properties(
        urls=[
            "https://www.homegate.ch/rent/4000339190",
            "https://www.homegate.ch/rent/4000339215",
            "https://www.homegate.ch/rent/4000203103"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await homegate.scrape_search(
        url="https://www.homegate.ch/rent/real-estate/city-bern/matching-list",
        scrape_all_pages=False,
        max_scrape_pages=2,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
