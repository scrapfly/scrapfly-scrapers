from cerberus import Validator
import seloger
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable cache
seloger.BASE_CONFIG["cache"] = True


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


property_schema = {
    "cityId": {"type": "integer"},
    "programId": {"type": "integer"},
    "name": {"type": "string"},
    "photos": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "url": {"type": "string"},
                "mobileUrl": {"type": "string"},
                "HDurl": {"type": "string"},
            },
        },
    },
    "leadData": {
        "type": "dict",
        "schema": {
            "professionalId": {"type": "integer"},
            "annonceRef": {"type": "string"},
            "professionalName": {"type": "string"},
            "xmlAnnonce": {"type": "string"}
        },
    },
    "description": {"type": "string"},
    "stock": {"type": "integer", "nullable": True},
    "propertyTypes": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "rooms": {"type": "integer"},
                "propertyTypeId": {"type": "integer"},
                "priceMin": {"type": "integer"},
                "priceMax": {"type": "integer"},
            }
        },
    },
    "location": {
        "type": "dict",
        "schema": {
            "address": {"type": "string"},
            "city": {
                "type": "dict",
                "schema": {
                    "cityId": {"type": "integer"},
                    "cityName": {"type": "string"},
                    "zipCode": {"type": "string"},
                    "ptzZoneLetter": {"type": "string"},
                    "inseeCode": {"type": "string"},
                },
            },
            "countryId": {"type": "integer"},
            "regionId": {"type": "integer"},
        },
    },
    "phoneNumber": {"type": "string"},
}

search_schema = {
    "title": {"type": "string"},
    "url": {"type": "string"},
    "images": {
        "type": "list",
        "schema": {"type": "string"}
    },
    "price": {"type": "string"},
    "price_per_m2": {"type": "string"},
    "property_facts": {
        "type": "list",
        "schema": {"type": "string"}
    },
    "address": {"type": "string"},
    "agency": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await seloger.scrape_search(
        url="https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08FR13100",
        max_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_property_scraping():
    property_data = await seloger.scrape_property(
        urls=[
            "https://www.selogerneuf.com/immobilier/neuf/bien-programme/ile-de-france/",
            "https://www.selogerneuf.com/recherche/?idtypebien=1,2,9&idtt=9&tri=datepublicationantechronologique&localities=239",
            "https://www.selogerneuf.com/recherche/?idtypebien=1,2,9&idtt=9&tri=selection&localities=5092"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for property in property_data:
        validate_or_fail(property, validator)
    assert len(property_data) >= 1
