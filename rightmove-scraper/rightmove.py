"""
This is an example web scraper for rightmove.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import jmespath
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import List
from pathlib import Path
from loguru import logger as log
from typing import TypedDict
from urllib.parse import urlencode

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "GB",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class PropertyResult(TypedDict):
    """this is what our result dataset will look like"""
    id: str
    available: bool
    archived: bool
    phone: str
    bedrooms: int
    bathrooms: int
    type: str
    property_type: str
    tags: list
    description: str
    title: str
    subtitle: str
    price: str
    price_sqft: str
    address: dict
    latitude: float
    longitude: float
    features: list
    history: dict
    photos: list
    floorplans: list
    agency: dict
    industryAffiliations: list
    nearest_airports: list
    nearest_stations: list
    sizings: list
    brochures: list


def parse_property(data) -> PropertyResult:
    """parse rightmove cache data for proprety information"""
    # here we define field name to JMESPath mapping
    parse_map = {
        "id": "id",
        "available": "status.published",
        "archived": "status.archived",
        "phone": "contactInfo.telephoneNumbers.localNumber",
        "bedrooms": "bedrooms",
        "bathrooms": "bathrooms",
        "type": "transactionType",
        "property_type": "propertySubType",
        "tags": "tags",
        "description": "text.description",
        "title": "text.pageTitle",
        "subtitle": "text.propertyPhrase",
        "price": "prices.primaryPrice",
        "price_sqft": "prices.pricePerSqFt",
        "address": "address",
        "latitude": "location.latitude",
        "longitude": "location.longitude",
        "features": "keyFeatures",
        "history": "listingHistory",
        "photos": "images[*].{url: url, caption: caption}",
        "floorplans": "floorplans[*].{url: url, caption: caption}",
        "agency": """customer.{
            id: branchId, 
            branch: branchName, 
            company: companyName, 
            address: displayAddress, 
            commercial: commercial, 
            buildToRent: buildToRent,
            isNew: isNewHomeDeveloper
        }""",
        "industryAffiliations": "industryAffiliations[*].name",
        "nearest_airports": "nearestAirports[*].{name: name, distance: distance}",
        "nearest_stations": "nearestStations[*].{name: name, distance: distance}",
        "sizings": "sizings[*].{unit: unit, min: minimumSize, max: maximumSize}",
        "brochures": "brochures",
    }
    results = {}
    for key, path in parse_map.items():
        value = jmespath.search(path, data)
        results[key] = value
    return results


def find_json_objects(text: str, decoder=json.JSONDecoder()):
    """Find JSON objects in text, and generate decoded JSON data"""
    pos = 0
    while True:
        match = text.find("{", pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            yield result
            pos = match + index
        except ValueError:
            pos = match + 1


def extract_property(result: ScrapeApiResponse) -> dict:
    """extract property data from rightmove PAGE_MODEL javascript variable"""
    data = result.selector.xpath("//script[contains(.,'PAGE_MODEL = ')]/text()").get()
    json_data = list(find_json_objects(data))[0]
    return json_data["propertyData"]


async def scrape_properties(urls: List[str]) -> List[PropertyResult]:
    """scrape Rightmove property listings for property data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all page URLs concurrently
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        log.info("scraping property page {}", result.context["url"])
        properties.append(parse_property(extract_property(result)))
    return properties


async def find_locations(query: str) -> List[str]:
    """use rightmove's typeahead api to find location IDs. Returns list of location IDs in most likely order"""
    # rightmove uses two character long tokens so "cornwall" becomes "CO/RN/WA/LL"
    tokenize_query = "".join(
        c + ("/" if i % 2 == 0 else "") for i, c in enumerate(query.upper(), start=1)
    )
    url = (
        f"https://www.rightmove.co.uk/typeAhead/uknostreet/{tokenize_query.strip('/')}/"
    )
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = json.loads(result.content)
    # get the location id
    return [
        prediction["locationIdentifier"] for prediction in data["typeAheadLocations"]
    ]


async def scrape_search(
    location_id: str, scrape_all_properties: bool, max_properties: int = 1000
) -> dict:
    """scrape properties data from rightmove's search api"""
    log.info("scraping search with the id {}", location_id)
    RESULTS_PER_PAGE = 24
    # create a search URL
    def make_url(offset: int) -> str:
        url = "https://www.rightmove.co.uk/api/_search?"
        params = {
            "areaSizeUnit": "sqft",
            "channel": "BUY",  # BUY or RENT
            "currencyCode": "GBP",
            "includeSSTC": "false",
            "index": offset,  # page offset
            "isFetching": "false",
            "locationIdentifier": location_id,  # e.g.: "REGION^61294",
            "numberOfPropertiesPerPage": RESULTS_PER_PAGE,
            "radius": "0.0",
            "sortType": "6",
            "viewType": "LIST",
        }
        return url + urlencode(params)

    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(make_url(0), **BASE_CONFIG))
    first_page_data = json.loads(first_page.content)
    # get the properties data in the first search page 
    results = first_page_data["properties"]
    # get all available properties in this search query
    total_results = int(first_page_data["resultCount"].replace(",", ""))
    # scrape all available properties in the search if scrape_all_properties = True or max_properties > total_results
    if scrape_all_properties == False and max_properties < total_results:
        MAX_RESULTS = max_properties
    else:
        MAX_RESULTS = total_results

    other_pages = []
    # rightmove sets the API limit to 1000 properties
    max_api_results = 1000
    # add the remaining search pages as a list
    for offset in range(RESULTS_PER_PAGE, MAX_RESULTS, RESULTS_PER_PAGE):
        # stop adding more pages when the scraper reach the API limit
        if offset >= max_api_results:
            break        
        other_pages.insert(0, ScrapeConfig(make_url(offset), **BASE_CONFIG))
    log.info(
        "scraped search page with the location id {} remaining ({} more pages)",
        location_id,
        len(other_pages) - 1,
    )
    # scrape the remaining search pages concurrently
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        data = json.loads(result.content)
        results.extend(data["properties"])
    log.info("scraped {} proprties from the location id {}", len(results), location_id)
    return results
