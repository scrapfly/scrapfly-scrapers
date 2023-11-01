"""
This is an example web scraper for zoopla.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import jmespath
import urllib.parse
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, Literal, TypedDict, Optional
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "GB"
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class PropertyResult(TypedDict):
    """type hint of what the scraped property would look like"""
    listing_id: str
    title: str
    description: str
    url: str
    price: str
    photos: List[dict]
    agency: Dict[str, str]
    features: List[str]
    floor_plan: List[dict]
    nearby: List[dict]
    coordinates: dict
    photos: List[dict]
    details: dict
    agency: dict

def parse_next_data(result: ScrapeApiResponse) -> Dict:
    """parse hidden data from script tags"""
    next_data = result.selector.css("script#__NEXT_DATA__::text").get()
    next_data_json = json.loads(next_data)["props"]["pageProps"]
    return next_data_json


def parse_property(response: ScrapeApiResponse) -> Optional[PropertyResult]:
    """refine property data using JMESPath"""
    data = parse_next_data(response)
    if not data:
        return
    result = jmespath.search(
        """root.{
        id: listingId,
        title: title,
        description: detailedDescription,
        url: listingUris.detail,
        price: pricing.label,
        type: propertyType,
        date: publishedOn,
        category: category,
        section: section,
        features: features.bullets,
        floor_plan: floorPlan.image.{filename:filename, caption: caption}, 
        nearby: pointsOfInterest[].{title: title, distance: distanceMiles},
        coordinates: location.coordinates.{lat:latitude, lng: longitude},
        photos: propertyImage[].{filename: filename, caption: caption},
        details: analyticsTaxonomy,
        agency: branch
    }""", {"root": data["listingDetails"]})
    return result


def _get_max_search_pages(response: ScrapeApiResponse):
    selector = response.selector
    data = selector.css("script#__NEXT_DATA__::text").get()
    data = json.loads(data)
    return data["props"]["pageProps"]["initialState"]["pageNumberMax"]

async def scrape_properties(urls: List[str]):
    """scrape zoopla property listings from property pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all page URLs concurrently
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        log.info("scraping property page {}", result.context["url"])
        properties.append(parse_property(result))
    return properties


async def scrape_search(
    scrape_all_pages: bool,
    query: str,
    max_scrape_pages: int = 10,
    query_type: Literal["for-sale", "to-rent"] = "for-sale",
) -> List[Dict]:
    """scrape zoopla search pages for roperty listings"""
    encoded_query = urllib.parse.quote(query)
    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://www.zoopla.co.uk/search/?view_type=list&section={query_type}&q={encoded_query}&geo_autocomplete_identifier=&search_source=home&sort=newest_listings",
            **BASE_CONFIG,
        )
    )
    data = parse_next_data(first_page)
    # extract property listings
    search_data = data["regularListingsFormatted"]
    # get the number of the available search pages 
    max_search_pages = _get_max_search_pages(first_page)
    # scrape all available pages in the search if scrape_all_pages = True or max_search_pages > max_scrape_pages
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        total_pages_to_scrape = max_scrape_pages
    else:
        total_pages_to_scrape = max_search_pages
    log.info("scraping search page {} remaining ({} more pages)", first_page.context['url'], total_pages_to_scrape - 1)
    # add the remaining search pages to a scraping list
    _other_pages = [
        ScrapeConfig(f"{first_page.context['url']}&pn={page}", **BASE_CONFIG)
        for page in range(2, total_pages_to_scrape + 1)
    ]
    # scrape the remaining search page concurrently
    async for result in SCRAPFLY.concurrent_scrape(_other_pages):
        page_data = parse_next_data(result)["regularListingsFormatted"]
        search_data.extend(page_data)
    log.info("scraped {} search listings from {}", len(search_data), first_page.context['url'])
    return search_data
