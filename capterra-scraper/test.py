import pytest
from cerberus import Validator
import pprint

import capterra

pp = pprint.PrettyPrinter(indent=4)



def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


category_product_schema = {
    "product_id": {"type": "string"},
    "name": {"type": "string"},
    "url": {"type": "string"},
    "reviews_url": {"type": "string"},
    "logo": {"type": "string", "nullable": True},
    "rating": {"type": "float", "nullable": True},
    "review_count": {"type": "integer", "nullable": True},
    "rating_breakdown": {"type": "dict"},
    "description": {"type": "string", "nullable": True},
    "features": {"type": "list"},
}

review_schema = {
    "title": {"type": "string"},
    "date": {"type": "string", "nullable": True},
    "reviewer_name": {"type": "string"},
    "reviewer_role": {"type": "string", "nullable": True},
    "reviewer_industry": {"type": "string", "nullable": True},
    "reviewer_usage_duration": {"type": "string", "nullable": True},
    "reviewer_avatar": {"type": "string", "nullable": True},
    "ratings": {
        "type": "dict",
        "schema": {
            "overall": {"type": "float", "nullable": True},
            "ease_of_use": {"type": "float", "nullable": True},
            "features": {"type": "float", "nullable": True},
            "value_for_money": {"type": "float", "nullable": True},
            "customer_service": {"type": "float", "nullable": True},
            "likelihood_to_recommend": {"type": "integer", "nullable": True},
        },
    },
    "review_body": {"type": "string", "nullable": True},
    "pros": {"type": "string", "nullable": True},
    "cons": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_category_scraping():
    category_data = await capterra.scrape_category(
        category="scheduling-software",
        max_pages=1,
    )
    validator = Validator(category_product_schema, allow_unknown=True)
    for item in category_data:
        validate_or_fail(item, validator)
    assert len(category_data) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    reviews_data = await capterra.scrape_reviews(
        url="https://www.capterra.com/p/211559/Trello/reviews/",
        max_review_pages=1,
    )
    validator = Validator(review_schema, allow_unknown=True)
    for item in reviews_data:
        validate_or_fail(item, validator)
    assert len(reviews_data) >= 5
