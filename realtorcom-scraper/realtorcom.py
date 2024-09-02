"""
This is an example web scraper for Realtor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-realtorcom/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
import math
import os
import jmespath

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # realtor.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",
}


def parse_property(result: ScrapeApiResponse) -> Dict:
    """
    Parse realtor.com's property page for property data
    and reduce realtor.com's dataset into a cleaner version.
    """
    log.debug("parsing property page: {}", result.context["url"])
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if not data:
        print(f"page {result.context['url']} is not a property listing page")
        return
    data = json.loads(data)
    raw_data = data["props"]["pageProps"]["initialReduxState"]
    reduced = jmespath.search(
        """{
        id: propertyDetails.listing_id,
        slug: slug,
        url: propertyDetails.href,
        status: propertyDetails.status,
        tags: propertyDetails.tags,
        sold_date: propertyDetails.last_sold_date,
        sold_price: propertyDetails.last_sold_price,
        list_date: propertyDetails.list_date,
        list_price: propertyDetails.list_price,
        list_price_last_change: propertyDetails.last_price_change_amount,
        details: propertyDetails.description,
        flags: propertyDetails.flags,
        local: propertyDetails.local,
        location: propertyDetails.location,
        agent: propertyDetails.source.agents,
        advertisers: propertyDetails.advertisers,
        tax_history: propertyDetails.tax_history,
        history: propertyDetails.property_history[].{
            date: date,
            event: event_name,
            price: price,
            price_sqft: price_sqft
        },
        photos: propertyDetails.photos[].{
            url: href,
            tags: tags[].label
        },
        phones: propertyDetails.lead_attributes.opcity_lead_attributes.phones[].{
            type: category,
            number: number
        },
        features: propertyDetails.details[].{
            name: category,
            values: text
        }
    }""",
        raw_data,
    )
    reduced['features'] = {feature['name']: feature['values'] for feature in reduced['features']}
    return reduced


async def scrape_property(url: str) -> List[Dict]:
    """scrape realtor.com's property page for property data"""
    log.info("scraping {} property page", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url=url, **BASE_CONFIG))
    property = parse_property(result)
    return property


def parse_search(result: ScrapeApiResponse) -> Dict:
    """parse realtor.com's search page for search result data"""
    log.info("parsing search page: {}", result.context["url"])
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if not data:
        print(f"page {result.context['url']} is not a property listing page")
        return
    data = json.loads(data)["props"]["pageProps"]
    if not data.get('properties'):  # a|b testing, sometimes it's in a different location
        data['properties'] = data["searchResults"]["home_search"]["results"]
    if not data.get('totalProperties'):
        data['totalProperties'] = data['searchResults']['home_search']['total']
    return data


async def scrape_search(state: str, city: str, max_pages: Optional[int] = None) -> List[Dict]:
    """scrape realtor.com's search and find properties for given query. Paginate to max pages if provided"""
    log.info("scraping first property search page for {}, {}", city, state)
    first_page = f"https://www.realtor.com/realestateandhomes-search/{city}_{state}/pg-1"
    first_result = await SCRAPFLY.async_scrape(ScrapeConfig(first_page, **BASE_CONFIG))
    first_data = parse_search(first_result)
    results = first_data["properties"]

    total_pages = math.ceil(first_data["totalProperties"] / len(results))
    if max_pages and total_pages > max_pages:
        total_pages = max_pages

    log.info("found {} total pages", total_pages)
    to_scrape = []
    for page in range(1, total_pages + 1):
        assert "pg-1" in first_result.context["url"]  # make sure we don't accidently scrape duplicate pages
        page_url = first_result.context["url"].replace("pg-1", f"pg-{page}")
        to_scrape.append(ScrapeConfig(page_url, **BASE_CONFIG))

    log.info("scraping {} property search pages for {}, {}", len(to_scrape), city, state)
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        parsed = parse_search(result)
        results.extend(parsed["properties"])
    log.info(f"scraped search of {len(results)} results for {city}, {state}")
    return results


async def scrape_feed(url) -> Dict[str, datetime]:
    """scrapes atom RSS feed and returns all entries in "url:publish date" format"""
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, retry=True))
    body = result.content
    selector = Selector(text=body, type="xml")    
    results = {}
    for item in selector.xpath("//item"):
        url = item.xpath("link/text()").get()
        pub_date = item.xpath("pubDate/text()").get()
        results[url] = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S")
    return results


async def track_feed(url: str, output: Path, interval=60):
    """Track Realtor.com feed, scrape new listings and append them as JSON to the output file"""
    seen = set()
    output.touch(exist_ok=True)
    try:
        while True:
            changed = await scrape_feed(url=url)
            # check deduplication filter
            changed = {k: v for k, v in changed.items() if f"{k}:{v}" not in seen}
            if changed:
                # scrape properties and save to file - 1 property as JSON per line
                properties = await asyncio.gather(scrape_property(url) for url in changed.keys())
                with output.open("a") as f:
                    f.write("\n".join(json.dumps(property) for property in properties))

                # add seen to deduplication filter
                for k, v in changed.items():
                    seen.add(f"{k}:{v}")
            print(f"scraped {len(properties)} properties; waiting {interval} seconds")
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("stopping price tracking")
