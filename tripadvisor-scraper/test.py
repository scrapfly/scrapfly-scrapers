import pytest
import pprint as pp
from cerberus import Validator
import tripadvisor

# enable cache?
tripadvisor.BASE_CONFIG["cache"] = True

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


@pytest.mark.asyncio
async def test_location_data_scraping():
    result_location = await tripadvisor.scrape_location_data(query="Malta")
    schema = {
        "localizedName": {"type": "string"},
        "locationV2": {"type": "dict"},
        "placeType": {"type": "string"},
        "latitude": {"type": "float"},
        "longitude": {"type": "float"},
        "isGeo": {"type": "boolean"},
        "thumbnail": {"type": "dict"},
        "url": {"type": "string", "required": True, "regex": r"/Tourism-.+?\.html"},
        "HOTELS_URL": {"type": "string", "required": True, "regex": r"/Hotels-.+?\.html"},
        "ATTRACTIONS_URL": {"type": "string", "required": True, "regex": r"/Attractions-.+?\.html"},
        "RESTAURANTS_URL": {"type": "string", "required": True, "regex": r"/Restaurants-.+?\.html"},
    }
    validator = Validator(schema, allow_unknown=True)
    assert validator.validate(result_location[0]), {"item": result_location[0], "errors": validator.errors}


@pytest.mark.asyncio
async def test_search_scraping():
    result_search = await tripadvisor.scrape_search(query="Malta", max_pages=2)
    schema = {
        "url": {"type": "string", "regex": r"https://www.tripadvisor.com/Hotel_Review-g.+?\.html"},
        "name": {"type": "string", "minlength": 5},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result_search:
        assert validator.validate(item), {"item": item, "errors": validator.errors}


@pytest.mark.asyncio
async def test_hotel_scraping():
    result_hotel = await tripadvisor.scrape_hotel(
        "https://www.tripadvisor.com/Hotel_Review-g190327-d264936-Reviews-1926_Hotel_Spa-Sliema_Island_of_Malta.html",
        max_review_pages=3,
    )
    # test hotel info
    schema = {
        "basic_data": {
            "type": "dict",
            "schema": {
                "name": {"type": "string", "required": True},
                "url": {"type": "string", "required": True},
                "image": {"type": "string", "required": True},
                "priceRange": {"type": "string", "required": True},
            }
        },
        "description": {"type": "string", "required": True},
        "reviews": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "title": {"type": "string", "required": True},
                    "tripDate": {"type": "string", "required": True}
                }
            }
        }
    }
    
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result_hotel, validator)
    assert len(result_hotel["reviews"]) >= 10
