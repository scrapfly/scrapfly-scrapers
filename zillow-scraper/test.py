import pytest
from cerberus import Validator
import zillow

# enable cache?
zillow.BASE_CONFIG["cache"] = True


@pytest.mark.asyncio
async def test_search_scraping():
    url = "https://www.zillow.com/san-francisco-ca/?searchQueryState=%7B%22usersSearchTerm%22%3A%22Nebraska%22%2C%22mapBounds%22%3A%7B%22north%22%3A37.890669225201904%2C%22east%22%3A-122.26750460986328%2C%22south%22%3A37.659734343010626%2C%22west%22%3A-122.59915439013672%7D%2C%22isMapVisible%22%3Atrue%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22days%22%7D%2C%22ah%22%3A%7B%22value%22%3Atrue%7D%2C%22sche%22%3A%7B%22value%22%3Afalse%7D%2C%22schm%22%3A%7B%22value%22%3Afalse%7D%2C%22schh%22%3A%7B%22value%22%3Afalse%7D%2C%22schp%22%3A%7B%22value%22%3Afalse%7D%2C%22schr%22%3A%7B%22value%22%3Afalse%7D%2C%22schc%22%3A%7B%22value%22%3Afalse%7D%2C%22schu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A12%2C%22schoolId%22%3Anull%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A20330%2C%22regionType%22%3A6%7D%5D%2C%22pagination%22%3A%7B%7D%7D"
    result_search = await zillow.scrape_search(url=url, max_scrape_pages=3)
    schema = {
        "detailUrl": {"type": "string"},
        "timeOnZillow": {"type": "integer"},  # in seconds
        "beds": {"type": "integer", "nullable": True}, 
        "baths": {"type": "float", "nullable": True},
        "area": {"type": "integer", "nullable": True},
        "zpid": {"type": "integer", "coerce": int},  
        "price": {"type": "string"},  
    }
    validator = Validator(schema, allow_unknown=True)
    for item in result_search:
        if not validator.validate(item): 
            raise Exception({"item": item, "errors": validator.errors})


@pytest.mark.asyncio
async def test_property_scraping():
    url = "https://www.zillow.com/homedetails/661-Lakeview-Ave-San-Francisco-CA-94112/15192198_zpid/"
    result = await zillow.scrape_properties([url,])
    assert len(result) == 1
    result = result[0]
    schema = {
        "hdpUrl": {"type": "string"},
        "zpid": {"type": "integer", "coerce": int},  
        "city": {"type": "string"},
        "country": {"type": "string"},
        "state": {"type": "string"},
        "homeStatus": {"type": "string"},
        "price": {"type": "integer"},
        "yearBuilt": {"type": "integer"},
        "pageViewCount": {"type": "integer"},
        "favoriteCount": {"type": "integer"},
        "daysOnZillow": {"type": "integer"},
    }
    validator = Validator(schema, allow_unknown=True)
    if not validator.validate(result):
        raise Exception({"item": result, "errors": validator.errors})
