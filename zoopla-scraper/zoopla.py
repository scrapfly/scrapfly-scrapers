"""
This is an example web scraper for zoopla.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import jmespath
from pathlib import Path
from loguru import logger as log
from urllib.parse import urlparse, parse_qs
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
    selector = response.selector
    url = selector.xpath("//meta[@property='og:url']/@content").get()
    price = selector.xpath("//p[contains(text(),'£')]/text()").get()
    receptions = selector.xpath("//p[contains(text(),'reception')]/text()").get()
    baths = selector.xpath("//p[contains(text(),'bath')]/text()").get()
    beds = selector.xpath("//p[contains(text(),'bed')]/text()").get()
    gmap_source = selector.xpath("(//section[@aria-labelledby='local-area']//picture/source/@srcset)[last()]").get()
    coordinates = gmap_source.split("/static/")[1].split("/")[0] if gmap_source else None
    agent_path = selector.xpath("//section[@aria-label='Contact agent']//a/@href").get()

    info = []
    for i in selector.xpath("//section[h2[@id='key-info']]/ul/li"):
        info.append(
            {
                "title": i.xpath(".//p/text()").get(),
                "value": i.xpath(".//div/p/text()").get(),
            }
        )

    nearby = []
    for i in selector.xpath("//div[section[contains(@aria-label,'Travel')]]/section[3]//li/div"):
        distance = i.xpath(".//p[2]/text()").get()
        nearby.append(
            {
                "title": i.xpath(".//p[1]/text()").get(),
                "distance": float(distance.split(" ")[0]) if distance else None,
                "unit": distance.split(" ")[1] if distance else None,
            }
        )

    result = {
        "id": int(url.split("details/")[-1].split("/")[0]) if url else None,
        "url": url,
        "title": selector.xpath("//title/text()").get(),
        "address": selector.xpath("//address/text()").get(),
        "price": {
            "amount": int(price.replace("£", "").replace(",", "")) if price else None,
            "currency": "£",
        },
        "gallery": selector.xpath("//li[contains(@data-key,'gallery')]/picture/source[last()]/@srcset").getall(),
        "epcRating": selector.xpath("//p[contains(text(),'EPC')]/text()").get(),
        "floorArea": selector.xpath("//p[contains(text(),'ft')]/text()").get(),
        "numOfReceptions": int(receptions.split(" ")[0]) if receptions else None,
        "numOfBathrooms": int(baths.split(" ")[0]) if baths else None,
        "numOfBedrooms": int(beds.split(" ")[0]) if beds else None,
        "propertyTags": selector.xpath("(//section/ul)[1]/li/p/text()").getall(),
        "propertyInfo": info,
        "propertyDescription": selector.xpath("//section[@aria-labelledby='about']/ul/li/p/span/text()").getall(),
        "coordinates": {
            "googleMapeSource": gmap_source,
            "latitude": float(coordinates.split(",")[0]) if coordinates else None,
            "longitude": float(coordinates.split(",")[1]) if coordinates else None,
        },
        "nearby": nearby,
        "agent": {
            "name": selector.xpath("//section[@aria-label='Contact agent']//p/text()").get(),
            "logo": selector.xpath("//section[@aria-label='Contact agent']//img/@src").get(),
            "url": "https://www.zoopla.co.uk" + agent_path if agent_path else None,
        }
    }

    return result


async def scrape_properties(urls: List[str]):
    """scrape zoopla property listings from property pages"""
    to_scrape = [
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            render_js=True,
            auto_scroll=True,
            wait_for_selector="//section[@aria-labelledby='local-area']",
        )
        for url in urls
    ]
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
            "description": box.xpath(".//a[address]/p/text()").get(),
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
