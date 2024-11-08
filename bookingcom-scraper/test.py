"""
"""
from datetime import datetime, timedelta
import pytest
from cerberus import Validator
import bookingcom

# enable cache?
# bookingcom.BASE_CONFIG["cache"] = True
NOW = datetime.now().strftime('%Y-%m-%d')
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
MONTH_FROM_NOW = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
bookingcom.BASE_CONFIG["debug"] = True


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result_search = await bookingcom.scrape_search(query="Malta", checkin="2023-06-10", checkout="2023-06-20", max_pages=3)
    assert len(result_search) >= 50


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_scraping():
    bookingcom.BASE_CONFIG["cache"] = False
    urls = [
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        "https://www.booking.com/hotel/fr/avenir-jonquiere.en-gb.html",
        "https://www.booking.com/hotel/fr/hotelkyriaditaliegobelins.en-gb.html"
    ]
    for url in urls:
        item = await bookingcom.scrape_hotel(
            url,
            checkin=NOW,
        )
        assert item
        schema = {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "address": {"type": "string"},
            "images": {"type": "list"},
            "lat": {"type": "float", "coerce": float},
            "lng": {"type": "float", "coerce": float},
            'price': {
                'type': 'list',
                'schema': {
                    'type': 'dict',
                    'schema': {
                        'available': {'type': 'boolean'},
                        'checkin': {'type': 'string', 'regex': r"[0-9]{4}-[0-9]{2}-[0-9]{2}"},
                        'minLengthOfStay': {'type': 'integer'},
                        'avgPriceFormatted': {'type': 'string'},
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
