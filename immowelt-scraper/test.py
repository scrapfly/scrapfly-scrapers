from cerberus import Validator
import immowelt
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


proeprty_schema = {
    "schema": {
        "type": "dict",
        "schema": {
            "GlobalObjectKey": {"type": "string"},
            "CreateDate": {"type": "string"},
            "General": {
                "type": "dict",
                "schema": {
                    "Headline": {"type": "string"},
                    "EstateType": {"type": "string"},
                    "EstateTypeKey": {"type": "string"},
                    "ReferenceNumber": {"type": "string", "nullable": True},
                    "DistributionTypeKey": {"type": "string"},
                    "DistributionType": {"type": "string"},
                    "ConstructionYear": {"type": "string"},
                    "Rooms": {"type": "integer"},
                    "LivingSpace": {"type": "integer"},
                },
            },
            "Seo": {
                "type": "dict",
                "schema": {
                    "BreadCrumb": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "Id": {"type": "string"},
                                "Name": {"type": "string"},
                            },
                        },
                    },
                    "MetaTags": {
                        "type": "dict",
                        "schema": {
                            "PageTitle": {"type": "string"},
                            "Description": {"type": "string"},
                        },
                    },
                    "SeoOptimizedLocation": {"type": "string"},
                },
            },
            "Tealium": {
                "type": "dict",
                "schema": {
                    "enh_promo_id": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "enh_promo_name": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "enh_promo_creative": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "enh_promo_position": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "broker_guid": {"type": "string"},
                    "object_count_photos": {"type": "integer"},
                    "object_state": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_locationid": {"type": "string"},
                    "object_city": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_district": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_federalstate": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_county": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_zip": {"type": "string"},
                    "object_address_is_visible": {"type": "boolean"},
                    "object_price": {"type": "integer"},
                    "object_currency": {"type": "string"},
                    "object_gok": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_features": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "object_rooms": {"type": "integer"},
                    "object_area": {"type": "integer"},
                    "object_marketingtype": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "product_net_price_total": {"type": "string"},
                    "product_business_type": {"type": "string"},
                    "product_building_state": {"type": "string", "nullable": True},
                    "expose_type": {"type": "string"},
                    "page_type": {"type": "string"},
                    "app_medienid": {"type": "string"},
                },
            },
            "InternalAds": {
                "type": "list",
                "schema": {"type": "dict", "schema": {"Id": {"type": "string"}, "URL": {"type": "string"}}},
            },
            "Advertisement": {
                "type": "dict",
                "schema": {
                    "TargetValues": {
                        "type": "dict",
                        "schema": {
                            "IMMO_ADGROUP": {"type": "string"},
                            "IMMO_ART": {"type": "integer"},
                            "IMMO_ESTATETYPE": {"type": "string"},
                            "IMMO_MK": {"type": "integer"},
                            "IMMO_DISTRIBUTION": {"type": "string"},
                            "IMMO_NT": {"type": "integer"},
                            "IMMO_P": {"type": "string"},
                            "IMMO_PRANGE": {"type": "string"},
                            "IMMO_GLOBALUSERID": {"type": "integer"},
                            "IMMO_LOCATIONID": {"type": "integer"},
                            "IMMO_ORTCLEAN": {"type": "string"},
                            "IMMO_ORT": {"type": "string"},
                            "IMMO_PLZ": {"type": "string"},
                            "IMMO_TITLE": {"type": "string"},
                            "IMMO_BJ": {"type": "string"},
                            "IMMO_BILD": {"type": "string"},
                            "IMMO_ZA": {"type": "integer"},
                            "IMMO_WFL": {"type": "integer"},
                        },
                    },
                    "CampaignLinks": {
                        "type": "list",
                        "schema": {"type": "string"},
                    },
                    "IsAllowedForFinancing": {"type": "boolean"},
                },
            },
            "EquipmentAreas": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "Key": {"type": "string"},
                        "Headline": {"type": "string"},
                        "Equipments": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Key": {"type": "string"},
                                    "Value": {"type": "string"},
                                    "DisplayType": {"type": "string"},
                                    "Label": {"type": "string"},
                                },
                            },
                        },
                    },
                    "type": "dict",
                    "schema": {
                        "Key": {"type": "string"},
                        "Headline": {"type": "string"},
                        "Equipments": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Key": {"type": "string"},
                                    "Value": {"type": "string"},
                                    "DisplayType": {"type": "string"},
                                    "Label": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "HardFacts": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "NumberValue": {"type": "integer"},
                        "Unit": {"type": "string"},
                        "Key": {"type": "string"},
                        "Label": {"type": "string"},
                        "Comments": {"type": "list", "schema": {"type": "string"}},
                    },
                },
            },
            "MetaBadges": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "label": {"type": "string"},
                        "highlight": {"type": "boolean"},
                    },
                },
            },
            "LocalRatings": {
                "type": "dict",
                "schema": {
                    "lastUpdated": {"type": "string"},
                    "scores": {
                        "type": "dict",
                        "schema": {
                            "local_amenities": {"type": "integer"},
                            "mobility": {"type": "integer"},
                        },
                    },
                },
            },
            "Texts": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "Title": {"type": "string"},
                        "Content": {"type": "string"},
                        "Position": {"type": "integer"},
                    },
                },
            },
            "Price": {
                "type": "dict",
                "schema": {
                    "AdditionalInformation": {
                        "type": "dict",
                        "schema": {
                            "MarketPricing": {
                                "type": "dict",
                                "schema": {
                                    "Heading": {"type": "string"},
                                    "Link": {"type": "string"},
                                },
                            }
                        },
                    },
                    "DataTable": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "NumberValue": {"type": "integer"},
                                "Unit": {"type": "string"},
                                "Key": {"type": "string"},
                                "Label": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "EstateAddress": {
                "type": "dict",
                "schema": {
                    "Country": {"type": "string"},
                    "City": {"type": "string"},
                    "District": {"type": "string"},
                    "ZipCode": {"type": "string"},
                    "Street": {"type": "string"},
                    "LocationId": {"type": "integer"},
                    "PublishStreet": {"type": "boolean"},
                    "FederalState": {"type": "string"},
                    "FederalStateId": {"type": "integer"},
                },
            },
            "EstateMapData": {
                "type": "dict",
                "schema": {
                    "LocationCoordinates": {
                        "type": "dict",
                        "schema": {
                            "Latitude": {"type": "integer"},
                            "Longitude": {"type": "integer"},
                        },
                    },
                    "ShowPin": {"type": "boolean"},
                    "LocationId": {"type": "integer"},
                    "LocatedIn": {"type": "string"},
                },
            },
            "MediaItems": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "BaseUri": {"type": "string"},
                        "FileName": {"type": "string"},
                        "FileSize": {"type": "integer"},
                        "Location": {"type": "string"},
                        "MediaId": {"type": "string"},
                        "MimeType": {"type": "string"},
                        "Position": {"type": "integer"},
                        "StoragePath": {"type": "string"},
                        "Title": {"type": "string"},
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
            "id": {"type": "string"},
            "itemType": {"type": "string"},
            "projectId": {"type": "string"},
            "locationIds": {"type": "list", "schema": {"type": "integer"}},
            "place": {"type": "dict", "schema": {"city": {"type": "string"}}},
            "estateTypes": {"type": "dict", "schema": {"type": "string"}},
            "distributionType": {"type": "string"},
            "title": {"type": "string"},
            "prices": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "amountMin": {"type": "integer"},
                        "amountMax": {"type": "integer"},
                        "type": {"type": "string"},
                        "currency": {"type": "string"},
                    },
                },
            },
            "areas": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "sizeMin": {"type": "integer"},
                        "sizeMax": {"type": "integer"},
                        "type": {"type": "string"},
                    },
                },
            },
            "primaryArea": {
                "type": "dict",
                "schema": {
                    "sizeMin": {"type": "integer"},
                    "sizeMax": {"type": "integer"},
                    "type": {"type": "string"},
                },
            },
            "primaryPrice": {
                "type": "dict",
                "schema": {
                    "amountMin": {"type": "integer"},
                    "amountMax": {"type": "integer"},
                    "type": {"type": "string"},
                    "currency": {"type": "string"},
                },
            },
            "roomsMin": {"type": "integer"},
            "roomsMax": {"type": "integer"},
            "timestamp": {"type": "string"},
            "isNew": {"type": "boolean"},
            "pictures": {
                "type": "list",
                "schema": {
                    "schema": {
                        "type": "dict",
                        "schema": {
                            "imageUri": {"type": "string"},
                            "imageUriBasePath": {"type": "string"},
                        },
                    }
                },
            },
            "broker": {
                "type": "dict",
                "schema": {
                    "guid": {"type": "integer"},
                    "sellerType": {"type": "string"},
                    "companyName": {"type": "string"},
                    "partnerAward": {"type": "string"},
                    "immoweltExclusive": {"type": "boolean"},
                    "logoUri": {"type": "string"},
                    "logoUriHttps": {"type": "string"},
                },
            },
            "onlineId": {"type": "string"},
            "projectData": {
                "type": "dict",
                "schema": {
                    "constructionStartDate": {"type": "string"},
                    "constructionEndDate": {"type": "string"},
                    "movingDate": {"type": "string"},
                    "logoUri": {"type": "string"},
                    "numberOfUnits": {"type": "integer"},
                },
            },
            "relatedItems": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "itemType": {"type": "string"},
                        "onlineId": {"type": "string"},
                        "gok": {"type": "string"},
                        "roomsMin": {"type": "integer"},
                        "roomsMax": {"type": "integer"},
                        "primaryPrice": {
                            "type": "dict",
                            "schema": {
                                "amountMin": {"type": "integer"},
                                "amountMax": {"type": "integer"},
                                "type": {"type": "string"},
                                "currency": {"type": "string"},
                            },
                        },
                        "primaryArea": {
                            "type": "dict",
                            "schema": {
                                "sizeMin": {"type": "integer"},
                                "sizeMax": {"type": "integer"},
                                "type": {"type": "string"},
                            },
                        },
                        "features": {"type": "list", "schema": {"type": "string"}},
                    },
                },
            },
        },
    }
}


@pytest.mark.asyncio
async def test_properties_scraping():
    properties_data = await immowelt.scrape_properties(
        urls=[
            "https://www.immowelt.de/expose/27dgc5f",
            "https://www.immowelt.de/expose/25jqw5t",
            "https://www.immowelt.de/expose/249p65w",
        ]
    )
    validator = Validator(proeprty_schema, allow_unknown=True)
    for item in properties_data:
        validate_or_fail(item, validator)
    assert len(properties_data) >= 1


@pytest.mark.asyncio
async def test_search_scraping():
    search_data = await immowelt.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=3,
        # the locations ids represent the search address
        # to get the locations ids, search for proeprties on immowet.de and inspect the API requests payload
        location_ids=[4916],
    )
    validator = Validator(search_schema, allow_unknown=True)
    for item in search_data:
        validate_or_fail(item, validator)
    assert len(search_data) >= 2
