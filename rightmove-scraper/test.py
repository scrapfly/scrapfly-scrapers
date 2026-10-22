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
    "id": {"type": "integer", "nullable": True},
    "bedrooms": {"type": "integer", "nullable": True},
    "bathrooms": {"type": "integer", "nullable": True},
    "numberOfImages": {"type": "integer", "nullable": True},
    "numberOfFloorplans": {"type": "integer", "nullable": True},
    "numberOfVirtualTours": {"type": "integer", "nullable": True},
    "summary": {"type": "string", "nullable": True},
    "displayAddress": {"type": "string", "minlength": 1},
    "countryCode": {"type": "string", "nullable": True},
    "location": {
        "type": "dict",
        "schema": {
            "latitude": {"type": "float", "nullable": True},
            "longitude": {"type": "float", "nullable": True},
        },
        "nullable": True,
    },
    "propertyImages": {
        "type": "dict",
        "schema": {
            "images": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "srcUrl": {"type": "string", "nullable": True},
                        "url": {"type": "string", "nullable": True},
                        "caption": {"type": "string", "nullable": True},
                    },
                    "nullable": True,
                },
                "nullable": True,
            },
            "mainImageSrc": {"type": "string", "nullable": True},
            "mainMapImageSrc": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "propertySubType": {"type": "string", "nullable": True},
    "listingUpdate": {
        "type": "dict",
        "schema": {
            "listingUpdateReason": {"type": "string", "nullable": True},
            "listingUpdateDate": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "premiumListing": {"type": "boolean", "nullable": True},
    "featuredProperty": {"type": "boolean", "nullable": True},
    "price": {
        "type": "dict",
        "schema": {
            "amount": {"type": "integer", "nullable": True},
            "frequency": {"type": "string", "nullable": True},
            "currencyCode": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "customer": {
        "type": "dict",
        "schema": {
            "amount": {"type": "integer", "nullable": True},
            "brandPlusLogoURI": {"type": "string", "nullable": True},
            "contactTelephone": {"type": "string", "nullable": True},
            "branchDisplayName": {"type": "string", "nullable": True},
            "branchName": {"type": "string", "nullable": True},
            "brandTradingName": {"type": "string", "nullable": True},
            "branchLandingPageUrl": {"type": "string", "nullable": True},
            "development": {"type": "boolean", "nullable": True},
            "showReducedProperties": {"type": "boolean", "nullable": True},
            "commercial": {"type": "boolean", "nullable": True},
            "showOnMap": {"type": "boolean", "nullable": True},
            "enhancedListing": {"type": "boolean", "nullable": True},
            "developmentContent": {"type": "dict", "nullable": True},
            "buildToRent": {"type": "boolean", "nullable": True},
        },
        "nullable": True,
    },
    "commercial": {"type": "boolean", "nullable": True},
    "development": {"type": "boolean", "nullable": True},
    "residential": {"type": "boolean", "nullable": True},
    "students": {"type": "boolean", "nullable": True},
    "auction": {"type": "boolean", "nullable": True},
    "feesApply": {"type": "boolean", "nullable": True},
    "feesApplyText": {"type": "boolean", "nullable": True},
    "propertyUrl": {"type": "string", "minlength": 1},
    "contactUrl": {"type": "string", "nullable": True},
    "hasBrandPlus": {"type": "boolean", "nullable": True},
    "displayStatus": {"type": "string", "nullable": True},
    "addedOrReduced": {"type": "string", "nullable": True},
    "formattedBranchName": {"type": "string", "nullable": True},
    "propertyTypeFullDescription": {"type": "string", "nullable": True},
    "heading": {"type": "string", "nullable": True},
    "isRecent": {"type": "boolean", "nullable": True},
}


properties_schema = {
    "id": {"type": "string", "minlength": 1},
    "available": {"type": "boolean", "nullable": True},
    "archived": {"type": "boolean", "nullable": True},
    "phone": {"type": "string", "nullable": True},
    "bedrooms": {"type": "integer", "nullable": True},
    "bathrooms": {"type": "integer", "nullable": True},
    "type": {"type": "string", "nullable": True},
    "property_type": {"type": "string", "nullable": True},
    "tags": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "description": {"type": "string", "nullable": True},
    "title": {"type": "string", "minlength": 1},
    "subtitle": {"type": "string", "nullable": True},
    "price": {"type": "string", "nullable": True},
    "address": {
        "type": "dict",
        "schema": {
            "displayAddress": {"type": "string", "nullable": True},
            "countryCode": {"type": "string", "nullable": True},
            "ukCountry": {"type": "string", "nullable": True},
            "outcode": {"type": "string", "nullable": True},
            "incode": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "latitude": {"type": "float", "nullable": True},
    "longitude": {"type": "float", "nullable": True},
    "features": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "history": {
        "type": "dict",
        "schema": {
            "listingUpdateReason": {"type": "string", "nullable": True},
        },
        "nullable": True,
    },
    "photos": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string", "nullable": True},
                "caption": {"type": "string", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
    "floorplans": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string", "nullable": True},
                "caption": {"type": "string", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
    "agency": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer", "nullable": True},
            "branch": {"type": "string", "nullable": True},
            "company": {"type": "string", "nullable": True},
            "address": {"type": "string", "nullable": True},
            "commercial": {"type": "boolean", "nullable": True},
            "buildToRent": {"type": "boolean", "nullable": True},
            "isNew": {"type": "boolean", "nullable": True},
        },
        "nullable": True,
    },
    "industryAffiliations": {
        "type": "list",
        "schema": {"type": "string", "nullable": True},
        "nullable": True,
    },
    "nearest_stations": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string", "nullable": True},
                "distance": {"type": "float", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
    "brochures": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string", "nullable": True},
                "caption": {"type": "string", "nullable": True},
            },
            "nullable": True,
        },
        "nullable": True,
    },
}


@pytest.mark.asyncio
async def test_search_scraping():
    cornwall_id = (await rightmove.find_locations("cornwall"))[0]
    search_data = await rightmove.scrape_search(
        location_name="Cornwall", location_id=cornwall_id, max_properties=50, scrape_all_properties=False
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_properties_scraping():
    cornwall_id = (await rightmove.find_locations("cornwall"))[0]
    search_data = await rightmove.scrape_search(
        location_name="Cornwall", location_id=cornwall_id, max_properties=48, scrape_all_properties=False
    )
    urls = [
        "https://www.rightmove.co.uk" + item["propertyUrl"]
        for item in search_data
        if item.get("propertyUrl")
    ][:5]

    properties_data = await rightmove.scrape_properties(urls=urls)
    validator = Validator(properties_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1
