import json
import os
from pathlib import Path
from cerberus import Validator as _Validator
import pytest
import google_jobs
import pprint

pp = pprint.PrettyPrinter(indent=4)

google_jobs.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for non-standard schema keys


def require_min_presence(items, key, min_perc=0.1):
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


job_result_schema = {
    "title": {"type": "string", "min_presence": 1.0},
    "company": {"type": "string", "nullable": True, "min_presence": 0.3},
    "location": {"type": "string", "nullable": True, "min_presence": 0.3},
    "posted_date": {"type": "string", "nullable": True},
    "schedule_type": {"type": "string", "nullable": True},
    "salary_range": {"type": "string", "nullable": True},
    "description": {"type": "string", "nullable": True, "min_presence": 0.3},
    "qualifications": {"type": "list"},
    "source_board": {"type": "string", "nullable": True, "min_presence": 0.3},
    "application_url": {"type": "string", "nullable": True, "min_presence": 0.3},
    "job_id": {"type": "string", "nullable": True, "min_presence": 0.3},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await google_jobs.scrape_jobs(
        query="software engineer",
        location="San Francisco, CA",
    )
    assert len(result["jobs"]) >= 5
    job_validator = Validator(job_result_schema, allow_unknown=True)
    for item in result["jobs"]:
        validate_or_fail(item, job_validator)

