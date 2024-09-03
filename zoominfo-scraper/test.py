from cerberus import Validator
import pytest
import zoominfo
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
zoominfo.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


company_schema = {
    "companyId": {"type": "string"},
    "url": {"type": "string"},
    "foundingYear": {"type": "string"},
    "totalFundingAmount": {"type": "string"},
    "isPublic": {"type": "string"},
    "name": {"type": "string"},
    "pageTitle": {"type": "string"},
    "logo": {"type": "string"},
    "numberOfEmployees": {"type": "string"},
    "fullName": {"type": "string"},
    "address": {
        "type": "dict",
        "schema": {
            "street": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
            "country": {"type": "string"},
            "zip": {"type": "string"},
        },
    },
    "techUsed": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "logo": {"type": "string"},
                "vendorFullName": {"type": "string"},
                "vendorDisplayName": {"type": "string"},
                "vendorId": {"type": "string"},
            },
        },
    },
    "description": {"type": "string"},
    "competitors": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "employees": {"type": "string"},
                "revenue": {"type": "string"},
                "logo": {"type": "string"},
                "index": {"type": "integer"},
            },
        },
    },
}


faq_schema = {
    "question": {"type": "string"},
    "answer": {"type": "string"}
}


@pytest.mark.asyncio
async def test_company_scraping():
    companies_data = await zoominfo.scrape_comapnies(
        urls=[
            "https://www.zoominfo.com/c/tesla-inc/104333869",
            "https://www.zoominfo.com/c/microsoft/24904409",
            "https://www.zoominfo.com/c/nvidia-corp/136118787",
        ]
    )
    validator = Validator(company_schema, allow_unknown=True)
    for item in companies_data:
        validate_or_fail(item, validator)
    assert len(companies_data) >= 1


@pytest.mark.asyncio
async def test_directory_scraping():
    directory_data = await zoominfo.scrape_directory(
        url="https://www.zoominfo.com/companies-search/location-usa--california--los-angeles-industry-software",
        scrape_pagination=False,
    )
    assert len(directory_data) >= 5


@pytest.mark.asyncio
async def test_faq_scraping():
    faq_data = await zoominfo.scrape_faqs(
        url="https://www.zoominfo.com/c/tesla-inc/104333869"
    )
    validator = Validator(faq_schema, allow_unknown=False)
    for item in faq_data:
        validate_or_fail(item, validator)
    assert len(faq_data) >= 10