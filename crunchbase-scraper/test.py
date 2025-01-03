from cerberus import Validator
import pytest

import crunchbase
import pprint

pp = pprint.PrettyPrinter(indent=2)

# enable cache?
crunchbase.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_company_scraping():
    url = "https://www.crunchbase.com/organization/tesla-motors/people"
    result = await crunchbase.scrape_company(url)
    schema = {
        "employees": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "linkedin": {"type": "string"},
                    "job_departments": {"type": "list", "schema": {"type": "string"}},
                    "job_levels": {"type": "list", "schema": {"type": "string"}},
                },
            },
        },
        "organization": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "linkedin": {"type": "string", "nullable": True, "regex": r"https*://www.linkedin.com/company/.+?"},
                "twitter": {"type": "string", "nullable": True, "regex": r"https://(?:www\.)?x.com/.+?"},
                "facebook": {"type": "string", "nullable": True, "regex": r"https://www.facebook.com/.+?"},
                "email": {"type": "string", "nullable": True, "regex": r".+?@.+?"},
                "phone": {"type": "string", "nullable": True, "regex": r"^\+?[\d\s-]+$"},
                "website": {"type": "string", "nullable": True, "regex": r"https*://.+?"},
                "categories": {"type": "list", "schema": {"type": "string"}},
                "investments": {
                    "type": "list",
                    "schema": {
                        "type": "dict",
                        "schema": {
                            "name": {"type": "string"},
                            "raised": {"type": "integer"},
                            "organization": {"type": "string"},
                        },
                    },
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_person_scraping():
    url = "https://www.crunchbase.com/person/danny-hayes-8e1b"
    result = await crunchbase.scrape_person(url)
    schema = {
        "name": {"type": "string"},
        "title": {"type": "string"},
        "type": {"type": "string"},
        "gender": {"type": "string"},
        "linkedin": {"type": "string", "nullable": True, "regex": r"https*://www.linkedin.com/in/.+?"},
        "twitter": {"type": "string", "nullable": True, "regex": r"https://twitter.com/.+?"},
        "facebook": {"type": "string", "nullable": True, "regex": r"https://www.facebook.com/.+?"},
        "description": {"type": "string"},
        "location_groups": {"type": "list", "schema": {"type": "string"}},
        "location": {"type": "list", "schema": {"type": "string"}},
        "education": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "school": {"type": "string"},
                    "started_on": {"type": "string"},
                    "completed_on": {"type": "string"},
                    "type": {"type": "string", "nullable": True},
                },
            },
        },
        "timeline": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "title": {"type": "string", "nullable": True},
                    "author": {"type": "string", "nullable": True},
                    "publisher": {"type": "string", "nullable": True},
                    "url": {"type": "string", "nullable": True},
                    "date": {"type": "string", "nullable": True},
                    "type": {"type": "string", "nullable": True},
                },
            },
        },
        "investments": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "raised": {"type": "integer"},
                    "organization": {"type": "string"},
                },
            },
        },
        "investing_overview": {
            "type": "dict",
            "schema": {
                "num_current_advisor_jobs": {"type": "integer"},
                "num_founded_organizations": {"type": "integer"},
                "num_portfolio_organizations": {"type": "integer"},
                "rank_principal_investor": {"type": "integer"},
                "num_exits": {"type": "integer"},
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)
