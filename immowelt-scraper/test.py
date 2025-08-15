import json
import os
from pathlib import Path
from cerberus import Validator
import immowelt
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)
immowelt.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


proeprty_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "brand": {"type": "string"},
            "id": {"type": "string"},
            "title": {"type": "string"},
            "sections": {
                "type": "dict",
                "schema": {
                    "location": {
                        "type": "dict",
                        "schema": {
                            "address": {
                                "type": "dict",
                                "schema": {
                                    "country": {"type": "string"},
                                    "city": {"type": "string"},
                                    "zipCode": {"type": "string"},
                                    "street": {"type": "string"},
                                    "district": {"type": "string"},
                                },
                            }
                        },
                    },
                    "features": {
                        "type": "dict",
                        "schema": {
                            "preview": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "icon": {"type": "string"},
                                        "value": {"type": "string"},
                                    },
                                },
                            }
                        },
                    },
                },
            },
        },
    }
}

search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "brand": {"type": "string"},
            "id": {"type": "string"},
            "status": {"type": "string"},
            "location": {
                "type": "dict",
                "schema": {
                    "address": {
                        "type": "dict",
                        "schema": {
                            "country": {"type": "string"},
                            "city": {"type": "string"},
                            "zipCode": {"type": "string"},
                            "street": {"type": "string"},
                            "district": {"type": "string"},
                        },
                    }
                },
            },
        },
    }
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    result = await immowelt.scrape_properties(
        urls=[
            "https://www.immowelt.de/expose/86611a24-fcd7-4d11-9bb6-fbdd66581c0b",
            "https://www.immowelt.de/expose/2fab259",
        ]
    )
    validator = Validator(proeprty_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 1
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / "results/properties.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await immowelt.scrape_search(
        url="https://www.immowelt.de/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08DE6345",
        max_scrape_pages=3,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in result:
        validate_or_fail(item, validator)
    assert len(result) >= 2
    if os.getenv("SAVE_TEST_RESULTS") == "true":
        result.sort(key=lambda x: x["id"])
        (Path(__file__).parent / "results/search.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
