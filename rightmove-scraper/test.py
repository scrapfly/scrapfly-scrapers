from cerberus import Validator
import rightmove
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
rightmove.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer"},
            "bedrooms": {"type": "integer"},
            "bathrooms": {"type": "integer"},
            "numberOfImages": {"type": "integer"},
            "numberOfFloorplans": {"type": "integer", "nullable": True},
            "numberOfVirtualTours": {"type": "integer", "nullable": True},
            "summary": {"type": "string"},
            "displayAddress": {"type": "string"},
            "countryCode": {"type": "string"},
            "location": {
                "type": "dict",
                "schema": {
                    "latitude": {"type": "integer", "nullable": True},
                    "longitude": {"type": "integer", "nullable": True},
                },
            },
            "propertyImages": {
                "type": "list",
                "schema": {
                    "images": {
                        "type": "dict",
                        "schema": {
                            "srcUrl": {"type": "string"},
                            "url": {"type": "string"},
                            "caption": {"type": "integer"},
                        },
                    },
                    "mainImageSrc": {"type": "string"},
                    "mainMapImageSrc": {"type": "string"},
                },
            },
            "propertySubType": {"type": "string"},
            "listingUpdate": {
                "type": "dict",
                "schema": {
                    "listingUpdateReason": {"type": "string"},
                    "listingUpdateDate": {"type": "string"},
                },
            },
            "premiumListing": {"type": "boolean"},
            "featuredProperty": {"type": "boolean"},
            "price": {
                "type": "dict",
                "schema": {
                    "amount": {"type": "integer"},
                    "frequency": {"type": "string"},
                    "currencyCode": {"type": "string"},
                },
            },
            "customer": {
                "type": "dict",
                "schema": {
                    "amount": {"type": "integer"},
                    "brandPlusLogoURI": {"type": "string"},
                    "contactTelephone": {"type": "string"},
                    "branchDisplayName": {"type": "string"},
                    "branchName": {"type": "string"},
                    "brandTradingName": {"type": "string"},
                    "branchLandingPageUrl": {"type": "string"},
                    "development": {"type": "boolean"},
                    "showReducedProperties": {"type": "boolean"},
                    "commercial": {"type": "boolean"},
                    "showOnMap": {"type": "boolean"},
                    "enhancedListing": {"type": "boolean", "nullable": True},
                    "developmentContent": {"type": "boolean", "nullable": True},
                    "buildToRent": {"type": "boolean", "nullable": True},
                },
            },
            "commercial": {"type": "boolean"},
            "development": {"type": "boolean"},
            "residential": {"type": "boolean"},
            "students": {"type": "boolean"},
            "auction": {"type": "boolean"},
            "feesApply": {"type": "boolean"},
            "feesApplyText": {"type": "boolean", "nullable": True},
            "propertyUrl": {"type": "string"},
            "contactUrl": {"type": "string"},
            "hasBrandPlus": {"type": "boolean"},
            "displayStatus": {"type": "string"},
            "addedOrReduced": {"type": "string"},
            "formattedBranchName": {"type": "string"},
            "propertyTypeFullDescription": {"type": "string"},
            "heading": {"type": "string"},
            "isRecent": {"type": "boolean"},
        },
    }
}


properties_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "available": {"type": "boolean"},
            "archived": {"type": "boolean"},
            "phone": {"type": "string"},
            "bedrooms": {"type": "integer"},
            "bathrooms": {"type": "integer"},
            "type": {"type": "string"},
            "property_type": {"type": "string"},
            "tags": {"type": "dict", "schema": {"type": "string"}},
            "description": {"type": "string"},
            "title": {"type": "string"},
            "subtitle": {"type": "string"},
            "price": {"type": "string"},
            "address": {
                "type": "dict",
                "schema": {
                    "displayAddress": {"type": "string"},
                    "countryCode": {"type": "string"},
                    "ukCountry": {"type": "string"},
                    "outcode": {"type": "string"},
                    "incode": {"type": "string"},
                },
            },
            "latitude": {"type": "string", "nullable": True},
            "longitude": {"type": "string", "nullable": True},
            "features": {"type": "list", "schema": {"type": "string"}},
            "history": {
                "type": "dict",
                "schema": {"listingUpdateReason": {"type": "string"}},
            },
            "photos": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "url": {"type": "string"},
                        "caption": {"type": "string"},
                    },
                },
            },
            "floorplans": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "url": {"type": "string"},
                        "caption": {"type": "string"},
                    },
                },
            },
            "agency": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer"},
                    "branch": {"type": "string"},
                    "company": {"type": "string"},
                    "address": {"type": "string"},
                    "commercial": {"type": "boolean"},
                    "buildToRent": {"type": "boolean"},
                    "isNew": {"type": "boolean"},
                },
            },
            "industryAffiliations": {"type": "list", "schema": {"type": "string"}},
            "nearest_stations": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "name": {"type": "string"},
                        "distance": {"type": "integer"},
                    },
                },
            },
            "brochures": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "url": {"type": "string"},
                        "caption": {"type": "integer"},
                    },
                },
            },
        },
    }
}


@pytest.mark.asyncio
async def test_search_scraping():
    cornwall_id = (await rightmove.find_locations("cornwall"))[0]
    search_data = await rightmove.scrape_search(
        cornwall_id, max_properties=50, scrape_all_properties=False
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await rightmove.scrape_properties(
        urls=[
            "https://www.rightmove.co.uk/properties/149360984#/",
            "https://www.rightmove.co.uk/properties/136408088#/",
            "https://www.rightmove.co.uk/properties/148922639#/",
        ]
    )
    validator = Validator(properties_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1
