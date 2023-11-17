from cerberus import Validator
import redfin
import pytest
import pprint

redfin.BASE_CONFIG["cache"] = True

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_sale_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "address": {"type": "string"},
            "description": {"type": "string"},
            "price": {"type": "string"},
            "estimatedMonthlyPrice": {"type": "string"},
            "propertyUrl": {"type": "string"},
            "attachments": {"type": "list", "schema": {"type": "string"}},
            "details": {"type": "list", "schema": {"type": "string"}},
            "features": {
                "type": "dict",
                "schema": {
                    "Parking Information": {
                        "type": "list",
                        "schema": {"type": "string"},
                    }
                },
            },
        },
    }
}

property_rent_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "rentalId": {"type": "string"},
            "unitTypesByBedroom": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "bedroomTitle": {"type": "string"},
                        "availableUnitTypes": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "unitTypeId": {"type": "string"},
                                    "units": {
                                        "type": "list",
                                        "schema": {
                                            "type": "dict",
                                            "schema": {
                                                "unitId": {"type": "string"},
                                                "bedrooms": {"type": "integer"},
                                                "depositCurrency": {"type": "string"},
                                                "fullBaths": {"type": "integer"},
                                                "halfBaths": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "rentCurrency": {"type": "string"},
                                                "rentPrice": {"type": "integer"},
                                                "sqft": {"type": "string"},
                                                "status": {"type": "string"},
                                            },
                                        },
                                    },
                                    "availableUnits": {"type": "integer"},
                                    "bedrooms": {"type": "integer"},
                                    "fullBaths": {"type": "integer"},
                                    "halfBaths": {"type": "integer"},
                                    "name": {"type": "string"},
                                    "rentPriceMax": {"type": "integer"},
                                    "rentPriceMin": {"type": "integer"},
                                    "sqftMax": {"type": "integer"},
                                    "sqftMin": {"type": "integer"},
                                    "status": {"type": "string"},
                                    "style": {"type": "string"},
                                    "totalUnits": {"type": "integer"},
                                },
                            },
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
            "mlsId": {
                "type": "dict",
                "schema": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                },
            },
            "price": {
                "type": "dict",
                "schema": {
                    "value": {"type": "integer"},
                    "level": {"type": "integer"},
                },
            },
            "beds": {"type": "integer"},
            "baths": {"type": "integer"},
            "fullBaths": {"type": "integer"},
            "location": {
                "type": "dict",
                "schema": {
                    "value": {"type": "string"},
                    "level": {"type": "integer"},
                },
            },
            "streetLine": {
                "type": "dict",
                "schema": {
                    "value": {"type": "string"},
                    "level": {"type": "integer"},
                },
            },
            "countryCode": {"type": "string"},
            "showAddressOnMap": {"type": "boolean"},
            "soldDate": {"type": "integer"},
            "searchStatus": {"type": "integer"},
            "propertyType": {"type": "integer"},
            "uiPropertyType": {"type": "integer"},
            "listingType": {"type": "integer"},
            "propertyId": {"type": "integer"},
            "listingId": {"type": "integer"},
            "dataSourceId": {"type": "integer"},
            "marketId": {"type": "integer"},
        },
    }
}


@pytest.mark.asyncio
async def test_properties_for_sale_scraping():
    properties_sale_data = await redfin.scrape_property_for_sale(
        urls=[
            "https://www.redfin.com/WA/Seattle/506-E-Howell-St-98122/unit-W303/home/46456",
            "https://www.redfin.com/WA/Seattle/1105-Spring-St-98104/unit-405/home/12305595",
        ]
    )
    validator = Validator(property_sale_schema, allow_unknown=True)
    for item in properties_sale_data:
        validate_or_fail(item, validator)
    assert len(properties_sale_data) >= 1


@pytest.mark.asyncio
async def test_properties_for_rent_scraping():
    properties_rent_data = await redfin.scrape_property_for_rent(
        urls=[
            "https://www.redfin.com/WA/Seattle/Onni-South-Lake-Union/apartment/147020546",
            "https://www.redfin.com/WA/Seattle/The-Ivey-on-Boren/apartment/146904423",
        ]
    )
    validator = Validator(property_rent_schema, allow_unknown=True)
    for item in properties_rent_data:
        validate_or_fail(item, validator)
    assert len(properties_rent_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await redfin.scrape_search(
        url="https://www.redfin.com/city/16163/WA/Seattle"
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
