from cerberus import Validator
import pytest
import trustpilot
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
trustpilot.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


company_schema = {
    "pageUrl": {"type": "string"},
    "companyDetails": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "displayName": {"type": "string"},
            "identifyingName": {"type": "string"},
            "numberOfReviews": {"type": "integer"},
            "trustScore": {"type": "float"},
            "websiteUrl": {"type": "string"},
            "websiteTitle": {"type": "string"},
            "profileImageUrl": {"type": "string"},
            "stars": {"type": "integer"},
        },
    },
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "filtered": {"type": "boolean"},
                "pending": {"type": "boolean"},
                "text": {"type": "string"},
                "rating": {"type": "integer"},
                "title": {"type": "string"},
                "likes": {"type": "integer"},
            },
        },
    },
}

search_schema = {
    "businessUnitId": {"type": "string"},
    "stars": {"type": "integer"},
    "identifyingName": {"type": "string"},
    "displayName": {"type": "string"},
    "logoUrl": {"type": "string"},
    "numberOfReviews": {"type": "integer"},
    "trustScore": {"type": "float"},
    "location": {
        "type": "dict",
        "schema": {
            "address": {"type": "string", "nullable": True},
            "city": {"type": "string", "nullable": True},
            "zipCode": {"type": "string", "nullable": True},
            "country": {"type": "string", "nullable": True},
        },
    },
    "contact": {
        "type": "dict",
        "schema": {
            "website": {"type": "string", "nullable": True},
            "email": {"type": "string", "nullable": True},
            "phone": {"type": "string", "nullable": True},
        },
    },
}

review_schema = {
    "id": {"type": "string"},
    "text": {"type": "string"},
    "rating": {"type": "integer"},
    "title": {"type": "string"},
    "likes": {"type": "integer"},
    "consumer": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "displayName": {"type": "string"},
            "imageUrl": {"type": "string", "nullable": True},
            "numberOfReviews": {"type": "integer"},
            "countryCode": {"type": "string"},
        },
    },
}


@pytest.mark.asyncio
async def test_company_scraping():
    companies_data = await trustpilot.scrape_company(
        urls=[
            "https://www.trustpilot.com/review/www.flashbay.com",
            "https://www.trustpilot.com/review/iggm.com",
            "https://www.trustpilot.com/review/www.bhphotovideo.com",
        ]
    )
    validator = Validator(company_schema, allow_unknown=True)
    for item in companies_data:
        validate_or_fail(item, validator)
    assert len(companies_data) >= 2


@pytest.mark.asyncio
async def test_search_scraping():   
    search_data = await trustpilot.scrape_search(
        url="https://www.trustpilot.com/categories/electronics_technology", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 30


@pytest.mark.asyncio
async def test_review_scraping():
    reviews_data = await trustpilot.scrape_reviews(
        url="https://www.trustpilot.com/review/www.bhphotovideo.com",
        max_pages=3,
    )
    validator = Validator(review_schema, allow_unknown=True)
    for item in reviews_data:
        validate_or_fail(item, validator)
    assert len(reviews_data) >= 30