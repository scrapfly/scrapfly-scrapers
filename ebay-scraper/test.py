from cerberus import Validator
import pytest

import ebay
import pprint
import datetime

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
ebay.BASE_CONFIG["cache"] = True


class DateTimeValidator(Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema

    def _validate_type_datetime(self, value):
        """Enables validation for `datetime.datetime` data type."""

        if not isinstance(value, datetime.datetime):
            self._error("value must be a datetime object")


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {item}\nErrors: {validator.errors}")

def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


@pytest.mark.asyncio
async def test_product_scraping():
    result = await ebay.scrape_product("https://www.ebay.com/itm/393531906094")
    schema = {
        "url": {"type": "string", "regex": "https://www.ebay.com/itm/\d+"},
        "id": {"type": "string", "regex": r"\d+"},
        "name": {"type": "string"},
        "price": {"type": "string"},
        "seller_name": {"type": "string"},
        "seller_url": {"type": "string", "regex": "https://www.ebay.com/str/.+"},
        "photos": {"type": "list", "schema": {"type": "string", "regex": "https://i.ebayimg.com/images/.+"}},
        "description_url": {"type": "string", "regex": "https://.+?.ebaydesc.com/.+"},
        "features": {"type": "dict"},
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)
    assert result['features']
    variant_schema = {
        "id": {"type": "string", "regex": r"\d+"},
        "price": {"type": "string"},
        "price_converted": {"type": "string"},
        "quantity": {"type": "integer"},
    }
    validator = Validator(variant_schema, allow_unknown=True)
    for variant in result['variants'].values():
        validate_or_fail(variant, validator)




@pytest.mark.asyncio
async def test_search_scraping():
    url = "https://www.ebay.com/sch/i.html?_from=R40&_nkw=iphone&_sacat=0&LH_TitleDesc=0&Storage%2520Capacity=16%2520GB&_dcat=9355&_ipg=240&rt=nc&LH_All=1"
    result = await ebay.scrape_search(url, max_pages=3)
    schema = {
        "url": {"type": "string", "regex": r"https://www.ebay.com/itm/\d+"},
        # note: could be placeholder - https://secureir.ebaystatic.com/pictures/aw/pics/stockimage1.jpg 
        "photo": {"type": "string", "regex": r"https://i.ebayimg.com/thumbs/images/.+?|https://.+ebaystatic.com/.+", "nullable": True},
        "title": {"type": "string"},
        "location": {"type": "string", "min_presence": 0.02},
        "condition": {"type": "string"},
        "subtitles": {"type": "list", "schema": {"type": "string"}},
        "shipping": {"type": "float", "nullable": True},
        "rating": {"type": "float", "nullable": True, "min": 0, "max": 5},
        "rating_count": {"type": "integer", "min": 0, "max": 10_000, "nullable": True},
        "auction_end": {"type": "datetime", "nullable": True},
        "bids": {"type": "integer", "nullable": True, "min_presence": 0.05},
        "price": {"type": "string", "regex": r"\$[\d,\.]+", "nullable": True},
    }
    validator = DateTimeValidator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    for k in schema:
        require_min_presence(result, k, min_perc=schema[k].get("min_presence", 0.1))
