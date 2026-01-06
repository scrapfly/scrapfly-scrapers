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
    "title": {"type": "string"},
    "price": {"type": "string"},
    "url": {"type": "string"},
    "mileage": {"type": "string", "nullable": True, "min_presence": 0.5},
    "year": {"type": "string", "nullable": True, "min_presence": 0.5},
    "fuel_type": {"type": "string", "nullable": True, "min_presence": 0.5},
    "transmission": {"type": "string", "nullable": True, "min_presence": 0.3},
    "power": {"type": "string", "nullable": True, "min_presence": 0.3},
    "color": {"type": "string", "nullable": True, "min_presence": 0.3},
    "body_type": {"type": "string", "nullable": True, "min_presence": 0.3},
    "doors": {"type": "string", "nullable": True, "min_presence": 0.2},
    "seats": {"type": "string", "nullable": True, "min_presence": 0.2},
    "co2_emission": {"type": "string", "nullable": True, "min_presence": 0.1},
    "features": {"type": "list", "schema": {"type": "string"}},
    "seller": {"type": "dict", "schema": {
        "name": {"type": "string"},
        "location": {"type": "string"},
    }},
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
        "https://www.autoscout24.com/offers/peugeot-207-filou-motorschaden-gasoline-0b93e496-1f1b-475d-a972-fa4bd490031d",
    ]
    results = await autoscout24.scrape_car_details(urls)
    assert len(results) >= 1
    validator = Validator(car_details_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in car_details_schema:
        require_min_presence(results, k, min_perc=car_details_schema[k].get("min_presence", 0.1))

