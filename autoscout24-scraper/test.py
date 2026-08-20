import os

from cerberus import Validator as _Validator
import autoscout24
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
autoscout24.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )

listing_schema = {
    # without required the schema also validates an empty dict, so a page of junk passes
    "price": {"type": "dict", "required": True, "schema": {"priceFormatted": {"type": "string"}}},
    "url": {"type": "string", "required": True},
    "location": {
        "type": "dict",
        "schema": {
            "countryCode": {"type": "string"},
            "zip": {"type": "string"},
            "city": {"type": "string"},
            "street": {"type": "string", "nullable": True},
        },
        "min_presence": 0.1,
    },
    "vehicle": {
        "type": "dict",
        "schema": {
            "make": {"type": "string"},
            "model": {"type": "string"},
            "transmission": {"type": "string"},
            "fuel": {"type": "string"},
            "mileageInKm": {"type": "string"},
        },
        "min_presence": 0.1,
    },
    "tracking": {
        "type": "dict",
        "schema": {
            "firstRegistration": {"type": "string"},
        },
        "min_presence": 0.1,
    },
    "vehicleDetails": {"type": "list", "min_presence": 0.1},
}
car_details_schema = {
    "price": {"type": "dict", "required": True, "schema": {"priceFormatted": {"type": "string"}}},
    "vehicle": {"type": "dict", "min_presence": 0.1},
    "seller": {"type": "dict", "min_presence": 0.1},
    "location": {"type": "dict", "min_presence": 0.1},
}

def test_page_url():
    base = "https://www.autoscout24.com/lst/c/compact"
    assert autoscout24.change_page(base, 2) == base + "?page=2"
    # a page number already in the url is replaced instead of appended a second time
    assert autoscout24.change_page(base + "?page=2", 3) == base + "?page=3"
    # existing filters survive
    assert autoscout24.change_page(base + "?desc=0", 4) == base + "?desc=0&page=4"
    # a multi select filter repeats its key, and collapsing it would change the result set
    assert autoscout24.change_page(base + "?eq=1&eq=15&atype=C", 2) == base + "?eq=1&eq=15&atype=C&page=2"
    # AutoScout24 emits blank filters of its own, so they are kept as sent
    assert autoscout24.change_page(base + "?fregfrom=&desc=0", 2) == base + "?fregfrom=&desc=0&page=2"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_listings_scraping():
    url = "https://www.autoscout24.com/lst/c/compact"
    first_page = await autoscout24.scrape_listings(url, max_pages=1)
    assert first_page, "the first listings page returned no listings"
    results = await autoscout24.scrape_listings(url, max_pages=3)
    # a failed page 2 or 3 used to be swallowed and left one page of results behind, so the
    # expectation is relative to what one page actually holds instead of a fixed count that
    # duplicates across pages could satisfy on their own. the comparison is strict because two
    # healthy pages minus their overlap lands exactly on 2x page one when the third page dies
    assert len(results) > 2 * len(first_page)
    urls = [item["url"] for item in results if item.get("url")]
    assert len(set(urls)) == len(urls), "the same listing was returned by more than one page"
    validator = Validator(listing_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in listing_schema:
        require_min_presence(results, k, min_perc=listing_schema[k].get("min_presence", 0.1))



@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_car_details_scraping():
    listings = await autoscout24.scrape_listings(
        "https://www.autoscout24.com/lst/c/compact", max_pages=1
    )
    urls = [
        "https://www.autoscout24.com" + listing["url"]
        for listing in listings
        if listing.get("url")
    ][:5]
    assert urls, "scrape_listings returned no usable URLs to feed into scrape_car_details"
    results = await autoscout24.scrape_car_details(urls)
    assert len(results) >= 1
    # an unparsed page used to be appended as None, which cerberus reports as a DocumentError
    assert all(isinstance(result, dict) for result in results)
    validator = Validator(car_details_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in car_details_schema:
        require_min_presence(results, k, min_perc=car_details_schema[k].get("min_presence", 0.1))