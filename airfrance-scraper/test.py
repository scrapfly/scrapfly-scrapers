import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from cerberus import Validator

import airfrance

DEPARTURE = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
RETURN = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

layover_schema = {
    "airport": {"type": "string"},
    "duration_minutes": {"type": "integer", "nullable": True},
}

flight_schema = {
    "airline": {"type": "string"},
    "flight_number": {"type": "string"},
    "departure_time": {"type": "string"},
    "departure_airport": {"type": "string"},
    "arrival_time": {"type": "string"},
    "arrival_airport": {"type": "string"},
    "arrives_next_days": {"type": "integer"},
    "duration_minutes": {"type": "integer"},
    "stops": {"type": "integer"},
    "layovers": {"type": "list", "schema": {"type": "dict", "schema": layover_schema}},
    "price": {"type": "string"},
    "currency": {"type": "string"},
    "cabin_class": {"type": "string"},
    "seats_available": {"type": "integer", "nullable": True},
    "is_promo": {"type": "boolean"},
    "promo_title": {"type": "string", "nullable": True},
    "has_special_fare": {"type": "boolean"},
    "seat_map_eligible": {"type": "boolean"},
    "plane_model": {"type": "string"},
    "co2_kg": {"type": "integer"},
    "airport_change_warning": {"type": "list", "nullable": True, "schema": {"type": "string"}},
}


def _validate_or_raise(item, schema):
    validator = Validator(schema, allow_unknown=False)
    if not validator.validate(item):
        raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.flaky(reruns=3, reruns_delay=30)
def test_scrape_flights():
    results = airfrance.scrape_flights(
        origin="PAR",
        destination="TYO",
        departure_date=DEPARTURE,
        return_date=RETURN,
    )
    assert len(results) >= 2
    for flight in results:
        _validate_or_raise(flight, flight_schema)

