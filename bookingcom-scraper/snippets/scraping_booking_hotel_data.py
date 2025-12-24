import os
import re
import json
import asyncio

from uuid import uuid4
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_hotel(result: ScrapeApiResponse) -> Dict:
    print(f"parsing hotel page: {result.context['url']}")
    sel = result.selector

    features = defaultdict(list)
    for box in sel.xpath('//div[@data-testid="property-section--content"]/div[2]/div'):
        type_ = box.xpath('.//span[contains(@data-testid, "facility-group-icon")]/../text()').get()
        if not type_:
            continue
        feats = [f.strip() for f in box.css("li ::text").getall() if f.strip()]
        features[type_] = feats

    css = lambda selector, sep="": sep.join(sel.css(selector).getall()).strip()
    xpath = lambda selector, sep="": sep.join(sel.xpath(selector).getall()).strip()
    lat, lng = sel.css(".show_map_hp_link::attr(data-atlas-latlng)").get("0,0").split(",")
    id = re.findall(r"b_hotel_id:\s*'(.+?)'", result.content)
    data = {
        "url": result.context["url"],
        "id": id[0] if id else None,
        "title": sel.css("h2::text").get(),
        "description": css('[data-capla-component-boundary="b-property-web-property-page/PropertyDescriptionDesktop"] ::text', "\n"),
        "address": xpath("//div[@data-testid='PropertyHeaderAddressDesktop-wrapper']//button/div/text()"),
        "images": sel.css("#photo_wrapper img::attr(src)").getall(),
        "lat": lat,
        "lng": lng,
        "features": dict(features),
    }
    return data


async def scrape_hotel(url: str, checkin: str, price_n_days=61) -> Dict:
    """
    Scrape Booking.com hotel data and pricing information.
    """
    print(f"scraping hotel {url} {checkin} with {price_n_days} days of pricing data")
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


async def run():
    WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    result_hotel = await scrape_hotel(
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        checkin=WEEK_FROM_NOW, 
        price_n_days=7,
    )

    # save the results to a json file
    with open("hotel.json", "w", encoding="utf-8") as file:
        json.dump(result_hotel, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())