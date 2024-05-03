from cerberus import Validator
import pytest
import walmart
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
walmart.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


product_schema = {
    "product": {
        "type": "dict",
        "schema": {
            "availabilityStatus": {"type": "string"},
            "averageRating": {"type": "float"},
            "brand": {"type": "string"},
            "shortDescription": {"type": "string"},
            "id": {"type": "string"},
            "name": {"type": "string"},
            "orderLimit": {"type": "integer"},
            "type": {"type": "string"},
        },
    },
    "reviews": {
        "type": "dict",
        "schema": {
            "averageOverallRating": {"type": "float"},
            "customerReviews": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "reviewId": {"type": "string"},
                        "rating": {"type": "float"},
                        "reviewSubmissionTime": {"type": "string"},
                        "reviewText": {"type": "string"},
                        "reviewTitle": {"type": "string", "nullable": True},
                    },
                },
            },
        },
    },
}

search_schema = {
    "id": {"type": "string"},
    "usItemId": {"type": "string"},
    "name": {"type": "string"},
    "type": {"type": "string"},
    "imageInfo": {
        "type": "dict",
        "schema": {
            "id": {"type": "string", "nullable": True},
            "name": {"type": "string", "nullable": True},
            "thumbnailUrl": {"type": "string", "nullable": True},
            "size": {"type": "string", "nullable": True},
        },
    },
    "canonicalUrl": {"type": "string"},
    "classType": {"type": "string"},
    "averageRating": {"type": "float", "nullable": True},
    "numberOfReviews": {"type": "integer", "nullable": True},
    "salesUnitType": {"type": "string"},
    "sellerId": {"type": "string"},
    "sellerName": {"type": "string"},
}


@pytest.mark.asyncio
async def test_product_scraping():
    products_data = await walmart.scrape_products(
        urls=[
            "https://www.walmart.com/ip/1736740710",
            "https://www.walmart.com/ip/715596133",
            "https://www.walmart.com/ip/496918359",
        ]
    )
    validator = Validator(product_schema, allow_unknown=True)
    for item in products_data:
        validate_or_fail(item, validator)
        assert len(product_schema) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await walmart.scrape_search(
        query="laptop", sort="best_seller", max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 40
