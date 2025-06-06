import asyncio
import json
import os
from pathlib import Path
import pytest
import leboncoin
import pprint

from cerberus import Validator

pp = pprint.PrettyPrinter(indent=4)

# enable cache
leboncoin.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


ad_schema = {
    "list_id": {"type": "integer"},
    "first_publication_date": {"type": "string"},
    "index_date": {"type": "string"},
    "status": {"type": "string"},
    "category_id": {"type": "string"},
    "category_name": {"type": "string"},
    "subject": {"type": "string"},
    "url": {"type": "string"},
    "price": {"type": "list", "schema": {"type": "integer"}},
    "price_cents": {"type": "integer"},
    "images": {
        "type": "dict",
        "schema": {
            "thumb_url": {"type": "string"},
            "small_url": {"type": "string"},
            "nb_images": {"type": "integer"},
            "urls": {"type": "list", "schema": {"type": "string"}},
        },
    },
    "attributes": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    "location": {
        "type": "dict",
        "schema": {
            "country_id": {"type": "string"},
            "region_id": {"type": "string"},
            "region_name": {"type": "string"},
            "department_id": {"type": "string"},
            "department_name": {"type": "string"},
            "city": {"type": "string"},
        },
    },
    "owner": {
        "type": "dict",
        "schema": {
            "store_id": {"type": "string"},
            "user_id": {"type": "string"},
            "type": {"type": "string"},
            "name": {"type": "string"},
            "no_salesmen": {"type": "boolean"},
        },
    },
    "options": {
        "type": "dict",
        "schema": {
            "has_option": {"type": "boolean"},
            "booster": {"type": "boolean"},
            "photosup": {"type": "boolean"},
            "urgent": {"type": "boolean"},
            "gallery": {"type": "boolean"},
            "sub_toplist": {"type": "boolean"},
        },
    },
    "has_phone": {"type": "boolean"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await leboncoin.scrape_search(
        url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=2, scrape_all_pages=False
    )
    validator = Validator(ad_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 2
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["list_id"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_ad_scraping():
    result = []
    ads = await leboncoin.scrape_search(
        url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=1, scrape_all_pages=False
    )
    ad_urls = [i['url'] for i in ads if i and 'url' in i]

    to_scrape = [
        leboncoin.scrape_ad(url)
        for url in ad_urls[:3]
    ]
    for response in asyncio.as_completed(to_scrape):
        result.append(await response)
    validator = Validator(ad_schema, allow_unknown=True)
    for i in result:
        validate_or_fail(i, validator)
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["list_id"])
        (Path(__file__).parent / 'results/ads.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )