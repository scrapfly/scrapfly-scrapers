from cerberus import Validator
import zoopla
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)

# enable scrapfly cache
zoopla.BASE_CONFIG["cache"] = True

def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )

search_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "address": {"type": "string"},
            "alternativeRentFrequencyLabel": {"type": "string", "nullable": True},
            "availableFrom": {"type": "string", "nullable": True},
            "branch": {
                "type": "dict",
                "schema": {
                    "branchId": {"type": "integer"},
                    "branchDetailsUri": {"type": "string"},
                    "logoUrl": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                }
            },
            "branchDetailsUri": {"type": "string"},
            "featuredType": {"type": "string", "nullable": True},
            "features": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "iconId": {"type": "string"},
                        "content": {"type": "integer"},
                    }
                }
            },
            "flag": {"type": "string"},
            "image": {
                "type": "dict",
                "schema": {
                    "src": {"type": "string"},
                    "responsiveImgList": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "width": {"type": "integer"},
                                "src": {"type": "string"}
                            }
                        }
                    },
                    "caption": {"type": "string"}
                }
            },
            "isPremium": {"type": "boolean"},
            "lastPublishedDate": {"type": "string"},
            "listingId": {"type": "string"},
            "listingUris": {
                "type": "dict",
                "schema": {
                    "contact": {"type": "string"},
                    "detail": {"type": "string"},
                    "success": {"type": "string"}
                }
            },
            "location": {
                "type": "dict",
                "schema": {
                    "coordinates": {
                        "type": "dict",
                        "schema": {
                            "isApproximate": {"type": "boolean"},
                            "latitude": {"type": "integer", "nullable": True},
                            "longitude": {"type": "integer", "nullable": True},
                        }
                    }
                }
            },
            "numberOfFloorPlans": {"type": "integer"},
            "numberOfImages": {"type": "integer"},
            "numberOfVideos": {"type": "integer"},
            "price": {"type": "string"},
            "priceDrop": {"type": "string", "nullable": True},
            "priceTitle": {"type": "string", "nullable": True},
            "propertyType": {"type": "string"},
            "publishedOn": {"type": "string"},
            "publishedOnLabel": {"type": "string"},
            "shortPriceTitle": {"type": "string"},
            "summaryDescription": {"type": "string"},
            "tags": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "content": {"type": "string"}
                    }
                }
            },
            "title": {"type": "string"},
            "underOffer": {"type": "boolean"},
            "availableFromLabel": {"type": "string"},
            "isFavourite": {"type": "boolean"},
            "content": {"type": "string"},
            "gallery": {
                "type": "list",
                "schema": {
                    "type": "list",
                    "schema": {
                        "type": "string", "nullable": True,
                        "type": "string",
                    }
                }
            }
        }
    }
}

property_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "url": {"type": "string"},
            "price": {"type": "string"},
            "type": {"type": "string"},
            "date": {"type": "string"},
            "category": {"type": "string"},
            "section": {"type": "string"},
            "features": {
                "type": "list",
                "schema": {
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                    "type": "string",
                }
            },
            "floor_plan": {
                "type": "dict",
                "schema": {
                    "filename": {"type": "string", "nullable": True},
                    "caption": {"type": "string", "nullable": True},
                }
            },
            "nearby": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "title": {"type": "string"},
                        "distance": {"type": "integer"},
                    }
                }
            },
            "coordinates": {
                "type": "dict",
                "schema": {
                    "lat": {"type": "integer"},
                    "lng": {"type": "integer"},
                }
            },
            "photos": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "filename": {"type": "string"},
                        "caption": {"type": "string"},
                    }
                }
            },
            "__typename": {"type": "string"},
            "location": {"type": "string"},
            "regionName": {"type": "string"},
            "section": {"type": "string"},
            "acorn": {"type": "integer"},
            "acornType": {"type": "integer"},
            "areaName": {"type": "string"},
            "bedsMax": {"type": "integer"},
            "bedsMin": {"type": "integer"},
            "branchId": {"type": "integer"},
            "branchLogoUrl": {"type": "string"},
            "branchName": {"type": "string"},
            "brandName": {"type": "string"},
            "chainFree": {"type": "boolean"},
            "companyId": {"type": "integer"},
            "countryCode": {"type": "string"},
            "countyAreaName": {"type": "string"},
            "currencyCode": {"type": "string"},
            "displayAddress": {"type": "string"},
            "hasEpc": {"type": "boolean"},
            "hasFloorplan": {"type": "boolean"},
            "incode": {"type": "string"},
            "isRetirementHome": {"type": "boolean"},
            "isSharedOwnership": {"type": "boolean"},
            "listingCondition": {"type": "string"},
            "listingId": {"type": "integer"},
            "listingsCategory": {"type": "string"},
            "listingStatus": {"type": "string"},
            "memberType": {"type": "string"},
            "numBaths": {"type": "integer"},
            "numBeds": {"type": "integer"},
            "numImages": {"type": "integer"},
            "numRecepts": {"type": "integer"},
            "outcode": {"type": "string"},
            "postalArea": {"type": "string"},
            "postTownName": {"type": "string"},
            "priceActual": {"type": "integer"},
            "price": {"type": "integer"},
            "priceMax": {"type": "integer"},
            "priceMin": {"type": "integer"},
            "propertyHighlight": {"type": "string"},
            "propertyType": {"type": "string"},
            "tenure": {"type": "string"},
            "zindex": {"type": "integer"},
            "agency": {
                "type": "dict",
                "schema": {
                    "__typename": {"type": "string"},
                    "branchDetailsUri": {"type": "string"},
                    "branchId": {"type": "string"},
                    "branchResultsUri": {"type": "string"},
                    "logoUrl": {"type": "string"},
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                    "memberType": {"type": "string"},
                    "address": {"type": "string"},
                    "postcode": {"type": "string"},
                }
            }
        }
    }
}


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await zoopla.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=2,
        query="Islington, London",
        query_type= "for-sale"
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await zoopla.scrape_properties(
        urls=[
            "https://www.zoopla.co.uk/new-homes/details/66622163/",
            "https://www.zoopla.co.uk/new-homes/details/66519409/",
            "https://www.zoopla.co.uk/new-homes/details/66622172/"
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1
