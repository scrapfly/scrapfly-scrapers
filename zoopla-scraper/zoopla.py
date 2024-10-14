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
    }""",
        {"root": data["listingDetails"]},
    )
    return result


async def scrape_properties(urls: List[str]):
    """scrape zoopla property listings from property pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all page URLs concurrently
    try:
        async for result in SCRAPFLY.concurrent_scrape(to_scrape):
            log.info("scraping property page {}", result.context["url"])
            properties.append(parse_property(result))
    except Exception as e:
        log.error(f"An error occurred while scraping property pages", e)
        pass
    return properties


def parse_search(response: ScrapeApiResponse):
    """parse property data from Zoopla search pages"""
    selector = response.selector
    data = []
    total_results = int(
        selector.xpath("//p[@data-testid='total-results']/text()").get().split(" ")[0]
    )
    total_pages = total_results // 25  # each page contains 25 results
    boxes = selector.xpath("//div[@data-testid='regular-listings']/div")
    for box in boxes:
        url = box.xpath(".//a/@href").get()
        if not url:
            continue
        price = box.xpath(".//p[@data-testid='listing-price']/text()").get()
        sq_ft = box.xpath(".//span[contains(text(),'sq. ft')]/text()").get()
        sq_ft = int(sq_ft.split(" ")[0]) if sq_ft else None
        listed_on = box.xpath(".//li[contains(text(), 'Listed on')]/text()").get()
        listed_on = listed_on.split("on")[-1].strip() if listed_on else None
        bathrooms = box.xpath(
            ".//li[span[text()='Bathrooms']]/span[not(contains(text(), 'Bathrooms'))]/text()"
        ).get()
        bedrooms = box.xpath(
            ".//li[span[text()='Bedrooms']]/span[not(contains(text(), 'Bedrooms'))]/text()"
        ).get()
        livingrooms = box.xpath(
            ".//li[span[text()='Living rooms']]/span[not(contains(text(), 'Living'))]/text()"
        ).get()
        image = box.xpath(".//picture/source/@srcset").get()
        item = {
            "title": box.xpath(".//h2[@data-testid='listing-title']/text()").get(),
            "price": price,
            "priceCurrency": "Sterling pound £",
            "url": "https://www.zoopla.co.uk" + url.split("?")[0] if url else None,
            "image": image.split(":p")[0] if image else None,
            "address": box.xpath(".//address/text()").get(),
            "squareFt": sq_ft,
            "numBathrooms": int(bathrooms) if bathrooms else None,
            "numBedrooms": int(bedrooms) if bedrooms else None,
            "numLivingRoom": int(livingrooms) if livingrooms else None,
            "description": box.xpath(
                ".//div[h2[@data-testid='listing-title']]/p/text()"
            ).get(),
            "justAdded": bool(box.xpath(".//div[text()='Just added']/text()").get()),
            "propertyType": box.xpath(".//ul[position()=2]/li/div/div/text()").get(),
            "timeAdded": listed_on,
        }
        data.append(item)
    return {"search_data": data, "total_pages": total_pages}


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
            render_js=True,
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
        ScrapeConfig(
            f"{first_page.context['url']}&pn={page}", **BASE_CONFIG, render_js=True
        )
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
