"""
This is an example web scraper for booking.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-bookingcom/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"

For example use instructions see ./run.py
"""
import json
import math
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urlencode
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Booking.com requires Anti Scraping Protection bypass feature:
    "asp": True,
    "country": "US",
}

class HotelPreview(TypedDict):
    url: str
    name: str
    location: str
    score: str
    review_count: str
    image: str



def parse_search_page(result: ScrapeApiResponse) -> List[HotelPreview]:
    """parse hotel preview data from booking.com search page result"""
    log.info("parsing search page: {}", result.context["url"])
    hotel_previews = []
    for hotel_box in result.selector.xpath('//div[@data-testid="property-card"]'):
        preview = {
            "url": hotel_box.xpath('.//h3/a[@data-testid="title-link"]/@href').get("").split("?")[0],
            "name": hotel_box.xpath('.//h3/a[@data-testid="title-link"]/div/text()').get(""),
            "location": hotel_box.xpath('.//span[@data-testid="address"]/text()').get(""),
            "score": hotel_box.xpath('.//div[@data-testid="review-score"]/div/text()').get(),
            "review_count": hotel_box.xpath('.//div[@data-testid="review-score"]/div[2]/div[2]/text()').get(""),
            "image": hotel_box.xpath('.//img[@data-testid="image"]/@src').get(),
        }
        if preview["score"]:
            preview["score"] = float(preview["score"])
        if preview["review_count"]:
            preview["review_count"] = int(preview["review_count"].replace(",", "").split()[0])
        else:
            preview["review_count"] = 0
        hotel_previews.append(preview)
    return hotel_previews


class Location(TypedDict):
    b_max_los_data: dict
    b_show_entire_homes_checkbox: bool
    cc1: str
    cjk: bool
    dest_id: str
    dest_type: str
    label: str
    label1: str
    label2: str
    labels: list
    latitude: float
    lc: str
    longitude: float
    nr_homes: int
    nr_hotels: int
    nr_hotels_25: int
    photo_uri: str
    roundtrip: str
    rtl: bool
    value: str


class LocationSuggestions(TypedDict):
    results: List[Location]



async def search_location_suggestions(query: str) -> LocationSuggestions:
    """scrape booking.com location suggestions to find location details for search scraping"""
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://accommodations.booking.com/autocomplete.json",
            method="POST",
            headers={
                "Origin": "https://www.booking.com",
                "Referer": "https://www.booking.com/",
                "Content-Type": "text/plain;charset=UTF-8",
            },
            body=f'{{"query":"{query}","pageview_id":"","aid":800210,"language":"en-us","size":5}}',
        )
    )
    data = json.loads(result.content)
    return data


