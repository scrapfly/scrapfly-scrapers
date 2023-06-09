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
    log.debug("parsing search page: {}", result.context["url"])
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


async def scrape_search(
    query,
    checkin: str = "",  # e.g. 2023-05-30
    checkout: str = "",  # e.g. 2023-06-26
    number_of_rooms=1,
    max_pages: Optional[int] = None,
) -> List[HotelPreview]:
    """Scrape booking.com search"""
    checkin_year, checking_month, checking_day = checkin.split("-") if checkin else ("", "", "")
    checkout_year, checkout_month, checkout_day = checkout.split("-") if checkout else ("", "", "")
    log.info(f"scraping search for {query} {checkin}-{checkout}")
    search_url = "https://www.booking.com/searchresults.html?" + urlencode(
        {
            "ss": query,
            "checkin_year": checkin_year,
            "checkin_month": checking_month,
            "checkin_monthday": checking_day,
            "checkout_year": checkout_year,
            "checkout_month": checkout_month,
            "checkout_monthday": checkout_day,
            "no_rooms": number_of_rooms,
            "offset": 0,
        }
    )
    # first scrape the first page and find total amount of pages
    first_page = await scrapfly.async_scrape(ScrapeConfig(search_url, **BASE_CONFIG))
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
    async for result in scrapfly.concurrent_scrape(to_scrape):
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


async def scrape_hotel(url: str, checkin: str, price_n_days=30) -> Hotel:
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
    result = await scrapfly.async_scrape(ScrapeConfig(url, session=session, **BASE_CONFIG))
    hotel = parse_hotel(result)
    # csrf token is required to scrape the hidden pricing API
    # it can be found hidden in the HTML body
    csrf_token = re.findall(r"b_csrf_token:\s*'(.+?)'", result.content)[0]

    # body for hidden pricing API
    # note this can be customized to your needs like adult visitor number, pets etc.
    data = {
        "name": "hotel.availability_calendar",
        "result_format": "price_histogram",
        "hotel_id": hotel["id"],
        "search_config": json.dumps(
            {
                # we can adjust pricing configuration here but this is the default
                "b_adults_total": 2,
                "b_nr_rooms_needed": 1,
                "b_children_total": 0,
                "b_children_ages_total": [],
                "b_is_group_search": 0,
                "b_pets_total": 0,
                "b_rooms": [{"b_adults": 2, "b_room_order": 1}],
            }
        ),
        "checkin": checkin,
        "n_days": price_n_days,
        "respect_min_los_restriction": 1,
        "los": 1,
    }
    result = await scrapfly.async_scrape(
        ScrapeConfig(
            url="https://www.booking.com/fragment.json?cur_currency=usd",
            method="POST",
            data=data,
            headers={"X-Booking-CSRF": csrf_token},  # add CSRF token as header
            session=session,  # note: we need to use the same IP, so use scrapfly session
            **BASE_CONFIG,
        )
    )
    hotel["price"] = []
    for day in json.loads(result.content)["data"]['days']:
        hotel["price"].append({
            # get rid of b_ prefix
            k[2:] if k.startswith("b_") else k: v 
            for k, v in day.items()
        })
    return hotel
