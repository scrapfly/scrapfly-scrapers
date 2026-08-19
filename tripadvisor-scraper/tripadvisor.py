"""
This is an example web scraper for tripadvisor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-tripadvisor/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import math
import os
import re
import random
import string
from typing import List, Optional, TypedDict, Dict
from urllib.parse import urljoin, urlparse, urlunparse

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # Tripadvisor.com requires Anti Scraping Protection bypass feature:
    "asp": True,
    # set the proxy location to US
    "country": "US",
}


class LocationData(TypedDict):
    """result dataclass for tripadvisor location data"""
    localizedName: str
    url: str
    HOTELS_URL: str
    ATTRACTIONS_URL: str
    RESTAURANTS_URL: str
    placeType: str
    latitude: float
    longitude: float


def parse_location(item: Dict) -> LocationData:
    """flatten one typeahead location node into the result shape"""
    info = ((item.get("contentLocationNode") or {}).get("detail") or {}).get("info") or {}
    # the section links come as nested "barcelona hotels" style suggestions
    section_urls = {
        nested.get("buCategory"): (nested.get("route") or {}).get("url")
        for nested in item.get("nestedResults") or []
    }
    return {
        "localizedName": info.get("localizedName"),
        "url": (info.get("primaryRoute") or {}).get("webLinkUrl"),
        "HOTELS_URL": section_urls.get("HOTELS"),
        "ATTRACTIONS_URL": section_urls.get("ATTRACTIONS"),
        "RESTAURANTS_URL": section_urls.get("RESTAURANTS"),
        "placeType": info.get("placeType"),
        "latitude": info.get("latitude"),
        "longitude": info.get("longitude"),
    }


async def scrape_location_data(query: str) -> List[LocationData]:
    """
    scrape search location data from a given query.
    e.g. "New York" will return us TripAdvisor's location details for this query
    """
    log.info(f"scraping location data: {query}")
    # the graphql payload that defines our search
    # note: that changing values outside of expected ranges can block the web scraper
    
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://www.tripadvisor.com/",
            **BASE_CONFIG,
            render_js=True,
            js_scenario=[
                {
                    "wait_for_selector": {
                        "selector": "//input[@type='search']",
                        "timeout": 5000
                    }
                },
                {
                    "fill": {
                        "clear": False,
                        "selector": "//input[@type='search']",
                        "value": query
                    }
                },
                {
                    "wait": 5000
                }
            ]
        )
    )

    # extract the json data from the graphql call
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    graphql_calls = []
    for call in _xhr_calls:
        if "/data/graphql/ids" not in call["url"]:
            continue
        try:
            body = json.loads(call["response"]["body"])
        except (TypeError, ValueError):
            continue  # not every batched graphql call answers with json
        if isinstance(body, list) and body and isinstance(body[0], dict):
            graphql_calls.append(body)
    location_data_call = [f for f in graphql_calls if "Typeahead_autocomplete" in f[0].get("data", {})]
    if not location_data_call:
        log.error(f"no typeahead response captured for query: {query}")
        return []
    # one typeahead call fires per keystroke, so only the last answers the
    # full query - the earlier ones answer "B", "Ba", "Bar"...
    results = location_data_call[-1][0]["data"]["Typeahead_autocomplete"]["results"]
    location_data = [
        parse_location(item) for item in results
        if item.get("__typename") == "Typeahead_LocationItem" and item.get("contentLocationNode")
    ]
    # a node without the detail block carries no usable fields
    location_data = [item for item in location_data if item["localizedName"]]
    if not location_data:
        log.error(f"no locations parsed for query: {query} - the typeahead payload shape changed")
    log.info(f"found {len(location_data)} results")
    return location_data

PAGE_OFFSET_RE = re.compile(r"-oa(\d+)-")


def page_offset(url: str) -> int:
    """read the "offset anchor" from a search url, 0 when it has none"""
    match = PAGE_OFFSET_RE.search(url)
    return int(match.group(1)) if match else 0


class Preview(TypedDict):
    url: str
    name: str


def parse_search_page(result: ScrapeApiResponse) -> List[Preview]:
    """parse result previews from TripAdvisor search page"""
    log.info(f"parsing search page: {result.context['url']}")
    parsed = []
    # Search results are contain in boxes which can be in two locations.
    # this is location #1:
    for box in result.selector.xpath("//div[@data-test-target='hotels-main-list']//ol/li"):
        title_list = box.xpath(".//div[@data-automation='hotel-card-title']/a/h3/text()").getall()
        title = title_list[1] if len(title_list) > 1 else (title_list[0] if title_list else None)
        url = box.css("div[data-automation=hotel-card-title] a::attr(href)").get()
        if not url:
            continue  # without a link the entry would resolve to the search page itself
        parsed_url = urlparse(urljoin(result.context["url"], url))
        clean_url = urlunparse(parsed_url._replace(query="", fragment=""))
        parsed.append(
            {
                "url": clean_url,
                "name": title,
            }
        )
    if parsed:
        return parsed
    # location #2
    for box in result.selector.css("div.listing_title>a"):
        parsed.append(
            {
                "url": urljoin(result.context["url"], box.xpath("@href").get()),  # turn url absolute
                "name": box.xpath("text()").get("").split(". ")[-1],
            }
        )
    return parsed


async def scrape_search(search_url: str, max_pages: Optional[int] = None) -> List[Preview]:
    """scrape search results of a search query"""
    # first scrape location data and the first page of results
    log.info(f"{search_url}: scraping first search results page")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(search_url, **BASE_CONFIG))

    # sponsored listings can repeat, so keep urls unique
    results = []
    seen = set()
    for item in parse_search_page(first_page):
        if item["url"] not in seen:
            seen.add(item["url"])
            results.append(item)
    if not results:
        log.error("query {} found no results", search_url)
        return []

    next_page_url = first_page.selector.css('a[aria-label="Next page"]::attr(href)').get()
    if not next_page_url:
        log.info(f"{search_url}: single page of results")
        return results
    next_page_url = urljoin(search_url, next_page_url)  # turn url absolute

    # the offset step comes from the site's own next-page link. it is not the
    # number of parsed cards - sponsored listings inflate that count
    first_offset = page_offset(search_url)
    step = page_offset(next_page_url) - first_offset
    if step <= 0:
        log.warning(f"{search_url}: could not read the pagination step, stopping after one page")
        return results

    # note: "oa" stands for "offset anchors"
    total_results = first_page.selector.re_first(r"of ([\d,]+) places to stay")
    total_results = int(total_results.replace(",", "")) if total_results else 0
    if total_results:
        total_pages = max(1, math.ceil((total_results - first_offset) / step))
    else:
        # the total is a copy-specific string, so fall back to the cap
        log.warning(f"{search_url}: could not read the result total")
        total_pages = max_pages if max_pages else 1
    if max_pages is not None and total_pages > max_pages:
        log.debug(f"{search_url}: only scraping {max_pages} max pages from {total_pages} total")
        total_pages = max_pages

    # scrape remaining pages
    log.info(f"{search_url}: found {total_results=}, {step=}. Scraping {total_pages} pagination pages")
    other_page_urls = [
        PAGE_OFFSET_RE.sub(f"-oa{first_offset + step * i}-", next_page_url)
        for i in range(1, total_pages)
    ]
    # we use assert to ensure that we don't accidentally produce duplicates which means something went wrong
    assert len(set(other_page_urls)) == len(other_page_urls)

    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in other_page_urls]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(result, ScrapeApiResponse):
            log.warning(f"skipping a search page: {result}")
            continue
        for item in parse_search_page(result):
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)
    return results


def parse_review_text(block) -> Optional[str]:
    """join a review text block - paragraphs are split by <br> into separate nodes"""
    parts = block.xpath(".//span[contains(@class, 'JguWG')]//span/text()").getall()
    return "\n".join(part.strip() for part in parts if part.strip()) or None


def parse_hotel_page(result: ScrapeApiResponse) -> Dict:
    """parse hotel data from hotel pages"""
    selector = result.selector
    basic_data = json.loads(selector.xpath("//script[contains(text(),'aggregateRating')]/text()").get())
    description = selector.xpath("//div[@data-automation='aboutTabDescription']/div/div/div/text()").get()
    # merge both - JSON-LD carries the property amenities, the DOM the room features
    amenities = [f["name"] for f in basic_data.get("amenityFeatures", []) if f.get("name")]
    for feature in selector.xpath("//div[contains(@data-test-target, 'amenity')]"):
        # .//text() because some amenity names are wrapped in a link
        name = "".join(feature.xpath(".//text()").getall()).strip()
        if name and name not in amenities:
            amenities.append(name)

    reviews = []
    # match on the attribute alone - these element names change with every redesign
    for review in selector.xpath("//*[@data-test-target='HR_CC_CARD']"):
        title = "".join(review.xpath(".//*[@data-test-target='review-title']//text()").getall()).strip() or None
        blocks = review.xpath(".//div[contains(@class, 'fIrGe')]")
        text = parse_review_text(blocks[0]) if blocks else None
        # the reply is a second block, trusted only when the card headers it
        has_reply = bool(review.xpath(".//*[contains(text(), 'Response from')]"))
        owner_response = parse_review_text(blocks[1]) if has_reply and len(blocks) > 1 else None
        rate = review.xpath(".//*[contains(text(),'of 5 bubbles')]/text()").get()
        rate = (float(rate.replace(" of 5 bubbles", ""))) if rate else None
        # .//text() because these values are split by a comment node ("Traveled <!-- -->as a couple")
        trip_data = "".join(review.xpath(".//span[contains(text(), 'Date of stay:')]/parent::div/following-sibling::span//text()").getall()).strip() or None
        trip_type = "".join(review.xpath(".//span[contains(text(), 'Trip type:')]/parent::div/following-sibling::span//text()").getall()).strip() or None

        reviews.append({
            "title": title,
            "text": text,
            "rate": rate,
            "tripDate": trip_data,
            "tripType": trip_type,
            "ownerResponse": owner_response,
        })

    return {
        "basic_data": basic_data,
        "description": description,
        "featues": amenities,
        "reviews": reviews
    }


async def scrape_hotel(url: str, max_review_pages: Optional[int] = None) -> Dict:
    """Scrape hotel data and reviews"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True))
    hotel_data = parse_hotel_page(first_page)

    # get the number of total review pages
    _review_page_size = 10
    total_reviews = int(hotel_data["basic_data"]["aggregateRating"]["reviewCount"])
    total_review_pages = math.ceil(total_reviews / _review_page_size)

    # get the number of review pages to scrape
    if max_review_pages is not None and max_review_pages < total_review_pages:
        total_review_pages = max_review_pages
    
    # scrape all review pages concurrently
    review_urls = [
        # note: "or" stands for "offset reviews"
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-")
        # the first page is already scraped above, so it counts towards the cap
        for i in range(1, total_review_pages)
    ]
    async for result in SCRAPFLY.concurrent_scrape([
            ScrapeConfig(url, **BASE_CONFIG, render_js=True)
            for url in review_urls
        ]):
        # concurrent_scrape yields errors instead of raising them
        if not isinstance(result, ScrapeApiResponse):
            log.warning(f"skipping a review page: {result}")
            continue
        data = parse_hotel_page(result)
        hotel_data["reviews"].extend(data["reviews"])
    if hotel_data["reviews"] and not any(r["title"] or r["text"] for r in hotel_data["reviews"]):
        raise RuntimeError(
            f"parsed {len(hotel_data['reviews'])} reviews with no title or text - the review selectors are stale"
        )
    log.success(f"scraped one hotel data with {len(hotel_data['reviews'])} reviews")
    return hotel_data
