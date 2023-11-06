from cerberus import Validator
import immoscout24
import pytest
import pprint
import json

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(
            f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}"
        )


property_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "detailsData": {
                "type": "dict",
                "schema": {
                    "accountId": {"type": "integer"},
                    "companyId": {"type": "integer"},
                    "memberPackageId": {"type": "integer"},
                    "agency": {
                        "type": "dict",
                        "schema": {
                            "companyCity": {"type": "string"},
                            "companyName1": {"type": "string"},
                            "companyPhoneBusiness": {"type": "string"},
                            "companyStreet": {"type": "string"},
                            "companyZip": {"type": "string"},
                            "showLogoOnSerp": {"type": "boolean"},
                            "lastName": {"type": "string"},
                            "logoUrl": {"type": "string"},
                            "logoUrlDetailPage": {"type": "string"},
                            "reference": {"type": "string"},
                            "webUrl": {"type": "string"},
                            "isAccountMigrated": {"type": "boolean"},
                            "isGuest": {"type": "boolean"},
                            "userType": {"type": "string"},
                        },
                    },
                    "attributesInside": {
                        "type": "dict",
                        "schema": {
                            "propView": {"type": "boolean"},
                        },
                    },
                    "attributesTechnology": {
                        "type": "dict",
                        "schema": {
                            "propCabletv": {"type": "boolean"},
                        },
                    },
                    "attributesTechnology": {
                        "type": "dict",
                        "schema": {
                            "propElevator": {"type": "boolean"},
                            "propBalcony": {"type": "boolean"},
                        },
                    },
                    "attributesSurrounding": {
                        "type": "dict",
                        "schema": {
                            "distanceShop": {"type": "integer"},
                            "distanceShopFormatted": {"type": "string"},
                            "distanceKindergarten": {"type": "integer"},
                        },
                    },
                    "attributes": {
                        "type": "dict",
                        "schema": {
                            "yearBuilt": {"type": "integer"},
                        },
                    },
                    "availableFrom": {"type": "string"},
                    "availableFromFormatted": {"type": "string"},
                    "cityId": {"type": "integer"},
                    "cityName": {"type": "string"},
                    "commuteTimes": {
                        "type": "dict",
                        "schema": {
                            "defaultPois": {
                                "type": "list",
                                "schema": {
                                    "type": "dict",
                                    "schema": {
                                        "defaultPoiId": {"type": "integer"},
                                        "label": {"type": "string"},
                                        "transportations": {
                                            "type": "list",
                                            "schema": {
                                                "type": "dict",
                                                "schema": {
                                                    "transportationTypeId": {
                                                        "type": "integer"
                                                    },
                                                    "travelTime": {"type": "integer"},
                                                    "isReachable": {"type": "boolean"},
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "contactFormTypeId": {"type": "integer"},
                    "countryId": {"type": "integer"},
                    "description": {"type": "string"},
                    "extraPrice": {"type": "integer"},
                    "extraPriceFormatted": {"type": "string"},
                    "geoAccuracy": {"type": "integer"},
                    "grossPrice": {"type": "integer"},
                    "grossPriceFormatted": {"type": "string"},
                    "hasNewBuildingProject": {"type": "boolean"},
                    "hasVirtualTour": {"type": "boolean"},
                    "id": {"type": "integer"},
                    "images": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "url": {"type": "string"},
                                "originalWidth": {"type": "integer"},
                                "originalHeight": {"type": "integer"},
                                "id": {"type": "integer"},
                                "sortOrder": {"type": "integer"},
                                "lastModified": {"type": "string"},
                            },
                        },
                    },
                    "isHighlighted": {"type": "boolean"},
                    "isNeubauLite": {"type": "boolean"},
                    "isNeubauLitePremium": {"type": "boolean"},
                    "isHgCrosslisting": {"type": "boolean"},
                    "isNew": {"type": "boolean"},
                    "isNewEndDate": {"type": "string"},
                    "isOnline": {"type": "boolean"},
                    "isTopListing": {"type": "boolean"},
                    "isPremiumToplisting": {"type": "boolean"},
                    "latitude": {"type": "integer"},
                    "longitude": {"type": "integer"},
                    "msRegionId": {"type": "integer"},
                    "netPrice": {"type": "integer"},
                    "netPriceFormatted": {"type": "string"},
                    "normalizedPrice": {"type": "integer"},
                    "numberOfRooms": {"type": "integer"},
                    "price": {"type": "integer"},
                    "propertyCategoryId": {"type": "integer"},
                    "regionId": {"type": "integer"},
                    "state": {"type": "string"},
                    "street": {"type": "string"},
                    "surfaceLiving": {"type": "integer"},
                    "title": {"type": "string"},
                    "lastPublished": {"type": "string"},
                    "shortDescription": {"type": "string"},
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
            "accountId": {"type": "integer"},
            "companyId": {"type": "integer"},
            "memberPackageId": {"type": "integer"},
            "agency": {
                "type": "dict",
                "schema": {
                    "companyCity": {"type": "string"},
                    "companyName1": {"type": "string"},
                    "companyPhoneBusiness": {"type": "string"},
                    "companyStreet": {"type": "string"},
                    "companyZip": {"type": "string"},
                    "firstName": {"type": "string"},
                    "gender": {"type": "string"},
                    "gendshowLogoOnSerper": {"type": "boolean"},
                    "lastName": {"type": "string"},
                    "logoUrl": {"type": "string"},
                    "logoUrlDetailPage": {"type": "string"},
                    "nameFormatted": {"type": "string"},
                },
            },
            "availableFrom": {"type": "string"},
            "availableFromFormatted": {"type": "string"},
            "cityId": {"type": "integer"},
            "cityName": {"type": "string"},
            "commuteTimes": {
                "type": "dict",
                "schema": {
                    "defaultPois": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "defaultPoiId": {"type": "integer"},
                                "label": {"type": "string"},
                                "transportations": {
                                    "type": "list",
                                    "schema": {
                                        "type": "dict",
                                        "schema": {
                                            "transportationTypeId": {"type": "integer"},
                                            "travelTime": {"type": "integer"},
                                            "isReachable": {"type": "boolean"},
                                        },
                                    },
                                },
                            },
                        },
                    }
                },
            },
            "countryId": {"type": "integer"},
            "extraPrice": {"type": "integer"},
            "geoAccuracy": {"type": "integer"},
            "grossPrice": {"type": "integer"},
            "hasNewBuildingProject": {"type": "boolean"},
            "hasVirtualTour": {"type": "boolean"},
            "isHighlighted": {"type": "boolean"},
            "isNeubauLite": {"type": "boolean"},
            "isNeubauLitePremium": {"type": "boolean"},
            "isHgCrosslisting": {"type": "boolean"},
            "latitude": {"type": "integer"},
            "longitude": {"type": "integer"},
            "netPrice": {"type": "integer"},
            "numberOfRooms": {"type": "integer"},
            "price": {"type": "integer"},
            "propertyUrl": {"type": "string"},
            "propertyCategoryId": {"type": "integer"},
            "propertyTypeId": {"type": "integer"},
            "state": {"type": "string"},
            "street": {"type": "string"},
            "surfaceLiving": {"type": "integer"},
            "images": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "url": {"type": "string"},
                        "originalWidth": {"type": "integer"},
                        "originalHeight": {"type": "integer"},
                        "id": {"type": "integer"},
                    },
                },
            },
            "lastPublished": {"type": "string"},
            "sortalgoScore": {"type": "integer"},
            "sortalgoScore2": {"type": "integer"},
        },
    }
}


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await immoscout24.scrape_properties(
        urls=[
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8068164",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/7940339",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8068179",
        ]
    )
    validator = Validator(property_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await immoscout24.scrape_search(
        url="https://www.immoscout24.ch/en/real-estate/rent/city-bern",
        scrape_all_pages=False,
        max_scrape_pages=2,
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
