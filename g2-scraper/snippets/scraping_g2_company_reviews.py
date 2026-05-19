# https://gist.github.com/scrapfly-dev/7ab4a770b8813b387efb88ca538771d8
import os
import re
import json
import math
import asyncio

from urllib.parse import urljoin
from typing import Dict, List, Literal
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "render_js" : True,
    "proxy_pool": "public_residential_pool"
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_review_page(response: ScrapeApiResponse):
    """parse reviews data from G2 company pages"""
    selector = response.selector

    total_reviews_text = selector.xpath("//a[contains(@href, '/reviews#reviews') and contains(text(), 'reviews')]/text()").get()
    if total_reviews_text:
        total_reviews = int(total_reviews_text.split()[2])
        # Updated: The page now shows 10 reviews, not 25
        _review_page_size = 10
        total_pages = math.ceil(total_reviews / _review_page_size)
    else:
        total_reviews = None
        total_pages = 0

    data = []
    # main review container selector from 'div' to 'article'
    for review in selector.xpath("//article[.//div[@itemprop='reviewBody']]"):
        author_name = review.xpath(".//div[@itemprop='author']/meta[@itemprop='name']/@content").get()
        author_profile = review.xpath(".//div[contains(@class, 'avatar')]/parent::a/@href").get()

        # Author details have a new, less structured format
        author_details = review.xpath(
            ".//div[div[@itemprop='author']]//div[contains(@class, 'elv-text-subtle')]/text()"
        ).getall()
        author_position = author_details[0] if author_details and len(author_details) > 0 else None
        author_company_size = next((detail for detail in author_details if "emp." in detail), None)

        # selector for review tags
        review_tags = review.xpath(
            ".//div[contains(@class, 'gap-3') and contains(@class, 'flex-wrap')]//label/text()"
        ).getall()

        review_date = review.xpath(".//meta[@itemprop='datePublished']/@content").get()
        # selector for review rate using the reliable itemprop meta tag
        review_rate = review.xpath(".//span[@itemprop='reviewRating']/meta[@itemprop='ratingValue']/@content").get()
        review_title = review.xpath(".//div[@itemprop='name']//text()").get()

        # selectors for review likes and dislikes
        review_likes_parts = review.xpath(
            ".//section[div[contains(text(), 'What do you like best')]]/p//text()"
        ).getall()
        review_likes = "".join(review_likes_parts).replace("Review collected by and hosted on G2.com.", "").strip()

        review_dislikes_parts = review.xpath(
            ".//section[div[contains(text(), 'What do you dislike')]]/p//text()"
        ).getall()
        review_dislikes = (
            "".join(review_dislikes_parts).replace("Review collected by and hosted on G2.com.", "").strip()
        )

        data.append(
            {
                "author": {
                    "authorName": author_name.strip() if author_name else None,
                    "authorProfile": author_profile,
                    "authorPosition": (author_position.strip() if author_position else None),
                    "authorCompanySize": (author_company_size.strip() if author_company_size else None),
                },
                "review": {
                    "reviewTags": [tag.strip() for tag in review_tags if tag.strip()],
                    "reviewData": review_date,
                    "reviewRate": float(review_rate) if review_rate else None,
                    "reviewTitle": (review_title.replace('"', "").strip() if review_title else None),
                    "reviewLikes": review_likes,
                    "reviewDislikes": review_dislikes,
                },
            }
        )

    return {"total_pages": total_pages, "reviews_data": data}


async def scrape_reviews(url: str, max_review_pages: int = None) -> List[Dict]:
    """scrape company reviews from G2 review pages"""
    print(f"scraping first review page from company URL {url}")
    # Enhanced config
    enhanced_config = {
        **BASE_CONFIG,
        "auto_scroll": True,
        "wait_for_selector": "//section[@id='reviews']//article",
    }
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **enhanced_config))
    data = parse_review_page(first_page)
    reviews_data = data["reviews_data"]
    total_pages = data["total_pages"]

    # get the number of total review pages to scrape
    if max_review_pages and max_review_pages < total_pages:
        total_pages = max_review_pages

    # scrape the remaining review pages
    print(f"scraping reviews pagination, remaining ({total_pages - 1}) more pages")
    remaining_urls = [url + f"?page={page_number}" for page_number in range(2, total_pages + 1)]
    to_scrape = [ScrapeConfig(url, **enhanced_config) for url in remaining_urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_review_page(response)
        reviews_data.extend(data["reviews_data"])


    print(f"scraped {len(reviews_data)} company reviews from G2 review pages with the URL {url}")
    return reviews_data


async def main():
    reviews_data = await scrape_reviews(
        url="https://www.g2.com/products/digitalocean/reviews",
        max_review_pages=3
    )

    # save the results to a json file
    with open("reviews_data.json", "w", encoding="utf-8") as file:
        json.dump(reviews_data, file, indent=2, ensure_ascii=False)    


if __name__ == "__main__":
    asyncio.run(main())