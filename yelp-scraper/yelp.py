"""
This is an example web scraper for yelp.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import uuid
import json
import math
import base64
import jmespath
from typing import Dict, List, TypedDict
from urllib.parse import urlencode
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass yelp.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    # set the proxy pool to residential
    "proxy_pool": "public_residential_pool",
}


class Review(TypedDict):
    id: str
    userId: str
    business: dict
    user: dict
    comment: dict
    rating: int
    # and more


def parse_page(response: ScrapeApiResponse):
    """parse business data from yelp business pages"""
    sel = response.selector
    xpath = lambda xp: sel.xpath(xp).get(default="").strip()
    open_hours = {}
    for day in sel.xpath('//th/p[contains(@class,"day-of-the-week")]'):
        name = day.xpath("text()").get().strip()
        value = day.xpath("../following-sibling::td//p/text()").get().strip()
        open_hours[name.lower()] = value

    return dict(
        name=xpath("//h1/text()"),
        website=xpath('//p[contains(text(),"Business website")]/following-sibling::p/a/text()'),
        phone=xpath('//p[contains(text(),"Phone number")]/following-sibling::p/text()'),
        address=xpath('//a[contains(text(),"Get Directions")]/../following-sibling::p/text()'),
        logo=xpath('//img[contains(@class,"businessLogo")]/@src'),
        claim_status="".join(sel.xpath('//span[span[contains(@class,"claim")]]/text()').getall()).strip().lower(),
        open_hours=open_hours,
    )


def parse_business_id(response: ScrapeApiResponse):
    """parse the business id from yelp business pages"""
    selector = response.selector
    business_id = selector.css('meta[name="yelp-biz-id"]::attr(content)').get()
    return business_id


def parse_review_data(response: ScrapeApiResponse):
    """parse review data from the JSON response"""
    data = json.loads(response.scrape_result["content"])
    reviews = data[0]["data"]["business"]["reviews"]["edges"]
    parsed_reviews = []
    for review in reviews:
        result = jmespath.search(
            """{
            encid: encid,
            text: text.{full: full, language: language},
            rating: rating,
            feedback: feedback.{coolCount: coolCount, funnyCount: funnyCount, usefulCount: usefulCount},
            author: author.{encid: encid, displayName: displayName, displayLocation: displayLocation, reviewCount: reviewCount, friendCount: friendCount, businessPhotoCount: businessPhotoCount},
            business: business.{encid: encid, alias: alias, name: name},
            createdAt: createdAt.utcDateTime,
            businessPhotos: businessPhotos[].{encid: encid, photoUrl: photoUrl.url, caption: caption, helpfulCount: helpfulCount},
            businessVideos: businessVideos,
            availableReactions: availableReactionsContainer.availableReactions[].{displayText: displayText, reactionType: reactionType, count: count}
            }""",
            review["node"],
        )
        parsed_reviews.append(result)
    total_reviews = data[0]["data"]["business"]["reviewCount"]
    return {"reviews": parsed_reviews, "total_reviews": total_reviews}


def parse_search(response: ScrapeApiResponse):
    """parse listing data from the search XHR data"""
    search_data = []
    selector = response.selector
    script = selector.xpath("//script[@data-id='react-root-props']/text()").get()
    data = json.loads(script.split("react_root_props = ")[-1].rsplit(";", 1)[0])
    for item in data["legacyProps"]["searchAppProps"]["searchPageProps"]["mainContentComponentsListProps"]:
        # filter search data cards
        if "bizId" in item.keys():
            search_data.append(item)
        # filter the max results count
        elif "totalResults" in item["props"]:
            total_results = item["props"]["totalResults"]
    return {"search_data": search_data, "total_results": total_results}


async def scrape_pages(urls: List[str]) -> List[Dict]:
    """scrape yelp business pages"""
    # add the business pages to a scraping list
    result = []
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        result.append(parse_page(response))
    log.success(f"scraped {len(result)} business pages")
    return result


async def request_reviews_api(url: str, start_index: int, business_id):
    """request the graphql API for review data"""
    pagionation_data = {"version": 1, "type": "offset", "offset": start_index}
    pagionation_data = json.dumps(pagionation_data)
    after = base64.b64encode(pagionation_data.encode("utf-8")).decode(
        "utf-8"
    )  # decode the pagination values for the payload

    payload = json.dumps(
        [
            {
                "operationName": "GetBusinessReviewFeed",
                "variables": {
                    "encBizId": f"{business_id}",
                    "reviewsPerPage": 10,
                    "selectedReviewEncId": "",
                    "hasSelectedReview": False,
                    "sortBy": "DATE_DESC",
                    "languageCode": "en",
                    "ratings": [5, 4, 3, 2, 1],
                    "isSearching": False,
                    "after": after,  # pagination parameter
                    "isTranslating": False,
                    "translateLanguageCode": "en",
                    "reactionsSourceFlow": "businessPageReviewSection",
                    "minConfidenceLevel": "HIGH_CONFIDENCE",
                    "highlightType": "",
                    "highlightIdentifier": "",
                    "isHighlighting": False,
                },
                "extensions": {
                    "operationType": "query",
                    # static value
                    "documentId": "ef51f33d1b0eccc958dddbf6cde15739c48b34637a00ebe316441031d4bf7681",
                },
            }
        ]
    )

    headers = {
        "authority": "www.yelp.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://www.yelp.com",
        "referer": url,  # main business page URL
        "x-apollo-operation-name": "GetBusinessReviewFeed",
    }
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://www.yelp.com/gql/batch", headers=headers, body=payload, method="POST", asp=True, country="US"
        )
    )
    return response


async def scrape_reviews(url: str, max_reviews: int = None) -> List[Review]:
    # first find business ID from business URL
    log.info("scraping the business id from the business page")
    response_business = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True))
    business_id = parse_business_id(response_business)

    log.info("scraping the first review page")
    first_page = await request_reviews_api(url=url, business_id=business_id, start_index=1)
    review_data = parse_review_data(first_page)
    reviews = review_data["reviews"]
    total_reviews = review_data["total_reviews"]

    # find total page count to scrape
    if max_reviews and max_reviews < total_reviews:
        total_reviews = max_reviews

    # next, scrape the remaining review pages
    log.info(f"scraping review pagination, remaining ({total_reviews // 10}) more pages")
    for offset in range(11, total_reviews, 10):
        try:
            response = await request_reviews_api(url=url, business_id=business_id, start_index=offset)
            new_review_data = parse_review_data(response)["reviews"]
            reviews.extend(new_review_data)
        except Exception as e:
            log.error(f"An error occurred while scraping search pages", e)
            pass
    log.success(f"scraped {len(reviews)} reviews from review pages")
    return reviews


async def scrape_search(keyword: str, location: str, max_pages: int = None):
    """scrape single page of yelp search"""

    def make_search_url(offset):
        base_url = "https://www.yelp.com/search?"
        params = {"find_desc": keyword, "find_loc": location, "start": offset}
        return base_url + urlencode(params)
        # final url example:
        # https://www.yelp.com/search?find_desc=plumbers&find_loc=Seattle%2C+WA&start=1


    log.info("scraping the first search page")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(make_search_url(1), **BASE_CONFIG, render_js=True)
    )
    data = parse_search(first_page)
    search_data = data["search_data"]
    total_results = data["total_results"]

    # find total page count to scrape
    total_pages = math.ceil(total_results / 10)  # each page contains 10 results
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # add the remaining pages to a scraping list and scrape them concurrently
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    other_pages = [
        ScrapeConfig(make_search_url(offset), **BASE_CONFIG, render_js=True)
        for offset in range(11, total_pages * 10, 10)
    ]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        try:
            search_data.extend(parse_search(response)["search_data"])
        except Exception as e:
            log.error(f"An error occurred while scraping search pages", e)
            pass
    log.success(f"scraped {len(search_data)} listings from search pages")
    return search_data
