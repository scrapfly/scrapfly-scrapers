import pytest
import pprint as pp
from cerberus import Validator as _Validator
import tripadvisor

# enable cache?
tripadvisor.BASE_CONFIG["cache"] = False
tripadvisor.BASE_CONFIG["debug"] = True


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema

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
    }
    
    review_schema = {
        "title": {"type": "string", "nullable": True},
        "text": {"type": "string", "nullable": True},
        "rate": {"type": "float", "nullable": True},
        "tripDate": {"type": "string", "nullable": True},
        "tripType": {"type": "string", "nullable": True},
    }

    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result_hotel, validator)
    assert len(result_hotel["reviews"]) >= 10
    for k in review_schema:
        require_min_presence(result_hotel["reviews"], k, min_perc=review_schema[k].get("min_presence", 0.1))   

@pytest.mark.asyncio
async def test_location_data_scraping():
    result_location = await tripadvisor.scrape_location_data(query="Malta")
    assert len(result_location) > 10

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result_search = await tripadvisor.scrape_search(
        search_url="https://www.tripadvisor.com/Hotels-g60763-oa30-New_York_City_New_York-Hotels.html",
        max_pages=2
    )
    schema = {
        "url": {"type": "string", "regex": r"https://www.tripadvisor.com/Hotel_Review-g.+?\.html"},
        "name": {"type": "string", "minlength": 5},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result_search:
        assert validator.validate(item), {"item": item, "errors": validator.errors}


     
