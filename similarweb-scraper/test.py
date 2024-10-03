from cerberus import Validator as _Validator
import pytest
import similarweb
import pprint

pp = pprint.PrettyPrinter(indent=4)

similarweb.BASE_CONFIG["cache"] = False

class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


website_schema = {
    "interests": {
        "type": "dict",
        "schema": {
            "interestedWebsitesTotalCount": {"type": "integer"},
            "topInterestedCategories": {
                "type": "list",
                "schema": {"type": "string"}
            }
        }
    },
    "competitors": {
        "type": "dict",
        "schema": {
            "topSimilarityCompetitors": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "domain": {"type": "string"},
                        "icon": {"type": "string"},
                        "visitsTotalCount": {"type": "integer"},
                        "categoryId": {"type": "string"},
                        "categoryRank": {"type": "integer", "nullable": True},
                        "affinity": {"type": "float"},
                        "isDataFromGa": {"type": "boolean"},
                    }
                }
            }
        }
    },
    "searchesSource": {
        "type": "dict",
        "schema": {
            "organicSearchShare": {"type": "float"},
            "paidSearchShare": {"type": "float"},
            "keywordsTotalCount": {"type": "float"},
        }
    }
}

website_compare_schema = {
    "twitter.com": {
        "type": "dict",
        "schema": {
            "overview": {
                "type": "dict",
                "schema": {
                    "description": {"type": "string"},
                    "countryAlpha2Code": {"type": "string"},
                    "globalRank": {"type": "integer"},
                    "globalRankChange": {"type": "integer"},
                    "countryRank": {"type": "integer"},
                    "countryRankChange": {"type": "integer"},
                    "categoryRank": {"type": "integer"},
                }
            }
        }
    }
}

trends_schema = {
    "name": {"type": "string"},
    "url": {"type": "string"},
    "list": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "@type": {"type": "string"},
                "position": {"type": "integer"},
                "item": {
                    "type": "dict",
                    "schema": {
                        "@type": {"type": "string"},
                        "name": {"type": "string"},
                        "url": {"type": "string"}
                    }
                }
            }
        }
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_website_scraping():
    website_data = await similarweb.scrape_website(
        domains=["google.com", "twitter.com", "youtube.com"]
    )
    validator = Validator(website_schema, allow_unknown=True)
    for item in website_data:
        validate_or_fail(item, validator)
    assert len(website_data) == 3


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_website_compare_scraping():
    comparing_data = await similarweb.scrape_website_compare(
        first_domain="twitter.com",
        second_domain="instagram.com"
    )
    validator = Validator(website_compare_schema, allow_unknown=True)
    validate_or_fail(comparing_data, validator)
    assert len(comparing_data["twitter.com"]["overview"]) >= 10


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_trend_scraping():
    trending_data = await similarweb.scrape_trendings(
        urls=[
            "https://www.similarweb.com/top-websites/computers-electronics-and-technology/programming-and-developer-software/",
            "https://www.similarweb.com/top-websites/computers-electronics-and-technology/social-networks-and-online-communities/",
            "https://www.similarweb.com/top-websites/finance/investing/"
        ]
    )
    validator = Validator(trends_schema, allow_unknown=True)
    for item in trending_data:
        validate_or_fail(item, validator)
    assert len(trending_data) == 3
