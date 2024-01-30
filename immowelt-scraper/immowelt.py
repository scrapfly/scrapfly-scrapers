"""
This is an example web scraper for immowelt.de.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to switzerland
    "country": "DE",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

def parse_next_data(response: ScrapeApiResponse) -> Dict:
    """parse lsiting data from property page"""
    # get the property id from the page URL
    proeprty_id = str(response.context["url"]).split(".de/")[-1]
    selector = response.selector
    # extract the data from the script tag
    next_data = selector.xpath("//script[@id='serverApp-state']/text()").get()
    # parse the data into a valid JSON object
    next_data = json.loads(next_data.replace("&q;", '"').replace("\n", " "))
    return next_data[proeprty_id]


def parse_search_api(response: ScrapeApiResponse) -> List[Dict]:
    """parse the search API response"""
    data = json.loads(response.scrape_result["content"])
    search_data = data["data"]
    max_search_pages = data["pagesCount"]
    return {
        "search_data": search_data,
        "max_search_pages": max_search_pages
    }    


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listings data from property pages"""
    # add all property pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data = parse_next_data(response)
            properties.append(data)
        except:
            log.warning("expired property page")
    log.success(f"scraped {len(properties)} property listings")
    return properties


async def _get_auth_token() -> str:
    """get a new authorization token to authorize the API calls"""
    log.info("getting an auth token for the API")
    url = "https://www.immowelt.de/suche/muenchen/wohnungen/"
    # allows rendering headless browsers to capture local storage data
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, asp=True, render_js=True, country="DE", auto_scroll=True))
    # access the atuh token from local storage data
    auth_token = response.scrape_result["browser_data"]["local_storage_data"]["residential.search.ui.oauth.access.token"]
    return auth_token


async def send_api_request(page_number: int, auth_token: str, location_ids: List[int]) -> List[Dict]:
    """get search data from the search API"""
    # add the request headers
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
    }
    # add the request payload
    data = {
        "estateGroups": ["RESIDENTIAL", "COMMERCIAL"],
        "estateType": "APARTMENT", # APARTMENT or HOUSE
        "distributionTypes": ["SALE"], # SALE or RENT
        "estateSubtypes": [],
        "locationIds": location_ids,
        "featureFilters": [],
        "excludedFeatureFilters": [],
        # narrow down the search results by adding more search fields
        "primaryPrice": {"min": None, "max": None},
        "primaryArea": {"min": None, "max": None},
        "areas": [{"areaType": "PLOT_AREA", "min": None, "max": None}],
        "rooms": {"min": None, "max": None},
        "constructionYear": {"min": None, "max": None},
        "geoRadius": {"radius": None, "point": {"lat": None, "lon": None}},
        "sort": {"direction": "DESC", "field": "RELEVANCE"},
        "immoItemTypes": ["ESTATE", "PROJECT"],
        "paging": {"size": 20, "page": page_number},
    }

    # send a POST request to the search API
    response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url="https://api.immowelt.com/residentialsearch/v1/searches",
        headers=HEADERS,
        body=json.dumps(data),
        country="DE",
        method="POST"
    ))
    return response


async def scrape_search(scrape_all_pages: bool, max_scrape_pages: int, location_ids: List[int]) -> List[Dict]:
    """scrape search pages usign the search API"""
    # get the an auth token for the API
    auth_token = await _get_auth_token()
    # scrape the first search page
    first_page = await send_api_request(1, auth_token, location_ids)
    data = parse_search_api(first_page)
    search_data = data["search_data"]
    # get the the number of available search pages
    max_search_pages = data["max_search_pages"]
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages    
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    else:
        max_scrape_pages = max_search_pages
    log.info(f"scraping search pagination, remaining ({max_scrape_pages - 1}) more pages")
    # scrape the remaining search pages from the API
    for page_number in range(2, max_scrape_pages + 1):
        response = await send_api_request(page_number, auth_token, location_ids)
        data = parse_search_api(response)["search_data"]
        search_data.extend(data)
    log.success(f"scraped {len(search_data)} properties from search")
    return search_data