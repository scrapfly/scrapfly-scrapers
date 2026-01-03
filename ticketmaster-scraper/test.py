from cerberus import Validator as _Validator
import pytest

import ticketmaster
import pprint

pp = pprint.PrettyPrinter(indent=4)

ticketmaster.BASE_CONFIG["cache"] = True


# Custom Validator to support min_presence
class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


artist_schema = {
    "artist_name": {"type": "string"},
    "ratingValue": {"type": "float", "nullable": True, "min_presence": 0.5},
    "bestRating": {"type": "integer", "nullable": True, "min_presence": 0.5},
    "ratingCount": {"type": "integer", "nullable": True, "min_presence": 0.5},
    "genre": {"type": "string", "nullable": True, "min_presence": 0.5},
    "events_count": {"type": "integer"},
    "events": {
        "type": "list",
        "schema": {
            "type": "dict",
        },
    },
    "reviews": {
        "type": "list",
        "schema": {
            "type": "dict",
        },
    },
}
discovery_schema = {
    "events": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "event_name": {"type": "string"},
                "event_url": {"type": "string"},
                "date": {"type": "string"},
                "time": {"type": "string", "nullable": True},
                "venue_name": {"type": "string"},
                "venue_location": {"type": "string"},
                "ticket_url": {"type": "string"},
            },
        },
    },
    "events_count": {"type": "integer"},
    "total_count": {"type": "integer"},
}


@pytest.mark.asyncio
async def test_artist_scraping():
    urls = [
        "https://www.ticketmaster.com/imagine-dragons-tickets/artist/1435919",
        "https://www.ticketmaster.com/jeff-dunham-tickets/artist/806157",
    ]
    results = await ticketmaster.scrape_artist(urls)
    validator = Validator(artist_schema, allow_unknown=True)
    for result in results:
        validate_or_fail(result, validator)
    for k in artist_schema:
        require_min_presence(results, k, min_perc=artist_schema[k].get("min_presence", 0.1))
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_discovery_scraping():
    filters = {"classificationId": "KnvZfZ7vAvv", "startDate": "2026-01-03", "endDate": "2026-01-10"}
    result = await ticketmaster.scrape_discovery("https://www.ticketmaster.com/discover/concerts", **filters)
    validator = Validator(discovery_schema, allow_unknown=True)
    validate_or_fail(result, validator)
    assert result["events_count"] >= 1
    assert result["total_count"] >= result["events_count"]
