import os

from cerberus import Validator as _Validator
import pytest
import copilot
import pprint

pp = pprint.PrettyPrinter(indent=4)


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for non-standard schema keys


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


source_schema = {
    "title": {"type": "string", "required": True, "minlength": 1},
    "url": {"type": "string", "required": True, "minlength": 1},
    "snippet": {"type": "string", "nullable": True},
}

copilot_schema = {
    "query": {"type": "string", "required": True, "minlength": 1},
    "answer": {"type": "string", "required": True, "minlength": 1},
    "sources": {
        "type": "list",
        "required": True,
        "schema": {"type": "dict", "schema": source_schema},
    },
}


@pytest.mark.flaky(reruns=3, reruns_delay=30)
def test_scrape_copilot():
    result = copilot.scrape_copilot(
        query="what is the best web scraping tool for 2026? list the top 10 tools",
        mode="search",
    )
    validator = Validator(copilot_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    assert len(result["answer"]) > 50
    assert len(result["sources"]) > 0
