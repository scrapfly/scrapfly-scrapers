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
    "listing": {
        "type": "dict",
        "schema": {
            "listingDetail": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer"},
                    "transactionTypeId": {"type": "integer"},
                    "transactionType": {"type": "string"},
                    "propertyTypeId": {"type": "integer"},
                    "propertyType": {"type": "string"},
                    "propertySubTypeId": {"type": "integer", "nullable": True},
                    "propertySubType": {"type": "string", "nullable": True},
                    "propertyNatureId": {"type": "integer"},
                    "publicationTypeIdSl": {"type": "integer"},
                    "publicationTypeId": {"type": "integer"},
                    "publicationId": {"type": "integer"},
                    "address": {
                        "type": "dict",
                        "schema": {
                            "city": {"type": "string"},
                            "superCity": {"type": "string", "nullable": True},
                            "postalCode": {"type": "string", "nullable": True},
                            "street": {"type": "string", "nullable": True},
                            "district": {"type": "string"},
                            "countryId": {"type": "integer"},
                            "divisionId": {"type": "integer", "nullable": True},
                        },
                    },
                    "reference": {"type": "string"},
                    "descriptive": {"type": "string"},
                    "roomCount": {"type": "integer"},
                    "bedroomCount": {"type": "integer"},
                    "surface": {"type": "float"},
                    "surfaceUnit": {"type": "string"},
                    "isExclusiveSalesMandate": {"type": "boolean"},
                    "isRentChargesIncluded": {"type": "boolean", "nullable": True},
                    "listingPrice": {
                        "type": "dict",
                        "schema": {
                            "price": {"type": "integer", "min": 1},
                            "priceUnit": {"type": "string"},
                            "pricePerSquareMeter": {
                                "type": "integer",
                                "nullable": True,
                            },
                            "monthlyPayment": {"type": "integer", "nullable": True},
                        },
                    },
                    "coordinates": {
                        "type": "dict",
                        "schema": {
                            "latitude": {"type": "float", "nullable": True},
                            "longitude": {"type": "float", "nullable": True},
                            "street": {"type": "string", "nullable": True},
                        },
                    },
                    "media": {
                        "type": "dict",
                        "schema": {
                            "photos": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "id": {"type": "integer"},
                                        "defaultUrl": {"type": "string"},
                                        "originalUrl": {"type": "string"},
                                        "lowResolutionUrl": {"type": "string"},
                                    },
                                },
                            }
                        },
                    },
                    "seoTitle": {"type": "string"},
                    "title": {"type": "string"},
                    "mainTitle": {"type": "string"},
                    "featuresPopupTitle": {"type": "string"},
                    "shortDescription": {"type": "string"},
                },
            },
        },
    },
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer"},
            "idRcu": {"type": "string"},
            "name": {"type": "string"},
            "professionType": {"type": "string"},
            "address": {"type": "string"},
            "logo": {"type": "string"},
            "description": {"type": "string"},
            "tierId": {"type": "integer"},
            "feesUrl": {"type": "string", "nullable": True},
            "websiteUrl": {"type": "string", "nullable": True},
            "profilPageUrl": {"type": "string"},
            "phoneNumber": {"type": "string", "nullable": True},
            "legalNotice": {
                "type": "dict",
                "schema": {
                    "rating": {"type": "integer", "nullable": True},
                    "reviewCount": {"type": "integer", "nullable": True},
                    "reviewUrl": {"type": "string", "nullable": True},
                },
            },
        },
    },
}

search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "integer"},
            "cardType": {"type": "string"},
            "publicationId": {"type": "integer"},
            "highlightingLevel": {"type": "integer"},
            "businessUnit": {"type": "integer"},
            "photosQty": {"type": "integer"},
            "photos": {"type": "list", "schema": {"type": "string"}},
            "title": {"type": "string"},
            "estateType": {"type": "string"},
            "estateTypeId": {"type": "integer"},
            "transactionTypeId": {"type": "integer"},
            "nature": {"type": "integer"},
            "pricing": {
                "type": "dict",
                "schema": {
                    "squareMeterPrice": {"type": "string"},
                    "rawPrice": {"type": "string"},
                    "price": {"type": "string"},
                    "monthlyPrice": {"type": "integer", "nullable": True},
                },
            },
            "contact": {
                "type": "dict",
                "schema": {
                    "agencyId": {"type": "integer"},
                    "agencyPage": {"type": "string"},
                    "isPrivateSeller": {"type": "boolean", "nullable": True},
                    "contactName": {"type": "string"},
                    "imgUrl": {"type": "string"},
                    "phoneNumber": {"type": "string"},
                    "email": {"type": "string"},
                    "agencyLink": {"type": "string"},
                },
            },
            "tags": {"type": "list", "schema": {"type": "string"}},
            "isExclusive": {"type": "boolean", "nullable": True},
            "cityLabel": {"type": "string"},
            "districtLabel": {"type": "string"},
            "zipCode": {"type": "string"},
            "description": {"type": "string"},
            "classifiedURL": {"type": "string"},
            "rooms": {"type": "integer", "nullable": True},
            "surface": {"type": "string", "nullable": True},
        },
    }
}


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await seloger.scrape_search(
        url="https://www.seloger.com/immobilier/achat/immo-bordeaux-33/bien-appartement/",
        scrape_all_pages=False,
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
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/hotel-de-ville-quinconce-saint-seurin-fondaudege/232628697.htm",
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/capucins-saint-michel-nansouty-saint-genes/230616779.htm",
            "https://www.seloger.com/annonces/achat/appartement/bordeaux-33/hotel-de-ville-quinconce-saint-seurin-fondaudege/228767099.htm"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for property in property_data:
        validate_or_fail(property, validator)
    assert len(property_data) >= 1
