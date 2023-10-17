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
import re
import string
from typing import List, Optional, TypedDict
from urllib.parse import urljoin

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Tripadvisor.com requires Anti Scraping Protection bypass feature:
    "asp": True,
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
        "X-Requested-By": random_request_id,
        "Referer": "https://www.tripadvisor.com/Hotels",
        "Origin": "https://www.tripadvisor.com",
        "Content-Type": "application/json",
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
    for box in result.selector.css("span.listItem"):
        title = box.css("div[data-automation=hotel-card-title] a ::text").getall()[1]
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
    total_results = first_page.selector.xpath("//span/text()").re("(\d*\,*\d+) properties")[0]
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


def extract_page_manifest(html):
    """extract javascript state data hidden in TripAdvisor HTML pages"""
    data = re.findall(r"pageManifest:({.+?})};", html, re.DOTALL)[0]
    return json.loads(data)


def extract_named_urql_cache(urql_cache: dict, pattern: str):
    """extract named urql response cache from hidden javascript state data"""
    data = json.loads(next(v["data"] for k, v in urql_cache.items() if pattern in v["data"]))
    return data


class Review(TypedDict):
    id: str
    date: str
    rating: str
    title: str
    text: str
    votes: int
    url: str
    language: str
    platform: str
    author_id: str
    author_name: str
    author_username: str


def parse_reviews(result: ScrapeApiResponse) -> Review:
    """Parse reviews from a review page"""
    page_data = extract_page_manifest(result.content)
    review_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"reviewListPage"')
    parsed = []
    # review data contains loads of information, let's parse only the basic in this tutorial
    for review in review_cache["locations"][0]["reviewListPage"]["reviews"]:
        parsed.append(
            {
                "id": review["id"],
                "date": review["publishedDate"],
                "rating": review["rating"],
                "title": review["title"],
                "text": review["text"],
                "votes": review["helpfulVotes"],
                "url": review["route"]["url"],
                "language": review["language"],
                "platform": review["publishPlatform"],
                "author_id": review["userProfile"]["id"],
                "author_name": review["userProfile"]["displayName"],
                "author_username": review["userProfile"]["username"],
            }
        )
    return parsed


class Hotel(TypedDict):
    name: str
    id: str
    type: str
    description: str
    rating: float
    rating_count: int
    features: List[str]
    stars: int


def parse_hotel_info(data: dict) -> Hotel:
    """parse hotel data from TripAdvisor javascript state to something more readable"""
    parsed = {}
    # there's a lot of information in hotel data, in this tutorial let's extract the basics:
    parsed["name"] = data["name"]
    parsed["id"] = data["locationId"]
    parsed["type"] = data["accommodationType"]
    parsed["description"] = data["locationDescription"]
    parsed["rating"] = data["reviewSummary"]["rating"]
    parsed["rating_count"] = data["reviewSummary"]["count"]
    # for hotel "features" lets just extract the names:
    parsed["features"] = []
    for amenity_type, values in data["detail"]["hotelAmenities"]["highlightedAmenities"].items():
        for value in values:
            parsed["features"].append(f"{amenity_type}_{value['amenityNameLocalized'].lower()}")

    if star_rating := data["detail"]["starRating"]:
        parsed["stars"] = star_rating[0]["tagNameLocalized"]
    return parsed


class HotelAllData(TypedDict):
    info: Hotel
    reviews: List[Review]
    price: dict


async def scrape_hotel(url: str, max_review_pages: Optional[int] = None) -> HotelAllData:
    """Scrape all hotel data: information, pricing and reviews"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    page_data = extract_page_manifest(first_page.content)

    # price data keys are dynamic first we need to find the full key name
    _pricing_key = next(
        (key for key in page_data["redux"]["api"]["responses"] if "/hotelDetail" in key and "/heatMap" in key)
    )
    pricing_details = page_data["redux"]["api"]["responses"][_pricing_key]["data"]["items"]

    # We can extract data from Graphql cache embeded in the page
    # TripAdvisor is using: https://github.com/FormidableLabs/urql as their graphql client
    hotel_cache = extract_named_urql_cache(page_data["urqlCache"]["results"], '"locationDescription"')
    hotel_info = hotel_cache["locations"][0]

    # for reviews we first need to scrape multiple pages
    # so, first let's find total amount of pages
    total_reviews = hotel_info["reviewSummary"]["count"]
    _review_page_size = 10
    total_review_pages = int(math.ceil(total_reviews / _review_page_size))
    if max_review_pages and total_review_pages > max_review_pages:
        total_review_pages = max_review_pages
    # then we can scrape all review pages concurrently
    # note: in review url "or" stands for "offset reviews"
    review_urls = [
        # note: "or" stands for "offset reviews"
        url.replace("-Reviews-", f"-Reviews-or{_review_page_size * i}-")
        for i in range(2, total_review_pages + 1)
    ]
    assert len(set(review_urls)) == len(review_urls)
    reviews = parse_reviews(first_page)
    async for result in SCRAPFLY.concurrent_scrape([ScrapeConfig(url, BASE_CONFIG) for url in review_urls]):
        reviews.extend(parse_reviews(result))

    return {
        "price": pricing_details,
        "info": parse_hotel_info(hotel_info),
        "url": first_page.context["url"],
        "reviews": reviews,
    }
