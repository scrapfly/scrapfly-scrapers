from cerberus import Validator
import seloger
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
seloger.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


property_schema = {
    "brand": {"type": "string"},
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
                            "district": {"type": "string"},
                        },
                    },
                    "isAddressPublished": {"type": "boolean"},
                    "geometry": {
                        "type": "dict",
                        "schema": {
                            "type": {"type": "string"},
                            "coordinates": {"type": "list"},
                        },
                    },
                },
            },
            "description": {
                "type": "dict",
                "schema": {
                    "description": {"type": "string"},
                    "texts": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "text": {"type": "string"},
                            },
                        },
                    },
                    "headline": {"type": "string"},
                },
            },
            "hardFacts": {
                "type": "dict",
                "schema": {
                    "title": {"type": "string"},
                    "keyfacts": {"type": "list", "schema": {"type": "string"}},
                    "facts": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "type": {"type": "string"},
                                "value": {"type": "string"},
                                "splitValue": {"type": "string"},
                                "label": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "price": {
                "type": "dict",
                "schema": {
                    "base": {
                        "type": "dict",
                        "schema": {
                            "main": {
                                "type": "dict",
                                "schema": {
                                    "key": {"type": "string"},
                                    "label": {"type": "dict"},
                                    "value": {
                                        "type": "dict",
                                        "schema": {
                                            "main": {"type": "dict"},
                                            "alt": {"type": "dict"},
                                        },
                                    },
                                },
                            },
                            "type": {"type": "string"},
                        },
                    },
                    "components": {"type": "list"},
                    "layout": {"type": "string"},
                },
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
                            },
                        },
                    },
                    "details": {
                        "type": "dict",
                        "schema": {
                            "categories": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "elements": {
                                            "type": "list",
                                            "schema": {
                                                "type": "dict",
                                                "schema": {
                                                    "icon": {"type": "string"},
                                                    "value": {"type": "string"},
                                                },
                                            },
                                        },
                                        "title": {"type": "string"},
                                    },
                                },
                            }
                        },
                    },
                },
            },
            "gallery": {
                "type": "dict",
                "schema": {
                    "images": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "key": {"type": "string"},
                                "url": {"type": "string"},
                                "alt": {"type": "string", "required": False},
                                "classification": {
                                    "type": "dict",
                                    "schema": {
                                        "name": {"type": "string"},
                                        "version": {"type": "string"},
                                    },
                                },
                            },
                        },
                    }
                },
            },
        },
    },
    "contactSections": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "legacyId": {"type": "string"},
            "brand": {"type": "string"},
            "agencyId": {"type": "string"},
            "static": {
                "type": "dict",
                "schema": {
                    "phoneNumbers": {"type": "list", "schema": {"type": "string"}},
                },
            },
            "sticky": {
                "type": "dict",
                "schema": {
                    "phoneNumbers": {"type": "list", "schema": {"type": "string"}},
                },
            },
            "contactCard": {
                "type": "dict",
                "schema": {
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "phoneNumbers": {"type": "list", "schema": {"type": "string"}},
                    "isPrivateOwner": {"type": "boolean"},
                    "agencyLogo": {"type": "dict"},
                    "contactLogo": {"type": "dict"},
                },
            },
            "contactForm": {"type": "dict"},
            "mobilePhones": {"type": "dict"},
            "provider": {"type": "dict"},
            "confirmationPage": {"type": "dict"},
        },
    },
}
search_schema = {
    "title": {"type": "string"},
    "url": {"type": "string"},
    "images": {
        "type": "list",
        "schema": {"type": "string"}
    },
    "price": {"type": "string"},
    "price_per_m2": {"type": "string"},
    "property_facts": {
        "type": "list",
        "schema": {"type": "string"}
    },
    "address": {"type": "string"},
    "agency": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await seloger.scrape_search(
        url="https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08FR13100",
        max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_property_scraping():
    property_data = await seloger.scrape_property(
        urls=[
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/247611919.htm?ln=classified_search_results&serp_view=list&search=distributionTypes%3DBuy%26estateTypes%3DApartment%26locations%3DAD08FR13100&m=classified_search_results_classified_classified_detail_XL",
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/le-lac-bacalan/245875571.htm?ln=classified_search_results&serp_view=list&search=distributionTypes%3DBuy%26estateTypes%3DApartment%26locations%3DAD08FR13100&m=classified_search_results_classified_classified_detail_XL",
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/hotel-de-ville-quinconce-saint-seurin-fondaudege/247907293.htm?ln=classified_search_results&serp_view=list&search=distributionTypes%3DBuy%26estateTypes%3DApartment%26locations%3DAD08FR13100&m=classified_search_results_classified_classified_detail_XL",
        ]
    )
    validator = Validator(property_schema, allow_unknown=True, require_all=True)
    for property in property_data:
        validate_or_fail(property, validator)
    assert len(property_data) >= 1
