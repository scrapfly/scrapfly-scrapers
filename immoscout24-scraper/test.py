import os
from pathlib import Path
from cerberus import Validator
import immoscout24
import pytest
import pprint
import json

pp = pprint.PrettyPrinter(indent=4)
immoscout24.BASE_CONFIG['cache'] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "lister": {
        "type": "dict",
        "schema": {
            "legalName": {"type": "string", "nullable": True},
            "website": {
                "type": "dict",
                "schema": {
                    "value": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "address": {
                "type": "dict",
                "schema": {
                    "locality": {"type": "string", "nullable": True},
                    "country": {"type": "string", "nullable": True},
                    "street": {"type": "string", "nullable": True},
                    "postalCode": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
        },
        "nullable": True,
    },
    "characteristics": {
        "type": "dict",
        "schema": {
            "numberOfRooms": {"type": "float", "nullable": True},
            "yearBuilt": {"type": "integer", "nullable": True},
            "floor": {"type": "integer", "nullable": True},
            "livingSpace": {"type": "integer", "nullable": True},
        },
        "nullable": True,
    },
}


search_schema = {
    "id": {"type": "string", "minlength": 1},
    "accountId": {"type": "integer", "nullable": True},
    "companyId": {"type": "integer", "nullable": True},
    "memberPackageId": {"type": "integer", "nullable": True},
    "agency": {
        "type": "dict",
        "schema": {
            "companyCity": {"type": "string", "nullable": True},
            "companyName1": {"type": "string", "nullable": True},
            "companyPhoneBusiness": {"type": "string", "nullable": True},
            "companyStreet": {"type": "string", "nullable": True},
            "companyZip": {"type": "string", "nullable": True},
            "firstName": {"type": "string", "nullable": True},
            "gender": {"type": "string", "nullable": True},
            "gendshowLogoOnSerper": {"type": "boolean", "nullable": True},
            "lastName": {"type": "string", "nullable": True},
            "logoUrl": {"type": "string", "nullable": True},
            "logoUrlDetailPage": {"type": "string", "nullable": True},
            "nameFormatted": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "availableFrom": {"type": "string", "nullable": True},
    "availableFromFormatted": {"type": "string", "nullable": True},
    "cityId": {"type": "integer", "nullable": True},
    "cityName": {"type": "string", "nullable": True},
    "commuteTimes": {
        "type": "dict",
        "schema": {
            "defaultPois": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "defaultPoiId": {"type": "integer", "nullable": True},
                        "label": {"type": "string", "nullable": True},
                        "transportations": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "transportationTypeId": {"type": "integer", "nullable": True},
                                    "travelTime": {"type": "integer", "nullable": True},
                                    "isReachable": {"type": "boolean", "nullable": True},
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
    "countryId": {"type": "integer", "nullable": True},
    "extraPrice": {"type": "integer", "nullable": True},
    "geoAccuracy": {"type": "integer", "nullable": True},
    "grossPrice": {"type": "integer", "nullable": True},
    "hasNewBuildingProject": {"type": "boolean", "nullable": True},
    "hasVirtualTour": {"type": "boolean", "nullable": True},
    "isHighlighted": {"type": "boolean", "nullable": True},
    "isNeubauLite": {"type": "boolean", "nullable": True},
    "isNeubauLitePremium": {"type": "boolean", "nullable": True},
    "isHgCrosslisting": {"type": "boolean", "nullable": True},
    "latitude": {"type": "integer", "nullable": True},
    "longitude": {"type": "integer", "nullable": True},
    "netPrice": {"type": "integer", "nullable": True},
    "numberOfRooms": {"type": "integer", "nullable": True},
    "price": {"type": "integer", "nullable": True},
    "propertyUrl": {"type": "string", "minlength": 1},
    "propertyCategoryId": {"type": "integer", "nullable": True},
    "propertyTypeId": {"type": "integer", "nullable": True},
    "state": {"type": "string", "nullable": True},
    "street": {"type": "string", "nullable": True},
    "surfaceLiving": {"type": "integer", "nullable": True},
    "images": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string", "nullable": True},
                "originalWidth": {"type": "integer", "nullable": True},
                "originalHeight": {"type": "integer", "nullable": True},
                "id": {"type": "integer", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
    "lastPublished": {"type": "string", "nullable": True},
    "sortalgoScore": {"type": "integer", "nullable": True},
    "sortalgoScore2": {"type": "integer", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    search_data = await immoscout24.scrape_search(
        url="https://www.immoscout24.ch/en/real-estate/rent/city-bern",
        scrape_all_pages=False,
        max_scrape_pages=2,        
    )
    urls = ["https://www.immoscout24.ch/rent/" + item["listing"]["id"] for item in search_data]

    result = await immoscout24.scrape_properties(
        urls=urls[:4]
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
    result = await immoscout24.scrape_search(
        url="https://www.immoscout24.ch/en/real-estate/rent/city-bern",
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
