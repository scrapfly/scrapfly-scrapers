# https://gist.github.com/scrapfly-dev/aaf6ae3ccea182fb9715f2ea5d6d9480
import json
import os
import re
import asyncio

from typing import Dict, List
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_reviews(result: ScrapeApiResponse) -> List[Dict]:
    """parse review from single review page"""
    review_boxes = result.selector.css("#cm-cr-dp-review-list li.review")
    parsed = []
    for box in review_boxes:
        rating = box.css("[data-hook=review-star-rating] ::text").re_first(r"(\d+\.*\d*) out")
        parsed.append(
            {
                "text": "".join(box.css("[data-hook=review-collapsed] ::text").getall()).strip(),
                "title": box.css("*[data-hook=review-title]>span::text").get(),
                "location_and_date": box.css("span[data-hook=review-date] ::text").get(),
                "verified": bool(box.css("span[data-hook=avp-badge-linkless] ::text").get()),
                "rating": float(rating) if rating else None,
            }
        )
    return parsed


async def scrape_reviews(url: str) -> List[Dict]:
    """scrape product reviews of a given URL of an amazon product"""
    # pagination is not publically available, so we can't scrape more than one page
    print(f"scraping review page: {url}")
    api_response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    reviews = parse_reviews(api_response)
    print(f"scraped {len(reviews)} reviews")
    return reviews


async def main():
    reviews = await scrape_reviews(
        url = "https://www.amazon.com/PlayStation-5-Console-CFI-1215A01X/dp/B0BCNKKZ91/"
    )

    # save the results to a json file
    with open("reviews.json", "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())