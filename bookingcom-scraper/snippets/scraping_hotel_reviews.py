# https://gist.github.com/scrapfly-dev/ed49379f0a4e546e0c7592bd1662d468
import os
import re
import json
import asyncio

from uuid import uuid4
from typing import Dict, List, Optional
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def retrieve_reviews_api_xhr_call(result: ScrapeApiResponse) -> Dict:
    """retrieve the reviews xhr call from the captured browser data"""
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    for xhr in _xhr_calls:
        if "reviewCard" in xhr["response"]["body"]:
            return xhr


async def scrape_hotel_reviews(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """scrape hotel review data"""
    reviews_data = []
    reviews_page_url = url + "?force_referer=#tab-reviews"
    session_id = str(uuid4()).replace("-", "")
    print(f"scraping the main reviews page for the url {url} before scraping the graphql api")
    main_reviews_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(reviews_page_url, **BASE_CONFIG, render_js=True, rendering_wait=5000, session=session_id)
    )
    reviews_xhr_call = retrieve_reviews_api_xhr_call(main_reviews_page)
    gql_body = json.loads(reviews_xhr_call["body"])
    total_review_count = int(json.loads(reviews_xhr_call["response"]["body"])["data"]["reviewListFrontend"]["reviewsCount"])
    total_review_pages = math.ceil(total_review_count / 10)
    _csrf_token = re.findall(r"b_csrf_token:\s*'(.+?)'", main_reviews_page.content)[0]

    if max_pages is None:
        max_pages = total_review_pages
    
    if max_pages is not None and max_pages > total_review_pages:
        max_pages = total_review_pages

    print(f"scraping {max_pages} review pages concurrently using the graphql api")


    def update_gql_body(gql_body: Dict, offset: int) -> Dict:
        gql_body['variables']['input']['skip'] = offset
        return gql_body

    remaining_pages = [
        ScrapeConfig(
            "https://www.booking.com/dml/graphql?lang=en-gb",
            method="POST",
            body=json.dumps(update_gql_body(gql_body, offset)),
            session=session_id,
            # note that we need to set headers to avoid being blocked
            headers={
                "content-type": "application/json",
                "x-booking-csrf-token": _csrf_token,
                "referer": main_reviews_page.context["url"],
                "origin": "https://www.booking.com",
            },
            **BASE_CONFIG,
        )
        for offset in range(0, max_pages * 10, 10)
    ]

    async for response in SCRAPFLY.concurrent_scrape(remaining_pages):
        reviews_data.extend(json.loads(response.content)["data"]["reviewListFrontend"]["reviewCard"])

    print(f"scraped {len(reviews_data)} reviews from the hotel reviews api for the url {url}")
    return reviews_data


async def main():
    reviews_data = await scrape_hotel_reviews("https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html", max_pages=3)
    
    # save the results to a json file
    with open("hotel_reviews.json", "w", encoding="utf-8") as file:
        json.dump(reviews_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())