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

BASE_CONFIG = {"asp": True, "country": "GB"}

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
    next_data_json = json.loads(next_data)["props"]["pageProps"] if next_data else None
    return next_data_json


def parse_property(response: ScrapeApiResponse) -> Optional[PropertyResult]:
    """refine property data using JMESPath"""
    data = parse_next_data(response)
    if not data:
        raise Exception("Hidden script data aren't found")
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
    }""",
        {"root": data["listingDetails"]},
    )
    return result


async def scrape_properties(urls: List[str]):
    """scrape zoopla property listings from property pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all page URLs concurrently
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            log.info("scraping property page {}", result.context["url"])
            properties.append(parse_property(result))
        except Exception as e:
            log.error(f"An error occurred while scraping property pages", e)
            continue
    return properties


def parse_search(response: ScrapeApiResponse):
    """parse property data from Zoopla search pages"""
    selector = response.selector
    data = []
    total_results = int(
        json.loads(selector.xpath("//script[@id='__ZAD_TARGETING__']/text()").get())["search_results_count"]
    )
    boxes = selector.xpath("//div[@data-testid='regular-listings']/div")
    _results_count = len(boxes)
    total_pages = total_results // _results_count

    for box in boxes:
        url = box.xpath(".//a/@href").get()
        if not url:
            continue
        price = box.xpath(".//p[@data-testid='listing-price']/text()").get()
        sq_ft = box.xpath(".//span[contains(text(),'sq. ft')]/text()").get()
        sq_ft = int(sq_ft.split(" ")[0]) if sq_ft else None
        listed_on = box.xpath(".//li[contains(text(), 'Listed on')]/text()").get()
        listed_on = listed_on.split("on")[-1].strip() if listed_on else None
        bathrooms = box.xpath(".//span[(contains(text(), 'bath'))]/text()").get()
        bedrooms = box.xpath(".//span[(contains(text(), 'bed'))]/text()").get()
        livingrooms = box.xpath(".//span[(contains(text(), 'reception'))]/text()").get()
        image = box.xpath(".//picture/source/@srcset").get()
        agency = box.xpath(".//div[a[@data-testid='listing-card-content']]/div")
        item = {
            "price": int(price.split(" ")[0].replace("£", "").replace(",", "")) if price else None,
            "priceCurrency": "Sterling pound £",
            "url": "https://www.zoopla.co.uk" + url.split("?")[0] if url else None,
            "image": image.split(":p")[0] if image else None,
            "address": box.xpath(".//address/text()").get(),
            "squareFt": sq_ft,
            "numBathrooms": int(bathrooms.split(" ")[0]) if bathrooms else None,
            "numBedrooms": int(bedrooms.split(" ")[0]) if bedrooms else None,
            "numLivingRoom": int(livingrooms.split(" ")[0]) if livingrooms else None,
            "description": box.xpath(".//div[address]/p/text()").get(),
            "justAdded": bool(box.xpath(".//div[text()='Just added']/text()").get()),
            "agency": agency.xpath(".//img/@alt").get() or agency.xpath(".//p/text()").get(),
        }
        data.append(item)
    return {"search_data": data, "total_pages": total_pages}


async def scrape_search(
    scrape_all_pages: bool,
    location_slug: str,
    max_scrape_pages: int = 10,
    query_type: Literal["for-sale", "to-rent"] = "for-sale",
) -> List[Dict]:
    """scrape zoopla search pages for roperty listings"""
    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://www.zoopla.co.uk/{query_type}/property/{location_slug}",
            **BASE_CONFIG,
            render_js=True,
            auto_scroll=True,
            rendering_wait=5000,
            wait_for_selector="//p[@data-testid='total-results']",
        )
    )
    data = parse_search(first_page)
    # extract property listings
    search_data = data["search_data"]
    # get the number of the available search pages
    max_search_pages = data["total_pages"]
    # scrape all available pages in the search if scrape_all_pages = True or max_search_pages > max_scrape_pages
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        total_pages_to_scrape = max_scrape_pages
    else:
        total_pages_to_scrape = max_search_pages
    log.info(
        "scraping search page {} remaining ({} more pages)",
        first_page.context["url"],
        total_pages_to_scrape - 1,
    )
    # add the remaining search pages to a scraping list
    _other_pages = [
        ScrapeConfig(f"{first_page.context['url']}&pn={page}", **BASE_CONFIG, render_js=True)
        for page in range(2, total_pages_to_scrape + 1)
    ]
    # scrape the remaining search page concurrently
    try:
        async for result in SCRAPFLY.concurrent_scrape(_other_pages):
            page_data = parse_search(result)["search_data"]
            search_data.extend(page_data)
    except Exception as e:
        log.error(f"An error occurred while scraping search pages", e)
        pass

    log.info(
        "scraped {} search listings from {}",
        len(search_data),
        first_page.context["url"],
    )
    return search_data
