"""
"""
import pytest
from cerberus import Validator
import tripadvisor

# enable cache?
# tripadvisor.BASE_CONFIG["cache"] = True


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
        max_review_pages=2,
    )
    # test hotel info
    schema = {
        "name": {"type": "string", "required": True},
        "id": {"type": "integer", "required": True},
        "type": {"type": "string", "required": True, "allowed": ["T_HOTEL"]},
        "description": {"type": "string", "required": True},
        "rating": {"type": "float", "required": True, "min": 0, "max": 5},
        "rating_count": {"type": "integer", "required": True, "min": 0},
        "features": {"type": "list", "required": True, "schema": {"type": "string"}},
    }
    validator = Validator(schema)
    assert validator.validate(result_hotel["info"]), {"item": result_hotel["info"], "errors": validator.errors}

    # test reviews
    schema = {
        "id": {"type": "integer", "required": True},
        "date": {"type": "string", "required": True},  # You might want to check the date format
        "rating": {"type": "integer", "required": True, "min": 1, "max": 5},
        "title": {"type": "string", "required": True},
        "text": {"type": "string", "required": True},
        "votes": {"type": "integer", "required": True, "min": 0},
        "url": {"type": "string", "required": True},  # You can use regex to ensure valid URL
        "language": {"type": "string", "required": True},  # Consider enumerating the possible languages
        "platform": {"type": "string", "required": True},
        "author_id": {"type": "string", "required": True},
        "author_name": {"type": "string", "required": True},
        "author_username": {"type": "string", "required": True},
    }
    assert len(result_hotel["reviews"]) >= 20
    validator = Validator(schema)
    for item in result_hotel["reviews"]:
        assert validator.validate(item), {"item": item, "errors": validator.errors}

    # test prices
    price_schema = {
        "date": {"type": "string", "regex": r"\d+-\d+-\d+", "required": True},
        "priceUSD": {"type": "integer", "min": 0, "required": True},
        "priceDisplay": {"type": "string", "regex": r"\$[\d,]+", "required": True},
    }
    validator = Validator(price_schema)
    for item in result_hotel["price"]:
        assert validator.validate(item), {"item": item, "errors": validator.errors}
