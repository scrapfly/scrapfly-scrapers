from datetime import datetime, timedelta

import pytest
from cerberus import Validator

import maersk


DEPARTURE_DATE = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

vessel_schema = {
    "name": {"type": "string"},
    "code": {"type": "string"},
    "flag_country": {"type": "string"},
}

port_call_schema = {
    "facility_code": {"type": "string"},
    "geo_id": {"type": "string", "nullable": True},
    "estimated_arrival": {"type": "string", "nullable": True},
    "estimated_departure": {"type": "string", "nullable": True},
    "voyage_number": {"type": "string", "nullable": True},
    "service_name": {"type": "string", "nullable": True},
    "service_code": {"type": "string", "nullable": True},
}

routing_leg_schema = {
    "carriage_type": {"type": "string"},
    "transport_mode": {"type": "string"},
    "vessel": {"type": "dict", "nullable": True, "schema": vessel_schema},
    "origin": {"type": "dict", "schema": port_call_schema},
    "destination": {"type": "dict", "schema": port_call_schema},
    "transit_time": {"type": "string", "nullable": True},
}

schedule_route_schema = {
    "route_id": {"type": "string"},
    "route_code": {"type": "string"},
    "route_direction": {"type": "string"},
    "estimated_transit_time": {"type": "string"},
    "estimated_transit_days": {"type": "integer", "nullable": True},
    "vessel_name": {"type": "string", "nullable": True},
    "origin_facility": {"type": "string", "nullable": True},
    "destination_facility": {"type": "string", "nullable": True},
    "departure_time": {"type": "string", "nullable": True},
    "arrival_time": {"type": "string", "nullable": True},
    "service_name": {"type": "string", "nullable": True},
    "voyage_number": {"type": "string", "nullable": True},
    "legs": {"type": "list", "schema": {"type": "dict", "schema": routing_leg_schema}},
}

schedule_search_schema = {
    "url": {"type": "string"},
    "from_rkst_code": {"type": "string"},
    "to_rkst_code": {"type": "string"},
    "departure_date": {"type": "string", "regex": r"\d{4}-\d{2}-\d{2}"},
    "route_count": {"type": "integer", "min": 1},
    "routes": {"type": "list", "schema": {"type": "dict", "schema": schedule_route_schema}},
}

tracking_event_schema = {
    "location": {"type": "string", "nullable": True},
    "facility": {"type": "string", "nullable": True},
    "description": {"type": "string"},
    "date": {"type": "string", "nullable": True},
    "vessel": {"type": "string", "nullable": True},
    "voyage": {"type": "string", "nullable": True},
    "is_current": {"type": "boolean"},
}

tracking_container_schema = {
    "container_number": {"type": "string", "nullable": True},
    "container_type": {"type": "string", "nullable": True},
    "last_updated": {"type": "string", "nullable": True},
    "status": {"type": "string", "nullable": True},
    "current_location": {"type": "string", "nullable": True},
    "status_date": {"type": "string", "nullable": True},
    "events": {"type": "list", "schema": {"type": "dict", "schema": tracking_event_schema}},
}

tracking_result_schema = {
    "tracking_number": {"type": "string"},
    "origin": {"type": "string", "nullable": True},
    "destination": {"type": "string", "nullable": True},
    "containers": {"type": "list", "schema": {"type": "dict", "schema": tracking_container_schema}},
}


def _validate_or_raise(item, schema):
    validator = Validator(schema, allow_unknown=True)
    if not validator.validate(item):
        raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_tracking():
    result = await maersk.scrape_tracking("269124324")
    _validate_or_raise(result, tracking_result_schema)
    


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_scrape_schedule_search():
    result = await maersk.scrape_schedule_search(
        from_location="2IW9P6J7XAW72",
        to_location="1JUKNJGWHQBNJ",
        from_rkst_code="CNSGH",
        to_rkst_code="NLROT",
        departure_date=DEPARTURE_DATE,
    )
    _validate_or_raise(result, schedule_search_schema)

