import json
import os
from pathlib import Path
from cerberus import Validator
import pytest

import indeed

# enable cache?
indeed.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    url = "https://www.indeed.com/jobs?q=python&l=Texas"
    result = await indeed.scrape_search(url, max_results=10)

    schema = {
        "jobkey": {"type": "string"},
        "jobLocationCity": {"type": "string"},
        "jobLocationState": {"type": "string"},
        "company": {"type": "string"},
        "companyRating": {"type": "float"},
        "companyReviewCount": {"type": "integer"},
        "displayTitle": {"type": "string"},
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result:
        if not validator.validate(item):
            raise Exception({"item": item, "errors": validator.errors})
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["jobkey"])
        (Path(__file__).parent / 'results/search.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_job_scraping():
    jobs = ["9100493864fe1d6e", "5361f22542fe4a95"]
    result = await indeed.scrape_jobs(jobs)
    assert len(result) == 2
    for r in result:
        schema = {
            "jobTitle": {"type": "string"},
            "subtitle": {"type": "string"},
            "jobType": {"type": "string"},
            "companyName": {"type": "string"},
            "description": {"type": "string", "minlength": 100},
            "companyImagesModel": {
                "type": "dict",
                "schema": {
                    "logoUrl": {"type": "string", "nullable": True},
                },
            },
            "companyReviewModel": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "desktopCompanyLink": {"type": "string"},
                    "companyName": {"type": "string"},
                    "ratingsModel": {
                        "type": "dict",
                        "schema": {
                            "count": {"type": "integer"},
                            "rating": {"type": "float"},
                        },
                    },
                },
            },
        }
        validator = Validator(schema, allow_unknown=True)
        if not validator.validate(r):
            raise Exception({"item": r, "errors": validator.errors})
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["jobTitle"])
        (Path(__file__).parent / 'results/jobs.json').write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
