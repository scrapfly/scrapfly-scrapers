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
    assert glassdoor.Url.overview("eBay-Motors-Group", "4189745") == \
        "https://www.glassdoor.com/Overview/Working-at-eBay-Motors-Group-EI_IE4189745.11,28.htm"
    assert glassdoor.Url.jobs("eBay-Motors-Group", "4189745") == \
        "https://www.glassdoor.com/Jobs/eBay-Motors-Group-Jobs-E4189745.htm"
    assert glassdoor.Url.jobs("eBay-Motors-Group", "4189745", glassdoor.Region.UNITED_STATES) == \
        "https://www.glassdoor.com/Jobs/eBay-Motors-Group-Jobs-E4189745.htm?filter.countryId=1"
    assert glassdoor.Url.reviews("eBay-Motors-Group", "4189745") == \
        "https://www.glassdoor.com/Reviews/eBay-Motors-Group-Reviews-E4189745.htm"
    assert glassdoor.Url.salaries("eBay-Motors-Group", "4189745") == \
        "https://www.glassdoor.com/Salary/eBay-Motors-Group-Salaries-E4189745.htm"
    assert glassdoor.Url.change_page("https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm", 2) == \
        "https://www.glassdoor.com/Salary/eBay-Salaries-E7853_P2.htm"
    assert glassdoor.Url.change_page("https://www.glassdoor.com/Salary/eBay-Salaries-E7853_P2.htm", 3) == \
        "https://www.glassdoor.com/Salary/eBay-Salaries-E7853_P3.htm"
    with pytest.raises(ValueError):
        glassdoor.Url.change_page("https://www.glassdoor.com/Salary/eBay-Salaries-E7853/", 2)


def test_salary_range_parsing():
    assert glassdoor.parse_salary_range("$70K - $100K") == [
        {"ident": "min", "value": 70_000.0},
        {"ident": "max", "value": 100_000.0},
    ]
    # a decimal magnitude used to be scaled textually, turning 70.5K into 70.5
    assert glassdoor.parse_salary_range("$70.5K - $100K")[0]["value"] == 70_500.0
    assert glassdoor.parse_salary_range("$1,234 - $5,678")[1]["value"] == 5_678.0
    assert glassdoor.parse_salary_range("$70K") == []
    # the range node also carries the pay period and the estimate note
    assert glassdoor.parse_salary_range("$189K - $245K /yr Glassdoor est.")[1]["value"] == 245_000.0
    # an hourly rate must not be reported next to annual salaries
    assert glassdoor.parse_salary_range("$18/hr - $25/hr") == []
    # a rating or a submission count in the same node is not a salary
    assert glassdoor.parse_salary_range("4.0 stars $70K") == []
    assert glassdoor.parse_salary_range("3 salaries $70K - $100K")[0]["value"] == 70_000.0
    assert glassdoor.parse_salary_range("") == []


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_find_companies():
    schema = {
        "name": {"type": "string", "required": True},
        "id": {"type": "integer", "required": True},
        "shortName": {"type": "string", "required": True},
        "logoURL": {"type": "string", "required": True, "nullable": True},
        "websiteURL": {"type": "string", "required": True, "nullable": True},
    }
    results = await glassdoor.find_companies("Ebay")
    validator = Validator(schema, allow_unknown=True)
    for item in results:
        validate_or_fail(item, validator)    
    assert len(results) > 5
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        results.sort(key=lambda x: x["id"])
        (Path(__file__).parent / 'results/companies.json').write_text(
            json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_job_scraping():
    url = "https://www.glassdoor.com/Jobs/eBay-Jobs-E7853.htm?filter.countryId=1"
    result = await glassdoor.scrape_jobs(url, max_pages=2)
    schema = {
        "jobTitle": {"type": "string", "required": True},
        "jobLink": {"type": "string", "required": True, "regex": r"https://www\.glassdoor\.com/.+"},
        "job_location": {"type": "string", "required": True, "nullable": True},
        "jobSalary": {"type": "string", "required": True, "nullable": True},
        "jobDate": {"type": "string", "required": True, "nullable": True},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) > 50
    # an absolute xpath inside the card loop used to give every job the same date
    assert len({item["jobDate"] for item in result}) > 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["jobLink"])
        (Path(__file__).parent / 'results/jobs.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_salary_scraping():
    url = "https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm"
    result = await glassdoor.scrape_salaries(url, max_pages=3)
    schema = {
        "salaryCount": {"type": "integer", "required": True},
        "jobTitleCount": {"type": "integer", "required": True},
        "numPages": {"type": "integer", "required": True},
        "results": {
            "type": "list",
            "required": True,
            "schema": {
                "type": "dict",
                "schema": {
                    "jobTitle": {
                        "type": "dict",
                        "required": True,
                        "schema": {
                            "text": {"type": "string", "required": True},
                        }
                    },
                    "salaryCount": {"type": "integer", "required": True},
                    "basePayStatistics": {
                        "type": "dict",
                        "required": True,
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
    items = result["results"]
    assert items, "no salary results returned"
    with_percentiles = [i for i in items if i.get("basePayStatistics", {}).get("percentiles")]
    assert len(with_percentiles) / len(items) >= 0.5, (
        f"expected at least 50% of salary results to have basePayStatistics.percentiles populated, "
        f"got {len(with_percentiles)}/{len(items)}"
    )
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/salaries.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_review_scraping():
    url = "https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm"
    result = await glassdoor.scrape_reviews(url, max_pages=3)
    schema = {
        "reviewId": {"type": "integer", "required": True},
        "ratingOverall": {"type": "integer", "required": True},
        "reviewDateTime": {"type": "string", "required": True},
        "summary": {"type": "string", "required": True},
        "pros": {"type": "string", "required": True, "nullable": True},
        "cons": {"type": "string", "required": True, "nullable": True},
        "employer": {"type": "dict", "required": True},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) > 10
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        (Path(__file__).parent / 'results/reviews.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
