from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pytest

from cerberus import Validator

import google_flights

google_flights.BASE_CONFIG["cache"] = True

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


layover_schema = {
    "airport": {"type": "string"},
    "duration_minutes": {"type": "integer"},
}

flight_result_schema = {
    "airline": {"type": "string", "nullable": True},
    "flight_number": {"type": "string", "nullable": True},
    "departure_time": {"type": "string", "nullable": True},
    "departure_airport": {"type": "string", "nullable": True},
    "arrival_time": {"type": "string", "nullable": True},
    "arrival_airport": {"type": "string", "nullable": True},
    "duration_minutes": {"type": "integer", "nullable": True},
    "stops": {"type": "integer"},
    "layovers": {
        "type": "list",
        "schema": {"type": "dict", "schema": layover_schema},
    },
    "price": {"type": "integer", "nullable": True},
    "currency": {"type": "string"},
    "price_level": {
        "type": "string",
        "nullable": True,
        "allowed": ["low", "typical", "high"],
    },
    "cabin_class": {"type": "string", "nullable": True},
    "plane_model": {"type": "string", "nullable": True},
    "co2_kg": {"type": "integer", "nullable": True},
    "co2_vs_typical": {"type": "string", "nullable": True},
    "extensions": {"type": "list", "schema": {"type": "string"}},
    "legroom": {"type": "string", "nullable": True},
    "booking_token": {"type": "string", "nullable": True},
    "type": {"type": "string", "nullable": True, "allowed": ["One way", "Round trip"]},
}

flight_search_schema = {
    "search_date": {"type": "string", "regex": r"\d{4}-\d{2}-\d{2}"},
    "route": {"type": "string", "regex": r"[A-Z]{3}-[A-Z]{3}"},
    "departure_date": {"type": "string", "regex": r"\d{4}-\d{2}-\d{2}"},
    "return_date": {
        "type": "string",
        "nullable": True,
        "regex": r"\d{4}-\d{2}-\d{2}",
    },
    "flights": {
        "type": "list",
        "schema": {"type": "dict", "schema": flight_result_schema},
    },
}


booking_option_schema = {
    "book_with": {"type": "string"},
    "airline": {"type": "boolean"},
    "airline_logos": {"type": "list", "schema": {"type": "string"}},
    "option_title": {"type": "string"},
    "price": {"type": "integer", "nullable": True},
    "price_usd": {"type": "integer", "nullable": True},
    "extensions": {"type": "list", "schema": {"type": "string"}},
    "baggage_prices": {"type": "list", "schema": {"type": "string"}},
}

booking_schema = {
    "booking_options": {
        "type": "list",
        "schema": {"type": "dict", "schema": booking_option_schema},
    },
}


def _validate_or_raise(item, schema):
    validator = Validator(schema, allow_unknown=True)
    if not validator.validate(item):
        raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_flights():
    result = await google_flights.scrape_flights(
        origin="JFK",
        destination="CDG",
        depart=TODAY,
        ret=WEEK_FROM_NOW,
        currency="USD",
    )
    _validate_or_raise(result, flight_search_schema)
    assert len(result["flights"]) >= 5

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_booking():
    result = await google_flights.scrape_flights(
        origin="JFK",
        destination="CDG",
        depart=TODAY,
        ret=WEEK_FROM_NOW,
        currency="USD",
    )
    booking_token = result["flights"][1].get("booking_token")
    booking = await google_flights.scrape_booking(
        origin="JFK",
        destination="CDG",
        depart=TODAY,
        ret=WEEK_FROM_NOW,
        currency="USD",
        booking_token=booking_token,
    )
    _validate_or_raise(booking, booking_schema)
