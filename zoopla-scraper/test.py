from cerberus import Validator
import zoopla
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
zoopla.BASE_CONFIG["cache"] = False

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


search_schema = {
    "price": {"type": "integer", "nullable": True},
    "priceCurrency": {"type": "string"},
    "url": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
    "address": {"type": "string", "nullable": True},
    "squareFt": {"type": "integer", "nullable": True},
    "numBathrooms": {"type": "integer", "nullable": True},
    "numBedrooms": {"type": "integer", "nullable": True},
    "numLivingRoom": {"type": "integer", "nullable": True},
    "description": {"type": "string", "nullable": True},
    "justAdded": {"type": "boolean", "nullable": True},
    "agency": {"type": "string", "nullable": True}
}

property_schema = {
    "id": {"type": "integer"},
    "url": {"type": "string"},
    "title": {"type": "string"},
    "address": {"type": "string"},
    "price": {
        "type": "dict",
        "schema": {
            "amount": {"type": "integer"},
            "currency": {"type": "string"},
        },
    },
    "gallery": {
        "type": "list",
        "schema": {
            "type": "string",
        },
    },
    "floorArea": {"type": "string", "nullable": True},
    "numOfReceptions": {"type": "integer", "nullable": True},
    "numOfBathrooms": {"type": "integer", "nullable": True},
    "numOfBedrooms": {"type": "integer", "nullable": True},
    "propertyTags": {
        "type": "list",
        "schema": {
            "type": "string",
        },
    },
    "propertyInfo": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "label": {"type": "string", "nullable": True},
                "value": {"type": "string", "nullable": True}
            }
        }
    },
    "propertyDescription": {
        "type": "list",
        "schema": {
            "type": "string",
        },
    },    
    "coordinates": {
        "type": "dict",
        "schema": {
            "googleMapeSource": {"type": "string", "nullable": True},
            "latitude": {"type": "float", "nullable": True},
            "longitude": {"type": "float", "nullable": True},
        }
    },
    "nearby": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "title": {"type": "string", "nullable": True},
                "distance": {"type": "float", "nullable": True},
                "unit": {"type": "string", "nullable": True},
            }
        }
    },
    "agent": {
        "type": "dict",
        "schema": {
            "name": {"type": "string"},
            "logo": {"type": "string"},
            "url": {"type": "string"},
        }
    }
}

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await zoopla.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=2,
        location_slug="london/islington",
        query_type= "to-rent"
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)

    for k in search_schema:
        require_min_presence(search_data, k, min_perc=search_schema[k].get("min_presence", 0.1))  

    assert len(search_data) >= 25


@pytest.mark.asyncio
# @pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_properties_scraping():
    properties_data = await zoopla.scrape_properties(
        urls=[
            "https://www.zoopla.co.uk/new-homes/details/67644732/",
            "https://www.zoopla.co.uk/new-homes/details/66702316/",
            "https://www.zoopla.co.uk/new-homes/details/67644753/"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)

    for k in property_schema:
        require_min_presence(properties_data, k, min_perc=property_schema[k].get("min_presence", 0.1))

    assert len(properties_data) >= 1
