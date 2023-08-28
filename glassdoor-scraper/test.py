from cerberus import Validator
import pytest

import glassdoor
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache?
glassdoor.BASE_CONFIG["cache"] = True


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


@pytest.mark.asyncio
async def test_find_companies():
    results = await glassdoor.find_companies("Ebay")
    expected = [
        {
            "name": "eBay",
            "id": "7853",
            "url_overview": "https://www.glassdoor.com/Overview/Working-at-eBay-EI_IE7853.11,15.htm",
            "url_jobs": "https://www.glassdoor.com/Jobs/eBay-Jobs-E7853.htm?",
            "url_reviews": "https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm?",
            "url_salaries": "https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm?",
        },
        {
            "name": "Ebay Inc",
            "id": "7853",
            "url_overview": "https://www.glassdoor.com/Overview/Working-at-Ebay-Inc-EI_IE7853.11,19.htm",
            "url_jobs": "https://www.glassdoor.com/Jobs/Ebay-Inc-Jobs-E7853.htm?",
            "url_reviews": "https://www.glassdoor.com/Reviews/Ebay-Inc-Reviews-E7853.htm?",
            "url_salaries": "https://www.glassdoor.com/Salary/Ebay-Inc-Salaries-E7853.htm?",
        },
    ]
    for exp in expected:
        assert exp in results


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


@pytest.mark.asyncio
async def test_salary_scraping():
    url = "https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm"
    result = await glassdoor.scrape_salaries(url, max_pages=3)
    schema = {
        "salaryCount": {"type": "integer"},
        "jobTitleCount": {"type": "integer"},
        "pages": {"type": "integer"},
        "results": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "count": {"type": "integer"},
                    "minBasePay": {"type": "float"},
                    "medianBasePay": {"type": "float"},
                    "maxBasePay": {"type": "float"},
                    "totalCompMin": {"type": "float"},
                    "totalCompMax": {"type": "float"},
                    "totalCompMedian": {"type": "float"},
                    "totalAdditionalCashPayMin": {"type": "float"},
                    "totalAdditionalCashPayMax": {"type": "float"},
                    "totalAdditionalCashPayMedian": {"type": "float"},
                    "totalPayInsights": {
                        "type": "dict",
                        "schema": {
                            "isHigh": {"type": "boolean"},
                            "percentage": {"type": "integer"},
                        },
                    },
                    "jobTitle": {
                        "type": "dict",
                        "schema": {
                            "text": {"type": "string"},
                            "id": {"type": "integer"},
                        },
                    },
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)


@pytest.mark.asyncio
async def test_review_scraping():
    url = "https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm"
    result = await glassdoor.scrape_reviews(url, max_pages=3)
    schema = {
        "allReviewsCount": {"type": "integer"},
        "ratedReviewsCount": {"type": "integer"},
        "filteredReviewsCount": {"type": "integer"},
        "reviews": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "isLegal": {"type": "boolean"},
                    "featured": {"type": "boolean"},
                    "languageId": {"type": "string"},
                    "reviewId": {"type": "integer"},
                    "countHelpful": {"type": "integer"},
                    "countNotHelpful": {"type": "integer"},
                    "ratingOverall": {"type": "integer"},
                    "ratingCeo": {"nullable": True, "type": "string"},
                    "pros": {"nullable": True, "type": "string"},
                    "cons": {"nullable": True, "type": "string"},
                    "summary": {"nullable": True, "type": "string"},
                    "advice": {"nullable": True, "type": "string"},
                    "jobTitle": {
                        "type": "dict",
                        "nullable": True,
                        "schema": {
                            "text": {"type": "string"},
                            "id": {"type": "integer"},
                        },
                    },
                },
            },
        },
    }
    validator = Validator(schema, allow_unknown=True)
    validate_or_fail(result, validator)
