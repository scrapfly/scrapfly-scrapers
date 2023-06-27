"""
"""
from datetime import datetime, timedelta
import pytest
from cerberus import Validator
import bookingcom

# enable cache?
# bookingcom.BASE_CONFIG["cache"] = True
WEEK_FROM_NOW = datetime.now().strftime('%Y-%m-%d')
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
MONTH_FROM_NOW = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')


@pytest.mark.asyncio
async def test_search_scraping():
    result_search = await bookingcom.scrape_search(query="Malta", checkin="2023-06-10", checkout="2023-06-20", max_pages=2)
    assert len(result_search) >= 50
    schema = {
        "url": {"type": "string", "regex": r"https://www.booking.com/hotel/.+?\.html"},
        "name": {"type": "string", "minlength": 4},
        "score": {"type": "float", "min": 0, "max": 10, "nullable": True},
        "review_count": {"type": "integer", "min": 0, "max": 50_000, "nullable": True},
        "image": {"type": "string", "regex": r".+?/images/hotel/.+?"}
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result_search:
        if not validator.validate(item):
            raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.asyncio
async def test_hotel_scraping():
    bookingcom.BASE_CONFIG["cache"] = False
    item = await bookingcom.scrape_hotel(
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        checkin=WEEK_FROM_NOW,
        price_n_days=7,
    )
    assert item
    schema = {
        "url": {"type": "string", "regex": r"https://www.booking.com/hotel/.+?\.html"},
        "title": {"type": "string", "minlength": 4},
        "description": {"type": "string", "minlength": 200},
        "address": {"type": "string", "minlength": 50},
        "images": {"type": "list"},
        "lat": {"type": "float", "coerce": float},
        "lng": {"type": "float", "coerce": float},
        'price': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'length_of_stay': {'type': 'integer'},
                    'avg_price_raw': {'type': 'float'},
                    'price': {'type': 'float'},
                    'price_pretty': {'type': 'string'},
                    'min_length_of_stay': {'type': 'integer'},
                    'checkin': {'type': 'string'},
                    'avg_price_pretty': {'type': 'string'},
                    'available': {'type': 'integer'}
                }
            }
        },
        'features': {
            'type': 'dict',
            'valuesrules': {
                'type': 'list',
                'schema': {'type': 'string'},
            }
        },
    }
    validator = Validator(schema, allow_unknown=True)
    if not validator.validate(item):
        raise Exception({"item": item, "errors": validator.errors})
