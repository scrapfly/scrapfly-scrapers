"""
This is an example web scraper for yellowpages.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List, Optional
from urllib.parse import urlencode
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass yellowpages.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "proxy_pool": "public_residential_pool",
}


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse yellowpages.com search page for business preview data"""
    selector = response.selector
    script_data = selector.xpath(
        "//script[@type='application/ld+json'][2]/text()"
    ).get()
    data = json.loads(script_data)
    total_pages = int(selector.css(".pagination>span::text").re(r"of (\d+)")[0])
    return {"data": data, "total_pages": total_pages}


def parse_page(response: ScrapeApiResponse) -> Dict:
    """parse business data from business page"""
    sel = response.selector
    first = lambda css: sel.css(css).get("").strip()
    many = lambda css: [value.strip() for value in sel.css(css).getall()]
    together = lambda css, sep=" ": sep.join(sel.css(css).getall())

    # to parse working hours we need to do a bit of complex string parsing
    def _parse_datetime(values: List[str]):
        """
        parse datetime from yellow pages datetime strings

        >>> _parse_datetime(["Fr-Sa 12:00-22:00"])
        {'Fr': '12:00-22:00', 'Sa': '12:00-22:00'}
        >>> _parse_datetime(["Fr 12:00-22:00"])
        {'Fr': '12:00-22:00'}
        >>> _parse_datetime(["Fr-Sa 12:00-22:00", "We 10:00-18:00"])
        {'Fr': '12:00-22:00', 'Sa': '12:00-22:00', 'We': '10:00-18:00'}
        """

        WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        results = {}
        for text in values:
            days, hours = text.split(" ")
            if "-" in days:
                day_start, day_end = days.split("-")
                for day in WEEKDAYS[
                    WEEKDAYS.index(day_start) : WEEKDAYS.index(day_end) + 1
                ]:
                    results[day] = hours
            else:
                results[days] = hours
        return results

    return {
        "name": first("h1.business-name::text"),
        "categories": many(".categories>a::text"),
        "rating": first(".ratings div::attr(class)").split(" ", 1)[-1],
        "ratingCount": first(".ratings .count::text").strip("()"),
        "phone": first(".phone::attr(href)").replace("(", "").replace(")", ""),
        "website": first(".website-link::attr(href)"),
        "address": together(".address::text"),
        "workingHours": _parse_datetime(many(".open-details tr time::attr(datetime)")),
    }


async def scrape_search(
    query: str, location: Optional[str] = None, max_pages: Optional[int] = None
):
    """scrape yellowpages.com for listings"""

    def make_search_url(page):
        base_url = "https://www.yellowpages.com/search?"
        parameters = {
            "search_terms": query,
            "geo_location_terms": location,
            "page": page,
        }
        return base_url + urlencode(parameters)

    log.info(f'scraping "{query}" in "{location}"')
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(make_search_url(1), **BASE_CONFIG)
    )
    result = parse_search(first_page)
    search_data = result["data"]

    # find total page count
    total_pages = result["total_pages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # next, scrape the remaining search pages concurrently
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    other_pages = [
        ScrapeConfig(make_search_url(page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_search(response)["data"]
        search_data.extend(data)
    log.success(f"scraped {len(search_data)} listings from search pages")
    return search_data


async def scrape_pages(urls: List[str]) -> List[Dict]:
    """scrape yellowpages business pages"""
    # add the business pages to a scraping list
    result = []
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        result.append(parse_page(response))
    log.success(f"scraped {len(result)} business pages")
    return result
