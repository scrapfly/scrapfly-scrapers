"""
This is an example web scraper for yelp.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import math
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
        website=xpath(
            '//p[contains(text(),"Business website")]/following-sibling::p/a/text()'
        ),
        phone=xpath('//p[contains(text(),"Phone number")]/following-sibling::p/text()'),
        address=xpath(
            '//a[contains(text(),"Get Directions")]/../following-sibling::p/text()'
        ),
        logo=xpath('//img[contains(@class,"businessLogo")]/@src'),
        claim_status="".join(
            sel.xpath('//span[contains(@class,"claim-text")]/text()').getall()
        )
        .strip()
        .lower(),
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
    reviews = data["reviews"]
    total_reviews = data["pagination"]["totalResults"]
    return {"reviews": reviews, "total_reviews": total_reviews}


def parse_search(response: ScrapeApiResponse):
    """parse listing data from the search JSON data"""
    data = json.loads(response.scrape_result["content"])
    search_data = []
    for item in data["searchPageProps"]["mainContentComponentsListProps"]:
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


async def scrape_reviews(url: str, max_reviews: int = None) -> List[Review]:
    # first find business ID from business URL
    log.info("scraping the business id from the business page")
    response_business = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    business_id = parse_business_id(response_business)

    log.info("scraping the first review page")
    # then scrape first review page
    review_response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"https://www.yelp.com/biz/{business_id}/review_feed?rl=en&q=&sort_by=relevance_desc&start=0",
            **BASE_CONFIG,
        )
    )
    review_data = parse_review_data(review_response)
    reviews = review_data["reviews"]
    total_reviews = review_data["total_reviews"]

    # find total page count to scrape
    if max_reviews and max_reviews < total_reviews:
        total_reviews = max_reviews

    # next, scrape the remaining review pages concurrently
    log.info(
        f"scraping review pagination, remaining ({total_reviews // 10}) more pages"
    )
    other_pages = [
        ScrapeConfig(
            f"https://www.yelp.com/biz/{business_id}/review_feed?rl=en&q=&sort_by=relevance_desc&start={offset}",
            **BASE_CONFIG,
        )
        for offset in range(11, total_reviews, 10)
    ]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        reviews.extend(parse_review_data(response)["reviews"])
    log.success(f"scraped {len(reviews)} reviews from review pages")
    return reviews


async def scrape_search(keyword: str, location: str, max_pages: int = None):
    """scrape single page of yelp search"""

    def make_search_url(offset):
        base_url = "https://www.yelp.com/search/snippet?"
        params = {
            "find_desc": keyword,
            "find_loc": location,
            "start": offset,
            "parent_request": "",
            "ns": 1,
            "request_origin": "user",
        }
        return base_url + urlencode(params)
        # final url example:
        # https://www.yelp.com/search/snippet?find_desc=plumbers&find_loc=Toronto%2C+Ontario%2C+Canada&ns=1&start=210&parent_request_id=54233ce74d09d270&request_origin=user

    log.info(f"scraping the first search page")
    # the JSON data is a large file that require enabling render_js
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
        search_data.extend(parse_search(response)["search_data"])
    log.success(f"scraped {len(search_data)} listings from search pages")
    return search_data
