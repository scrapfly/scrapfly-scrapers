from cerberus import Validator
import pytest

import indeed

# enable cache?
indeed.BASE_CONFIG["cache"] = True


@pytest.mark.asyncio
async def test_search_scraping():
    url = "https://www.indeed.com/jobs?q=python&l=Texas&sc=0kf%3Aattr%28DSQF7%29attr%28X62BT%29%3B&vjk=3b684083eda5dd00"
    result_search = await indeed.scrape_search(url, max_results=20)

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
    for item in result_search:
        if not validator.validate(item):
            raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.asyncio
async def test_job_scraping():
    jobs = ["4c1e2988b22fa223", "483d39cbe1b6c1fe"]
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
