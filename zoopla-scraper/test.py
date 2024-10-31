from cerberus import Validator
import zoopla
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
zoopla.BASE_CONFIG["cache"] = False

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


search_schema = {
    "title": {"type": "string"},
    "price": {"type": "string"},
    "url": {"type": "string"},
    "image": {"type": "string", "nullable": True},
    "address": {"type": "string"},
    "squareFt": {"type": "integer", "nullable": True},
    "numBathrooms": {"type": "integer", "nullable": True},
    "numBedrooms": {"type": "integer", "nullable": True},
    "numLivingRoom": {"type": "integer", "nullable": True},
    "justAdded": {"type": "boolean", "nullable": True},
    "propertyType": {"type": "string", "nullable": True},
    "timeAdded": {"type": "string"},
}

property_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "url": {"type": "string"},
            "price": {"type": "string"},
            "type": {"type": "string"},
            "date": {"type": "string"},
            "category": {"type": "string"},
            "section": {"type": "string"},
            "features": {
                "type": "list",
                "schema": {
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                }
            },
            "floor_plan": {
                "type": "dict",
                "schema": {
                    "filename": {"type": "string", "nullable": True},
                    "caption": {"type": "string", "nullable": True},
                }
            },
            "nearby": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "title": {"type": "string"},
                        "distance": {"type": "integer"},
                    }
                }
            },
            "coordinates": {
                "type": "dict",
                "schema": {
                    "lat": {"type": "integer"},
                    "lng": {"type": "integer"},
                }
            },
            "photos": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "filename": {"type": "string"},
                        "caption": {"type": "string"},
                    }
                }
            },
            "__typename": {"type": "string"},
            "location": {"type": "string"},
            "regionName": {"type": "string"},
            "section": {"type": "string"},
            "acorn": {"type": "integer"},
            "acornType": {"type": "integer"},
            "areaName": {"type": "string"},
            "bedsMax": {"type": "integer"},
            "bedsMin": {"type": "integer"},
            "branchId": {"type": "integer"},
            "branchLogoUrl": {"type": "string"},
            "branchName": {"type": "string"},
            "brandName": {"type": "string"},
            "chainFree": {"type": "boolean"},
            "companyId": {"type": "integer"},
            "countryCode": {"type": "string"},
            "countyAreaName": {"type": "string"},
            "currencyCode": {"type": "string"},
            "displayAddress": {"type": "string"},
            "hasEpc": {"type": "boolean"},
            "hasFloorplan": {"type": "boolean"},
            "incode": {"type": "string"},
            "isRetirementHome": {"type": "boolean"},
            "isSharedOwnership": {"type": "boolean"},
            "listingCondition": {"type": "string"},
            "listingId": {"type": "integer"},
            "listingsCategory": {"type": "string"},
            "listingStatus": {"type": "string"},
            "memberType": {"type": "string"},
            "numBaths": {"type": "integer"},
            "numBeds": {"type": "integer"},
            "numImages": {"type": "integer"},
            "numRecepts": {"type": "integer"},
            "outcode": {"type": "string"},
            "postalArea": {"type": "string"},
            "postTownName": {"type": "string"},
            "priceActual": {"type": "integer"},
            "price": {"type": "integer"},
            "priceMax": {"type": "integer"},
            "priceMin": {"type": "integer"},
            "propertyHighlight": {"type": "string"},
            "propertyType": {"type": "string"},
            "tenure": {"type": "string"},
            "zindex": {"type": "integer"},
            "agency": {
                "type": "dict",
                "schema": {
                    "__typename": {"type": "string"},
                    "branchDetailsUri": {"type": "string"},
                    "branchId": {"type": "string"},
                    "branchResultsUri": {"type": "string"},
                    "logoUrl": {"type": "string"},
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                    "memberType": {"type": "string"},
                    "address": {"type": "string"},
                    "postcode": {"type": "string"},
                }
            }
        }
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await zoopla.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=2,
        location_slug="london/islington",
        query_type= "to-rent"
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)

    for k in search_schema:
        require_min_presence(search_data, k, min_perc=search_schema[k].get("min_presence", 0.1))  

    assert len(search_data) >= 25


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    properties_data = await zoopla.scrape_properties(
        urls=[
        "https://www.zoopla.co.uk/new-homes/details/67644732/",
        "https://www.zoopla.co.uk/new-homes/details/66702316/",
        "https://www.zoopla.co.uk/new-homes/details/67644753/",
        "https://www.zoopla.co.uk/new-homes/details/63945970/",
        "https://www.zoopla.co.uk/new-homes/details/68581498/",
        "https://www.zoopla.co.uk/new-homes/details/68635032/"
    ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1
