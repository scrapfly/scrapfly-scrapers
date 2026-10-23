import json
import os
from pathlib import Path
from cerberus import Validator
import domaincom
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)


# enable scrapfly cache
domaincom.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "listingId": {"type": "integer", "nullable": True},
    "listingUrl": {"type": "string", "minlength": 1},
    "unitNumber": {"type": "string", "nullable": True},
    "street": {"type": "string", "nullable": True},
    "suburb": {
        "type": [
            "dict",
            "string",
        ],
        "nullable": True,
    },
    "postcode": {"type": "string", "nullable": True},
    "createdOn": {"type": "string", "nullable": True},
    "propertyType": {"type": "string", "nullable": True},
    "beds": {"type": "integer", "nullable": True},
    "phone": {"type": "string", "nullable": True},
    "agencyName": {"type": "string", "nullable": True},
    "propertyDeveloperName": {"type": "string", "nullable": True},
    "agencyProfileUrl": {"type": "string", "nullable": True},
    "propertyDeveloperUrl": {"type": "string", "nullable": True},
    "description": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "listingSummary": {
        "type": "dict",
        "schema": {
            "beds": {"type": "integer", "nullable": True},
            "baths": {"type": "integer", "nullable": True},
            "parking": {"type": "integer", "nullable": True},
            "title": {"type": "string", "nullable": True},
            "price": {"type": "string", "nullable": True},
            "address": {"type": "string", "nullable": True},
            "listingType": {"type": "string", "nullable": True},
            "propertyType": {"type": "string", "nullable": True},
            "status": {"type": "string", "nullable": True},
            "mode": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "agents": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string", "nullable": True},
                "photo": {"type": "string", "nullable": True},
                "phone": {"type": "string", "nullable": True},
                "mobile": {"type": "string", "nullable": True},
                "agentProfileUrl": {"type": "string", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
}


search_schema = {
    "id": {"type": "integer", "nullable": True},
    "listingType": {"type": "string", "minlength": 1},
    "listingModel": {
        "type": "dict",
        "schema": {
            "promoType": {"type": "string", "nullable": True},
            "url": {"type": "string", "nullable": True},
            "projectName": {"type": "string", "nullable": True},
            "displayAddress": {"type": "string", "nullable": True},
            "images": {
                "type": "list",
                "schema": {"type": "string", "nullable": True},
                "nullable": True,
            },
            "branding": {
                "type": "dict",
                "schema": {
                    "agencyId": {"type": "integer", "nullable": True},
                    "agentNames": {"type": "string", "nullable": True},
                    "brandName": {"type": "string", "nullable": True},
                },
                "nullable": True,
            },
            "childListingIds": {
                "type": "list",
                "schema": {"type": "integer", "nullable": True},
                "nullable": True,
            },
            "address": {
                "type": "dict",
                "schema": {
                    "street": {"type": "string", "nullable": True},
                    "suburb": {"type": "string", "nullable": True},
                    "state": {"type": "string", "nullable": True},
                    "postcode": {"type": "string", "nullable": True},
                    "lat": {"type": "float", "nullable": True},
                    "lng": {"type": "float", "nullable": True},
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
    properties_data = await domaincom.scrape_properties(
        urls = [
            "https://www.domain.com.au/610-399-bourke-street-melbourne-vic-3000-2018835548",
            "https://www.domain.com.au/property-profile/308-9-degraves-street-melbourne-vic-3000",
            "https://www.domain.com.au/1518-474-flinders-street-melbourne-vic-3000-17773317"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    # for item in properties_data:
    validate_or_fail(properties_data[0], validator)
    assert len(properties_data) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/properties.json').write_text(json.dumps(properties_data, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await domaincom.scrape_search(
        url="https://www.domain.com.au/sale/melbourne-vic-3000", max_scrape_pages=1
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(search_data, indent=2, ensure_ascii=False))