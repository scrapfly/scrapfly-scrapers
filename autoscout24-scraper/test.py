from cerberus import Validator as _Validator
import autoscout24
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
autoscout24.BASE_CONFIG["cache"] = True


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )

listing_schema = {
    "price": {"type": "dict", "schema": {"priceFormatted": {"type": "string"}}},
    "url": {"type": "string"},
    "location": {
        "type": "dict",
        "schema": {
            "countryCode": {"type": "string"},
            "zip": {"type": "string"},
            "city": {"type": "string"},
            "street": {"type": "string", "nullable": True},
        },
        "min_presence": 0.9,
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
        "min_presence": 0.9,
    },
    "tracking": {
        "type": "dict",
        "schema": {
            "firstRegistration": {"type": "string"},
        },
        "min_presence": 0.9,
    },
    "vehicleDetails": {"type": "list", "min_presence": 0.9},
}
car_details_schema = {
    "price": {"type": "dict", "schema": {"priceFormatted": {"type": "string"}}},
    "vehicle": {"type": "dict", "min_presence": 0.95},
    "seller": {"type": "dict", "min_presence": 0.9},
    "location": {"type": "dict", "min_presence": 0.9},
}

@pytest.mark.asyncio
async def test_listings_scraping():
    url = "https://www.autoscout24.com/lst/c/compact"
    results = await autoscout24.scrape_listings(url, max_pages=3)
    assert len(results) >= 30
    validator = Validator(listing_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in listing_schema:
        require_min_presence(results, k, min_perc=listing_schema[k].get("min_presence", 0.1))



@pytest.mark.asyncio
async def test_car_details_scraping():
    urls = [
        "https://www.autoscout24.com/offers/bmw-116-116i-gasoline-black-23ff7f14-f5df-4bbc-a12f-b8d07bf9b870",
        "https://www.autoscout24.com/offers/fiat-500-1-2-sport-pano-gasoline-red-516f93af-fbcc-4614-a69e-3369f3334ad1",
        "https://www.autoscout24.com/offers/mercedes-benz-a-160-blueefficiency-classic-gasoline-grey-527717a0-2f01-4264-b9a5-bd7a69a27993",
    ]
    results = await autoscout24.scrape_car_details(urls)
    assert len(results) >= 1
    validator = Validator(car_details_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in car_details_schema:
        require_min_presence(results, k, min_perc=car_details_schema[k].get("min_presence", 0.1))