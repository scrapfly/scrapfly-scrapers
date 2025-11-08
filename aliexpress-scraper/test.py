import json
import os
from pathlib import Path
from cerberus import Validator
import pytest

import aliexpress
import pprint

pp = pprint.PrettyPrinter(indent=4)

aliexpress.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


review_schema = {
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "buyerFeedback": {"type": "string"},
                "buyerName": {"type": "string"},
                "buyerTranslationFeedback": {"type": "string"},
                "evalDate": {"type": "string"},
                "evaluationId": {"type": "integer"},
                "logistics": {"type": "string"},
            },
        },
    },
    "evaluation_stats": {
        "type": "dict",
        "schema": {
            "evarageStar": {"type": "float"},
            "evarageStarRage": {"type": "float"},
            "fiveStarNum": {"type": "float"},
        }
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_product_scraping():
    url = "https://www.aliexpress.com/item/2255800741121659.html"
    result = await aliexpress.scrape_product(url)
    schema = {
        "info": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "productId": {"type": "integer"},
                "link": {"type": "string"},
                "media": {"type": "list", "schema": {"type": "string"}},
                "rate": {"type": "integer"},
                "reviews": {"type": "integer"},
                "soldCount": {"type": "integer"},
                "availableCount": {"type": "integer", "nullable": True},             
            }
        },
        "pricing": {
            "type": "dict",
            "schema": {
                "priceCurrency": {"type": "string"},
                "price": {"type": "float"},
                "originalPrice": {"type": "float"},
                "discount": {"type": "string"},
            }
        },
        "specifications": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "value": {"type": "string"}
                }
            }
        },
        "shipping": {
            "type": "dict",
            "schema": {
                "cost": {"type": "float"},
                "currency": {"type": "string"},
                "delivery": {"type": "string"},
            }
        },
        "faqs": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "question": {"type": "string"},
                    "answer": {"type": "string", "nullable": True}
                }
            }
        },
        "seller": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "link": {"type": "string"},
                "id": {"type": "integer"},
                "info": {
                    "type": "dict",
                    "schema": {
                        "positiveFeedback": {"type": "string"},
                        "followers": {"type": "integer"},
                    }
                }, 
            }
        },    
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/product.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    url = "https://www.aliexpress.com/w/wholesale-drills.html?catId=0&SearchText=drills"
    result = await aliexpress.scrape_search(url, max_pages=2)
    assert len(result) >= 100
    schema = {
        "id": {"type": "string"},
        "type": {"type": "string"},
        "thumbnail": {"type": "string"},
        "title": {"type": "string"},
        "currency": {"type": "string"},
        "price": {"type": "float"},
    }
    validator = Validator(schema, allow_unknown=True)
    for product in result:
        validate_or_fail(product, validator)
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/search.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    result = await aliexpress.scrape_product_reviews("1005006717259012", max_scrape_pages=2)
    assert len(result["reviews"]) > 30
    validator = Validator(review_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/reviews.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
