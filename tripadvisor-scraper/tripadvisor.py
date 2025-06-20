"""
This is an example web scraper for tripadvisor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-tripadvisor/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import math
import os
import random
import string
from typing import List, Optional, TypedDict, Dict
from urllib.parse import urljoin

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


async def scrape_location_data(query: str) -> List[LocationData]:
    """
    scrape search location data from a given query.
    e.g. "New York" will return us TripAdvisor's location details for this query
    """
    log.info(f"scraping location data: {query}")
    # the graphql payload that defines our search
    # note: that changing values outside of expected ranges can block the web scraper
    payload = json.dumps(
        [
            {
                "variables": {
                    "request": {
                        "query": query,
                        "limit": 10,
                        "scope": "WORLDWIDE",
                        "locale": "en-US",
                        "scopeGeoId": 1,
                        "searchCenter": None,
                        # note: here you can expand to search for differents.
                        "types": [
                            "LOCATION",
                            # "QUERY_SUGGESTION",
                            # "RESCUE_RESULT"
                        ],
                        "locationTypes": [
                            "GEO",
                            "AIRPORT",
                            "ACCOMMODATION",
                            "ATTRACTION",
                            "ATTRACTION_PRODUCT",
                            "EATERY",
                            "NEIGHBORHOOD",
                            "AIRLINE",
                            "SHOPPING",
                            "UNIVERSITY",
                            "GENERAL_HOSPITAL",
                            "PORT",
                            "FERRY",
                            "CORPORATION",
                            "VACATION_RENTAL",
                            "SHIP",
                            "CRUISE_LINE",
                            "CAR_RENTAL_OFFICE",
                        ],
                        "userId": None,
                        "context": {},
                        "enabledFeatures": ["articles"],
                        "includeRecent": True,
                    }
                },
                "query": "84b17ed122fbdbd4",
                "extensions": {"preRegisteredQueryId": "84b17ed122fbdbd4"},
            }
        ]
    )

    # we need to generate a random request ID for this request to succeed
    random_request_id = "".join(random.choice(string.ascii_lowercase + string.digits) for i in range(64))
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "www.tripadvisor.com",
        "Origin": "https://www.tripadvisor.com",
        "X-Requested-With": "XMLHttpRequest",
        "content-type": "application/json",
        "x-requested-by": random_request_id
    }
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://www.tripadvisor.com/data/graphql/ids",
            headers=headers,
            body=payload,
            method="POST",
            **BASE_CONFIG,
        )
    )
    data = json.loads(result.content)
    results = data[0]["data"]["Typeahead_autocomplete"]["results"]
    # strip metadata
    results = [r["details"] for r in results if r['__typename'] == 'Typeahead_LocationItem']
    log.info(f"found {len(results)} results")
    return results


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
        title = box.xpath(".//div[@data-automation='hotel-card-title']/a/h3/text()").getall()[1]
        url = box.css("div[data-automation=hotel-card-title] a::attr(href)").get()
        parsed.append(
            {
                "url": urljoin(result.context["url"], url),  # turn url absolute
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


async def scrape_search(query: str, max_pages: Optional[int] = None) -> List[Preview]:
    """scrape search results of a search query"""
    # first scrape location data and the first page of results
    log.info(f"{query}: scraping first search results page")
    try:
        location_data = (await scrape_location_data(query))[0]  # take first result
    except IndexError:
        log.error(f"could not find location data for query {query}")
        return
    hotel_search_url = "https://www.tripadvisor.com" + location_data["HOTELS_URL"]

    log.info(f"found hotel search url: {hotel_search_url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(hotel_search_url, **BASE_CONFIG))

    # parse first page
    results = parse_search_page(first_page)
    if not results:
        log.error("query {} found no results", query)
        return []

    # extract pagination metadata to scrape all pages concurrently
    page_size = len(results)
    total_results = first_page.selector.xpath("//div[@data-test-target='hotels-main-list']//span").re(r"(\d[\d,]*)")[0]
    total_results = int(total_results.replace(",", ""))
    next_page_url = first_page.selector.css('a[aria-label="Next page"]::attr(href)').get()
    next_page_url = urljoin(hotel_search_url, next_page_url)  # turn url absolute
    total_pages = int(math.ceil(total_results / page_size))
    if max_pages and total_pages > max_pages:
        log.debug(f"{query}: only scraping {max_pages} max pages from {total_pages} total")
        total_pages = max_pages

    # scrape remaining pages
    log.info(f"{query}: found {total_results=}, {page_size=}. Scraping {total_pages} pagination pages")
    other_page_urls = [
        # note: "oa" stands for "offset anchors"
        next_page_url.replace(f"oa{page_size}", f"oa{page_size * i}")
        for i in range(1, total_pages)
    ]
    # we use assert to ensure that we don't accidentally produce duplicates which means something went wrong
    assert len(set(other_page_urls)) == len(other_page_urls)

    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in other_page_urls]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        results.extend(parse_search_page(result))
    return results


def parse_hotel_page(result: ScrapeApiResponse) -> Dict:
    """parse hotel data from hotel pages"""
    selector = result.selector
    basic_data = json.loads(selector.xpath("//script[contains(text(),'aggregateRating')]/text()").get())
    description = selector.xpath("//div[@data-automation='aboutTabDescription']/div/div/div/text()").get()
    amenities = []
    for feature in selector.xpath("//div[contains(@data-test-target, 'amenity')]/text()"):
        amenities.append(feature.get())

    reviews = []
    for review in selector.xpath("//div[contains(text(), 'wrote a review')]/ancestor::div[6]"):
        title = review.xpath(".//div[@data-test-target='review-title']/div/a/text()").get()
        text = "".join(review.xpath(".//span[contains(@data-automation, 'reviewText')]/text()").extract())
        rate = review.xpath(".//*[contains(text(),'of 5 bubbles')]/text()").get()
        rate = (float(rate.replace(" of 5 bubbles", ""))) if rate else None
        trip_data = review.xpath(".//div[1]/div[2]/div[1]/div[2]/text()").get()
        trip_type = review.xpath(".//div[1]/div[2]/div/div[4]/text()").get()

        reviews.append({
            "title": title,
            "text": text,
            "rate": rate,
            "tripDate": trip_data,
            "tripType": trip_type,
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
    if max_review_pages and max_review_pages < total_review_pages:
        total_review_pages = max_review_pages
    
    # scrape all review pages concurrently
    review_urls = [
        # note: "or" stands for "offset reviews"
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-")
        for i in range(1, total_review_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape([
            ScrapeConfig(url, **BASE_CONFIG, render_js=True)
            for url in review_urls
        ]):
        data = parse_hotel_page(result)
        hotel_data["reviews"].extend(data["reviews"])
    log.success(f"scraped one hotel data with {len(hotel_data['reviews'])} reviews")
    return hotel_data
