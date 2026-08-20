"""
This is an example web scraper for AutoScout24.com using Scrapfly
https://scrapfly.io/blog/posts/how-to-scrape-autoscout24

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Optional, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # AutoScout24 requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    # no render_js: the listing and offer data is in the server rendered __NEXT_DATA__ payload,
    # so rendering only adds cost and a browser page load to wait on
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class CarListing(TypedDict, total=False):
    """Car listing from search results"""
    price: Dict[str, str]
    url: str
    location: Optional[Dict[str, Optional[str]]]
    vehicle: Optional[Dict[str, Any]]
    tracking: Optional[Dict[str, Any]]
    vehicleDetails: Optional[List[Dict[str, Any]]]


class CarDetails(TypedDict, total=False):
    """Detailed car information from car page"""
    
    price: Dict[str, str]
    vehicle: Optional[Dict[str, Any]]
    seller: Optional[Dict[str, Any]]
    location: Optional[Dict[str, Any]]


def change_page(url: str, page: int) -> str:
    """set the page number on an AutoScout24 search url, replacing it when one is already there"""
    parts = urlsplit(url)
    # the multi select filters repeat a key (eq=1&eq=15), so the pairs stay a list instead of
    # becoming a dict, which would keep only the last value of each filter
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "page"]
    query.append(("page", str(page)))
    return urlunsplit(parts._replace(query=urlencode(query), fragment=""))


def parse_listings(result: ScrapeApiResponse) -> Tuple[List[CarListing], int]:
    """Parse AutoScout24 listings page for car listings and the number of available pages"""
    selector = result.selector

    script_data = selector.css("script#__NEXT_DATA__::text").get()
    if not script_data:
        log.warning(f"could not find __NEXT_DATA__ on page: {result.context['url']}")
        return [], 0
    page_props = json.loads(script_data).get("props", {}).get("pageProps", {})
    listings = page_props.get("listings") or []
    if not listings:
        # an upstream error page still ships a __NEXT_DATA__ blob, so an empty payload
        # has to be logged or a failed page looks exactly like a page of zero results
        log.warning(f"no listings in __NEXT_DATA__ on page: {result.context['url']}")
    return listings, page_props.get("numberOfPages") or 0


def parse_car_details(result: ScrapeApiResponse) -> Optional[CarDetails]:
    """Parse car detail page"""
    selector = result.selector
    script_data = selector.css("script#__NEXT_DATA__::text").get()
    if not script_data:
        log.warning(f"could not find __NEXT_DATA__ on page: {result.context['url']}")
        return None
    data = json.loads(script_data)
    car_data = data.get("props", {}).get("pageProps", {}).get("listingDetails") or None
    if not car_data:
        log.warning(f"no listing details in __NEXT_DATA__ on page: {result.context['url']}")
    return car_data


async def scrape_listings(url: str, max_pages: int = 3) -> List[CarListing]:
    """Scrape car listings from AutoScout24 search/category page (with pagination)"""
    # page 1 goes through change_page too, otherwise a url that already carries ?page=5 is
    # scraped once at page 5 and then continued from page 2
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(change_page(url, 1), **BASE_CONFIG))
    first_listings, total_pages = parse_listings(first_page)
    if not first_listings:
        log.error(f"the first page of {url} returned no listings, giving up on the remaining pages")
        return []

    all_listings: List[CarListing] = []
    seen = set()

    def collect(page_listings: List[CarListing]) -> int:
        """add the listings of one page, dropping the ones already collected"""
        added = 0
        for listing in page_listings:
            listing_url = listing.get("url")
            if listing_url and listing_url in seen:
                continue
            seen.add(listing_url)
            all_listings.append(listing)
            added += 1
        return len(page_listings) - added

    collect(first_listings)
    last_page = min(max_pages, total_pages) if total_pages else max_pages
    log.info(f"scraped page 1 of {url}: {len(all_listings)} listings, {total_pages} pages available")

    page_numbers = list(range(2, last_page + 1))
    other_pages = [ScrapeConfig(change_page(url, page), **BASE_CONFIG) for page in page_numbers]
    scraped_urls = set()
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        # concurrent_scrape yields whatever the request raised instead of raising it, and those
        # errors are not all one class, so only a real response may be touched
        if not isinstance(response, ScrapeApiResponse):
            log.error(f"failed to scrape a listings page, got: {response}")
            continue
        page_listings, _ = parse_listings(response)
        if not page_listings:
            continue
        # config holds the requested url, context holds the final one, which is the homepage
        # whenever the page bounced
        scraped_urls.add(response.config["url"])
        # AutoScout24 repeats boosted listings across pages, so they are dropped by url
        duplicates = collect(page_listings)
        log.info(f"scraped {response.context['url']}: {len(page_listings)} listings, {duplicates} duplicates dropped")

    # under concurrency AutoScout24 sometimes bounces a page to the homepage, which carries no
    # listings, so the pages that came back empty get one more sequential attempt
    for page in page_numbers:
        page_url = change_page(url, page)
        if page_url in scraped_urls:
            continue
        log.info(f"retrying page {page} of {url}")
        try:
            retry = await SCRAPFLY.async_scrape(ScrapeConfig(page_url, **BASE_CONFIG))
        except ScrapflyError as error:
            log.error(f"retry of page {page} failed, got: {error}")
            continue
        page_listings, _ = parse_listings(retry)
        if page_listings:
            collect(page_listings)
        else:
            log.error(f"page {page} of {url} returned no listings after a retry")

    log.success(f"scraped {len(all_listings)} car listings from {url}")
    return all_listings


async def scrape_car_details(urls: List[str]) -> List[CarDetails]:
    """Scrape detailed car information from car page"""
    all_car_details = []
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]

    scraped_urls = set()
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(response, ScrapeApiResponse):
            log.error(f"failed to scrape a car details page, got: {response}")
            continue
        car_details = parse_car_details(response)
        # an unparsed page must not leave a null in the results
        if car_details:
            scraped_urls.add(response.config["url"])
            all_car_details.append(car_details)

    # a page can bounce to the homepage under concurrency, so the missing ones get one more try
    for url in urls:
        if url in scraped_urls:
            continue
        log.info(f"retrying {url}")
        try:
            retry = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        except ScrapflyError as error:
            log.error(f"retry of {url} failed, got: {error}")
            continue
        car_details = parse_car_details(retry)
        if car_details:
            all_car_details.append(car_details)

    log.success(f"scraped {len(all_car_details)} car details of {len(urls)} requested")
    return all_car_details
