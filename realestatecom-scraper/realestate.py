"""
This is an example web scraper for realestate.com.au

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
import json
import jmespath
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass realesta.com.au scraping blocking
    "asp": True,
    # set the proxy country location
    "country": "US",
    "render_js" : True
}


output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_property_data(data: Dict) -> Dict:
    """refine property data from JSON"""
    if not data:
        return
    result = jmespath.search(
        """{
        id: id,
        propertyType: propertyType.display,
        description: description,            
        propertyLink: _links.canonical.href,
        address: address,
        propertySizes: propertySizes,
        generalFeatures: generalFeatures,
        propertyFeatures: propertyFeatures[].{featureName: displayLabel, value: value},
        images: media.images[].templatedUrl,
        videos: videos,
        floorplans: floorplans,        
        listingCompany: listingCompany.{name: name, id: id, companyLink: _links.canonical.href, phoneNumber: businessPhone, address: address.display.fullAddress, ratingsReviews: ratingsReviews, description: description},
        listers: listers,
        auction: auction
        }
        """,
        data,
    )
    return result


def parse_hidden_data(response: ScrapeApiResponse) -> Dict:
    """parse JSON data from script tag"""
    selector = response.selector
    script = selector.xpath(
        "//script[contains(text(),'window.ArgonautExchange')]/text()"
    ).get()
    # data needs to be parsed mutiple times
    data = json.loads(re.findall(r"window.ArgonautExchange=(\{.+\});", script)[0])
    data = json.loads(data["resi-property_listing-experience-web"]["urqlClientCache"])
    data = json.loads(list(data.values())[0]["data"])
    return data


def parse_search_data(data: List[Dict]) -> List[Dict]:
    """refine search data"""
    search_data = []
    data = list(data.values())[0]
    for listing in data["results"]["exact"]["items"]:
        # refine each property listing in the search results
        search_data.append(parse_property_data(listing["listing"]))
    max_search_pages = data["results"]["pagination"]["maxPageNumberAvailable"]
    return {"search_data": search_data, "max_search_pages": max_search_pages}


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from property pages"""
    # add the property pages URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all the property page concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:                
            data = parse_hidden_data(response)["details"]["listing"]
            data = parse_property_data(data)
            properties.append(data)
        except Exception as e:
            log.error(f"An error occurred while scraping property pages", e)
            pass        
    log.success(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(url: str, max_scrape_pages: int = None):
    """scrape property listings from search pages"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    log.info("scraping search page {}", url)
    data = parse_hidden_data(first_page)
    data = parse_search_data(data)
    search_data = data["search_data"]
    # get the number of maximum search pages
    max_search_pages = data["max_search_pages"]
    # scrape all available pages if not max_scrape_pages or max_scrape_pages > max_search_pages
    if max_scrape_pages and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    else:
        max_scrape_pages = max_search_pages
    log.info(
        f"scraping search pagination, remaining ({max_scrape_pages - 1} more pages)"
    )
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(
            str(first_page.context["url"]).split("/list")[0] + f"/list-{page}",
            **BASE_CONFIG,
        )
        for page in range(2, max_scrape_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        try:            
            data = parse_hidden_data(response)
            search_data.extend(parse_search_data(data)["search_data"])
        except Exception as e:
            log.error(f"An error occurred while scraping search pages", e)
            pass        
    log.success(f"scraped ({len(search_data)}) from {url}")
    return search_data
