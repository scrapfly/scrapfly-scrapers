from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pytest

from cerberus import Validator

import bookingcom

# enable cache?
# bookingcom.BASE_CONFIG["cache"] = True
NOW = datetime.now().strftime('%Y-%m-%d')
TODAY = datetime.now().strftime('%Y-%m-%d')
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
MONTH_FROM_NOW = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
bookingcom.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result_search = await bookingcom.scrape_search(
        query="Malta",
        checkin=TODAY,
        checkout=WEEK_FROM_NOW,
        max_pages=3
    )
    assert len(result_search) >= 50
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(result_search, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_scraping():
    bookingcom.BASE_CONFIG["cache"] = False
    urls = [
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        "https://www.booking.com/hotel/fr/avenir-jonquiere.en-gb.html",
        "https://www.booking.com/hotel/fr/hotelkyriaditaliegobelins.en-gb.html"
    ]
    results = []
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
        results.append(item)

    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/hotel.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_hotel_reviews_scraping():
    reviews_data = await bookingcom.scrape_hotel_reviews(
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        max_pages=3
    )
    assert len(reviews_data) > 20
    validation_schema = {
        "textDetails": {
            "type": "dict",
            "schema": {
                "positiveText": {"type": "string", "nullable": True},
                "negativeText": {"type": "string", "nullable": True},
            }
        }
    }
    validator = Validator(validation_schema, allow_unknown=True)
    for review in reviews_data:
        if not validator.validate(review):
            raise Exception({"review": review, "errors": validator.errors})