async def scrape_search(
    query,
    checkin: str = "",  # e.g. 2023-05-30
    checkout: str = "",  # e.g. 2023-06-26
    number_of_rooms=1,
    max_pages: Optional[int] = None,
) -> List[HotelPreview]:
    """Scrape booking.com search"""
    log.info(f"scraping search for {query} {checkin}-{checkout}")
    # first we must find destination details from provided query
    # for that scrape suggestions from booking.com autocomplete and take the first one
    location_suggestions = await search_location_suggestions(query)
    destination = location_suggestions["results"][0]
    search_url = "https://www.booking.com/searchresults.en-gb.html?" + urlencode(
        {
            "ss": destination["value"],
            "ssne": destination["value"],
            "ssne_untouched": destination["value"],
            "checkin": checkin,
            "checkout": checkout,
            "no_rooms": number_of_rooms,
            "dest_id": destination["dest_id"],
            "dest_type": destination["dest_type"],
            "efdco": 1,
            "group_adults": 1,
            "group_children": 0,
            "lang": "en-gb",
            "sb": 1,
            "sb_travel_purpose": "leisure",
            "src": "index",
            "src_elem": "sb",
        }
    )
    # first scrape the first page and find total amount of pages
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(search_url, **BASE_CONFIG))
    hotel_previews = parse_search_page(first_page)
    # parse total amount of pages from heading1 text, e.g: "London: 1,232 properties found"
    _total_results = int(first_page.selector.css("h1").re(r"([\d,]+) properties found")[0].replace(",", ""))
    _page_size = 25
    total_pages = math.ceil(_total_results / _page_size)
    if max_pages and total_pages > max_pages:
        total_pages = max_pages
    log.info(f"scraped {len(hotel_previews)} from 1st result page. {total_pages} to go")
    # now scrape other pages concurrently
    to_scrape = [
        ScrapeConfig(search_url.replace("offset=0", f"offset={page * _page_size}"), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(result, ScrapflyScrapeError):
            hotel_previews.extend(parse_search_page(result))
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    log.info(f"scraped {len(hotel_previews)} total hotel previews for {query} {checkin}-{checkout}")
    return hotel_previews


class PriceData(TypedDict):
    checkin: str
    min_length_of_stay: int
    avg_price_pretty: str
    available: int
    avg_price_raw: float
    length_of_stay: int
    price_pretty: str
    price: float


class Hotel(TypedDict):
    url: str
    id: str
    description: str
    address: str
    images: List[str]
    lat: str
    lng: str
    features: Dict[str, List[str]]
    price: List[PriceData]


def parse_hotel(result: ScrapeApiResponse) -> Hotel:
    log.debug("parsing hotel page: {}", result.context["url"])
    sel = result.selector

    features = defaultdict(list)
    for box in sel.xpath('//div[@data-testid="property-section--content"]/div[2]/div'):
        type_ = box.xpath('.//span[contains(@data-testid, "facility-group-icon")]/../text()').get()
        feats = [f.strip() for f in box.css("li ::text").getall() if f.strip()]
        features[type_] = feats

    css = lambda selector, sep="": sep.join(sel.css(selector).getall()).strip()
    lat, lng = sel.css(".show_map_hp_link::attr(data-atlas-latlng)").get("0,0").split(",")
    data = {
        "url": result.context["url"],
        "id": re.findall(r"b_hotel_id:\s*'(.+?)'", result.content)[0],
        "title": sel.css("h2::text").get(),
        "description": css("div#property_description_content ::text", "\n"),
        "address": css(".hp_address_subtitle::text"),
        "images": sel.css("a.bh-photo-grid-item>img::attr(src)").getall(),
        "lat": lat,
        "lng": lng,
        "features": dict(features),
    }
    return data


async def scrape_hotel(url: str, checkin: str, price_n_days=61) -> Hotel:
    """
    Scrape Booking.com hotel data and pricing information.
    """
    # first scrape hotel info details
    # note: we are using scrapfly session here as both info and pricing requests
    #       have to be from the same IP address/session
    if BASE_CONFIG.get("cache"):
        raise Exception("scrapfly cache cannot be used with sessions when scraping hotel data")
    log.info(f"scraping hotel {url} {checkin} with {price_n_days} days of pricing data")
    session = str(uuid4()).replace("-", "")
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            session=session,
            **BASE_CONFIG,
        )
    )
    hotel = parse_hotel(result)

    # To scrape price we'll be calling Booking.com's graphql service
    # in particular we'll be calling AvailabilityCalendar query
    # first, extract hotel variables:
    _hotel_country = re.findall(r'hotelCountry:\s*"(.+?)"', result.content)[0]
    _hotel_name = re.findall(r'hotelName:\s*"(.+?)"', result.content)[0]
    _csrf_token = re.findall(r"b_csrf_token:\s*'(.+?)'", result.content)[0]
    # then create graphql query
    gql_body = json.dumps(
        {
            "operationName": "AvailabilityCalendar",
            # hotel varialbes go here
            # you can adjust number of adults, room number etc.
            "variables": {
                "input": {
                    "travelPurpose": 2,
                    "pagenameDetails": {
                        "countryCode": _hotel_country,
                        "pagename": _hotel_name,
                    },
                    "searchConfig": {
                        "searchConfigDate": {
                            "startDate": checkin,
                            "amountOfDays": price_n_days,
                        },
                        "nbAdults": 2,
                        "nbRooms": 1,
                    },
                }
            },
            "extensions": {},
            # this is the query itself, don't alter it
            "query": "query AvailabilityCalendar($input: AvailabilityCalendarQueryInput!) {\n  availabilityCalendar(input: $input) {\n    ... on AvailabilityCalendarQueryResult {\n      hotelId\n      days {\n        available\n        avgPriceFormatted\n        checkin\n        minLengthOfStay\n        __typename\n      }\n      __typename\n    }\n    ... on AvailabilityCalendarQueryError {\n      message\n      __typename\n    }\n    __typename\n  }\n}\n",
        },
        # note: this removes unnecessary whitespace in JSON output
        separators=(",", ":"),
    )
    # scrape booking graphql
    result_price = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            "https://www.booking.com/dml/graphql?lang=en-gb",
            method="POST",
            body=gql_body,
            session=session,
            # note that we need to set headers to avoid being blocked
            headers={
                "content-type": "application/json",
                "x-booking-csrf-token": _csrf_token,
                "referer": result.context["url"],
                "origin": "https://www.booking.com",
            },
            **BASE_CONFIG,
        )
    )
    price_data = json.loads(result_price.content)
    hotel["price"] = price_data["data"]["availabilityCalendar"]["days"]
    return hotel
