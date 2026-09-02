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
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_scraping():
    max_review_pages = 3
    result_hotel = await tripadvisor.scrape_hotel(
        "https://www.tripadvisor.com/Hotel_Review-g190327-d264936-Reviews-1926_Hotel_Spa-Sliema_Island_of_Malta.html",
        max_review_pages=max_review_pages,
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
        # ownerResponse is absent on purpose: whether management replies is not a parser fact
    }

    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result_hotel, validator)
    reviews = result_hotel["reviews"]
    assert len(reviews) >= 10
    # max_review_pages counts the first page, 10 reviews per page
    assert len(reviews) <= max_review_pages * 10
    for k in review_schema:
        require_min_presence(reviews, k, min_perc=review_schema[k].get("min_presence", 0.1))

    require_min_presence(reviews, "title", min_perc=0.5)
    require_min_presence(reviews, "text", min_perc=0.5)
    # "Traveled as a couple", not the bare label - the value is split across nodes
    assert any(t["tripType"] and t["tripType"].strip() != "Traveled" for t in reviews)
    assert result_hotel["featues"], "no amenities parsed"
    # the hotel's reply belongs in its own field, not glued onto the guest review
    for review in reviews:
        if review["ownerResponse"]:
            assert review["ownerResponse"] not in (review["text"] or "")

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_location_data_scraping():
    result_location = await tripadvisor.scrape_location_data(query="Barcelona")
    assert len(result_location) >= 1
    require_min_presence(result_location, "localizedName", min_perc=1.0)
    require_min_presence(result_location, "placeType", min_perc=1.0)
    require_min_presence(result_location, "url", min_perc=0.9)
    names = " ".join(item.get("localizedName") or "" for item in result_location).lower()
    assert "barcelona" in names
    # one typeahead response's worth - a merged one runs to nine
    assert len(result_location) <= 12
    # the nested section links hang off the top-ranked row, whatever its placeType
    assert any(i["HOTELS_URL"] for i in result_location)

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

    urls = [item["url"] for item in result_search]
    assert len(urls) == len(set(urls))
    # one page yields ~31-33 with sponsored cards, so this only passes if page 2 landed
    assert len(result_search) >= 55


     
