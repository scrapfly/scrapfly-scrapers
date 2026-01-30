import json
import os
from pathlib import Path
from cerberus import Validator
import pytest

import glassdoor
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
glassdoor.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def test_glassdoor_url():
    expected = "https://www.glassdoor.com/Overview/Working-at-eBay-Motors-Group-EI_IE4189745.11,28.htm"
    glassdoor.Url.overview("eBay-Motors-Group", "4189745") == expected
    expected = "https://www.glassdoor.com/Jobs/eBay-Motors-Group-Jobs-E4189745.htm"
    glassdoor.Url.jobs("eBay-Motors-Group", "4189745") == expected
    expected = "https://www.glassdoor.com/Jobs/eBay-Motors-Group-Jobs-E4189745.htm?filter.countryId=1"
    glassdoor.Url.jobs("eBay-Motors-Group", "4189745", glassdoor.Region.UNITED_STATES) == expected
    expected = "https://www.glassdoor.com/Reviews/eBay-Motors-Group-Reviews-E4189745.htm"
    glassdoor.Url.reviews("eBay-Motors-Group", "4189745") == expected
    expected = "https://www.glassdoor.com/Salaries/eBay-Motors-Group-Salaries-E4189745.htm"
    glassdoor.Url.salaries("eBay-Motors-Group", "4189745") == expected


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def find_errors(errors, prefix=""):
    for key, value in errors.items():
        if isinstance(value, dict):
            yield from find_errors(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_find_companies():
    schema = {
        "name": {"type": "string"},
        "id": {"type": "integer"},
        "logoURL": {"type": "string", "nullable": True},
        "employerId": {"type": "integer", "nullable": True},
        "employerName": {"type": "string", "nullable": True},        
    }
    results = await glassdoor.find_companies("Ebay")
    validator = Validator(schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)    
    assert len(results) > 5
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        results.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(results, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_job_scraping():
    url = "https://www.glassdoor.com/Jobs/eBay-Jobs-E7853.htm?filter.countryId=1"
    result = await glassdoor.scrape_jobs(url, max_pages=2)
    schema = {
        "jobTitleText": {"type": "string"},
        "jobLink": {"type": "string"},
        "payCurrency": {"type": "string"},
        "locationName": {"type": "string"},
        "jobCountryId": {"type": "integer"},
        "ageInDays": {"type": "integer"},
        "employer": {
            "type": "dict",
            "schema": {
                "id": {"type": "integer"},
                "shortName": {"type": "string"},
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) > 50
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["jobLink"])
        (Path(__file__).parent / 'results/jobs.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_salary_scraping():
    url = "https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm"
    result = await glassdoor.scrape_salaries(url, max_pages=3)
    schema = {
        "salaryCount": {"type": "integer"},
        "jobTitleCount": {"type": "integer"},
        "numPages": {"type": "integer"},
        "results": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "currency": {
                        "type": "dict",
                        "schema": {
                            "__typename": {"type": "string"},
                            "code": {"type": "string"},
                        }
                    },
                    "jobTitle": {
                        "type": "dict",
                        "schema": {
                            "id": {"type": "integer"},
                            "text": {"type": "string"},
                        }
                    },
                    "salaryCount": {"type": "integer"},
                    "basePayStatistics": {
                        "type": "dict",
                        "schema": {
                            "percentiles": {
                                "type": "list",  # This ensures the validator expects a list
                                "schema": {
                                    "type": "dict",  # Each item in the list is a dictionary
                                    "schema": {
                                        "ident": {"type": "string"},
                                        "value": {"type": "float"},
                                    }
                                }
                            }
                        }
                    },
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/salaries.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    url = "https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm"
    result = await glassdoor.scrape_reviews(url, max_pages=3)
    assert len(result) > 10
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/reviews.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
