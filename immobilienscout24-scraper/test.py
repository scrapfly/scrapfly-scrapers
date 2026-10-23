import json
import os
from pathlib import Path
from cerberus import Validator
import immobilienscout24
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)
immobilienscout24.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "id": {"type": "integer", "nullable": True},
    "title": {"type": "string", "minlength": 1},
    "description": {"type": "string", "nullable": True},
    "address": {"type": "string", "minlength": 1},
    "propertyLlink": {"type": "string", "minlength": 1},
    "propertySepcs": {
        "type": "dict",
        "schema": {
            "floorsNumber": {"type": "string", "nullable": True},
            "livingSpace": {"type": "string", "nullable": True},
            "livingSpaceUnit": {"type": "string", "nullable": True},
            "vacantFrom": {"type": "string", "nullable": True},
            "numberOfRooms": {"type": "integer", "nullable": True},
            "Garage/parking space": {"type": "string", "nullable": True},
            "additionalSpecs": {
                "type": "list",
                "schema": {"type": "string", "nullable": True},
                "nullable": True,
            },
            "internetAvailable": {"type": "boolean", "nullable": True},
            "internetSpeed": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "price": {
        "type": "dict",
        "schema": {
            "priceWithoutHeadting": {"type": "string", "nullable": True},
            "priceperMeter": {"type": "string", "nullable": True},
            "additionalCosts": {"type": "string", "nullable": True},
            "heatingCosts": {"type": "string", "nullable": True},
            "totalRent": {"type": "string", "nullable": True},
            "basisRent": {"type": "string", "nullable": True},
            "deposit": {"type": "string", "nullable": True},
            "garage/parkingRent": {"type": "string", "nullable": True},
            "priceCurrency": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "building": {
        "type": "dict",
        "schema": {
            "constructionYear": {"type": "integer", "nullable": True},
            "energySources": {"type": "string", "nullable": True},
            "energyCertificate": {"type": "string", "nullable": True},
            "energyCertificateType": {"type": "string", "nullable": True},
            "energyCertificateDate": {"type": "integer", "nullable": True},
            "finalEnergyRrequirement": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "attachments": {
        "type": "dict",
        "schema": {
            "propertyImages": {
                "type": "list",
                "schema": {"type": "string", "nullable": True},
                "nullable": True,
            },
            "videoAvailable": {"type": "boolean", "nullable": True},
        },
        "nullable": True,
    },
    "agencyName": {"type": "string", "nullable": True},
    "agencyAddress": {"type": "string", "nullable": True},
}


search_schema = {
    "@id": {"type": "string", "minlength": 1},
    "@modification": {"type": "string", "nullable": True},
    "@creation": {"type": "string", "nullable": True},
    "@publishDate": {"type": "string", "nullable": True},
    "realEstateId": {"type": "integer", "nullable": True},
    "disabledGrouping": {"type": "string", "nullable": True},
    "resultlist.realEstate": {
        "type": "dict",
        "schema": {
            "@xsi.type": {"type": "string", "nullable": True},
            "@id": {"type": "string", "nullable": True},
            "title": {"type": "string", "nullable": True},
            "address": {
                "type": "dict",
                "schema": {
                    "street": {"type": "string", "nullable": True},
                    "houseNumber": {"type": "string", "nullable": True},
                    "postcode": {"type": "string", "nullable": True},
                    "city": {"type": "string", "nullable": True},
                    "quarter": {"type": "string", "nullable": True},
                    "wgs84Coordinate": {
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
            "companyWideCustomerId": {"type": "string", "nullable": True},
            "floorplan": {"type": "string", "nullable": True},
            "streamingVideo": {"type": "string", "nullable": True},
            "listingType": {"type": "string", "nullable": True},
            "showcasePlacementColor": {"type": "string", "nullable": True},
            "privateOffer": {"type": "string", "nullable": True},
            "contactDetails": {
                "type": "dict",
                "schema": {
                    "salutation": {"type": "string", "nullable": True},
                    "firstname": {"type": "string", "nullable": True},
                    "lastname": {"type": "string", "nullable": True},
                    "company": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "realtorCompanyName": {"type": "string", "nullable": True},
            "realtorLogoForResultList": {
                "type": "dict",
                "schema": {
                    "@xsi.type": {"type": "string", "nullable": True},
                    "floorplan": {"type": "string", "nullable": True},
                    "titlePicture": {"type": "string", "nullable": True},
                    "urls": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "url": {
                                    "type": "dict",
                                    "schema": {
                                        "@scale": {"type": "string", "nullable": True},
                                        "@href": {"type": "string", "nullable": True},
                                    },
                                    "nullable": True,
                                },
                            },
                            "nullable": True,
                        },
                        "nullable": True,
                    },
                    "galleryAttachments": {
                        "type": "dict",
                        "schema": {
                            "attachment": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "@xsi.type": {"type": "string", "nullable": True},
                                        "floorplan": {"type": "string", "nullable": True},
                                        "@titlePicture": {"type": "string", "nullable": True},
                                        "urls": {
                                            "type": "list",
                                            "schema": {
                                                "type": "dict",
                                                "schema": {
                                                    "url": {
                                                        "type": "dict",
                                                        "schema": {
                                                            "@scale": {"type": "string", "nullable": True},
                                                            "@href": {"type": "string", "nullable": True},
                                                        },
                                                        "nullable": True,
                                                    },
                                                },
                                                "nullable": True,
                                            },
                                            "nullable": True,
                                        },
                                    },
                                    "nullable": True,
                                },
                                "nullable": True,
                            },
                        },
                        "nullable": True,
                    },
                    "spotlightListing": {"type": "string", "nullable": True},
                    "verifiedBy": {
                        "type": "list",
                        "schema": {"type": "string", "nullable": True},
                        "nullable": True,
                    },
                    "price": {
                        "type": "dict",
                        "schema": {
                            "value": {"type": "integer", "nullable": True},
                            "currency": {"type": "string", "nullable": True},
                            "marketingType": {"type": "string", "nullable": True},
                            "priceIntervalType": {"type": "string", "nullable": True},
                        },
                        "nullable": True,
                    },
                    "livingSpace": {"type": "integer", "nullable": True},
                    "numberOfRooms": {"type": "integer", "nullable": True},
                    "builtInKitchen": {"type": "string", "nullable": True},
                    "balcony": {"type": "string", "nullable": True},
                    "garden": {"type": "string", "nullable": True},
                    "calculatedTotalRent": {
                        "type": "dict",
                        "schema": {
                            "totalRent": {
                                "type": "dict",
                                "schema": {
                                    "value": {"type": "integer", "nullable": True},
                                    "currency": {"type": "string", "nullable": True},
                                    "marketingType": {"type": "string", "nullable": True},
                                    "priceIntervalType": {"type": "string", "nullable": True},
                                },
                                "nullable": True,
                            },
                            "calculationMode": {"type": "string", "nullable": True},
                        },
                        "nullable": True,
                    },
                    "attributes": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "attribute": {
                                    "type": "list",
                                    "schema": {
                                        "type": "dict",
                                        "schema": {
                                            "label": {"type": "string", "nullable": True},
                                            "value": {"type": "string", "nullable": True},
                                        },
                                        "nullable": True,
                                    },
                                    "nullable": True,
                                },
                            },
                            "nullable": True,
                        },
                        "nullable": True,
                    },
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    search_data = await immobilienscout24.scrape_search(
        url="https://www.immobilienscout24.de/Suche/de/bayern/muenchen/wohnung-mieten",
        scrape_all_pages=False,
        max_scrape_pages=1,
    )
    urls = ["https://www.immobilienscout24.de/expose/" + i["@id"] for i in search_data]

    result = await immobilienscout24.scrape_properties(
        urls=urls[:3]
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
    result = await immobilienscout24.scrape_search(
        url="https://www.immobilienscout24.de/Suche/de/bayern/muenchen/wohnung-mieten",
        scrape_all_pages=False,
        max_scrape_pages=3,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["@id"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )

