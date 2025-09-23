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
    "schema": {
        "type": "dict",
        "schema": {
            "listingId": {"type": "integer"},
            "listingUrl": {"type": "string"},
            "unitNumber": {"type": "string"},
            "street": {"type": "string"},
            "suburb": {"type": "string"},
            "postcode": {"type": "string"},
            "createdOn": {"type": "string"},
            "propertyType": {"type": "string"},
            "beds": {"type": "integer"},
            "phone": {"type": "string"},
            "agencyName": {"type": "string"},
            "propertyDeveloperName": {"type": "string"},
            "agencyProfileUrl": {"type": "string"},
            "propertyDeveloperUrl": {"type": "string"},
            "description": {
                "type": "list",
                "schema": {
                    "type": "string"
                }
            },
            "listingSummary": {
                "type": "dict",
                "schema": {
                    "beds": {"type": "integer"},
                    "baths": {"type": "integer"},
                    "parking": {"type": "integer"},
                    "title": {"type": "string"},
                    "price": {"type": "string"},
                    "address": {"type": "string"},
                    "listingType": {"type": "string"},
                    "propertyType": {"type": "string"},
                    "status": {"type": "string"},
                    "mode": {"type": "string"},
                }
            },
            "agents": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "name": {"type": "string"},
                        "photo": {"type": "string"},
                        "phone": {"type": "string", "nullable": True},
                        "mobile": {"type": "string", "nullable": True},
                        "agentProfileUrl": {"type": "string"},
                    }
                }
            }
        }
    }
}


search_schema = {
    "schmea": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer"},
            "listingType": {"type": "string"},
            "listingModel": {
                "type": "dict",
                "schema": {
                    "promoType": {"type": "string"},
                    "url": {"type": "string"},
                    "projectName": {"type": "string"},
                    "displayAddress": {"type": "string"},
                    "images": {
                        "type": "list",
                        "schema": {
                            "type": "string"
                        }
                    },
                    "branding": {
                        "type": "dict",
                        "schema": {
                            "agencyId": {"type": "string"},
                            "agentNames": {"type": "string"},
                            "brandName": {"type": "string"}
                        }
                    },
                    "childListingIds": {
                        "type": "list",
                        "schema": {
                            "type": "integer"
                        }
                    },
                    "address": {
                        "type": "dict",
                        "schema": {
                            "street": {"type": "string"},
                            "suburb": {"type": "string"},
                            "state": {"type": "string"},
                            "postcode": {"type": "string"},
                            "lat": {"type": "integer"},
                            "lng": {"type": "integer"},
                        }
                    }
                }
            }

        }
    }
}


@pytest.mark.asyncio
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