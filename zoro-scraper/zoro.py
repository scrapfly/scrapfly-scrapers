"""
This is an example web scraper for zoro.com using Scrapfly
https://scrapfly.io/blog/posts/how-to-scrape-zoro-dot-com

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""

import os
import json
import re
from datetime import datetime
import urllib.parse
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict, Optional
from scrapfly import (
    ScrapeConfig,
    ScrapflyClient,
    ScrapeApiResponse,
    ScrapflyScrapeError,
)


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # requires Anti Scraping Protection bypass feature.
    "asp": True,
}


output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class ZoroReview(TypedDict):
    review_id: Optional[int]
    rating: Optional[int]
    headline: str
    comments: str
    nickname: str
    location: str
    created_date: str
    is_verified_buyer: bool
    helpful_votes: int
    media_count: int


class ZoroProduct(TypedDict):
    sku: str
    mpn: str
    name: str
    brand: str
    description: str
    price: str
    currency: str
    availability: str
    url: str
    specifications: Dict[str, str]
    images: List[str]
    rating: Optional[float]
    review_count: int
    reviews: List[ZoroReview]


class ZoroSearchListing(TypedDict):
    pass


def _timestamp_to_iso(timestamp_ms: int) -> str:
    """Convert millisecond timestamp to ISO format string."""
    if not timestamp_ms:
        return ""
    return datetime.fromtimestamp(timestamp_ms / 1000).isoformat()

def parse_reviews(xhr_calls: List[Dict]) -> List[ZoroReview]:
    reviews = []
    seen_review_ids = set()  # Track review IDs to avoid duplicates
    
    for xhr in xhr_calls:
        url = xhr.get("url", "")
        if url.startswith("https://display.powerreviews.com"):
            try:
                response = xhr.get("response", {})
                body = response.get("body", "")
                if not body:
                    log.warning(f"Empty response body for URL: {url}")
                    continue
                data = json.loads(body)
                # PowerReviews API structure: results[0].reviews
                results = data.get("results", [])
                if not results:
                    log.debug(f"No results in data for URL: {url}")
                    continue
                
                review_list = results[0].get("reviews", [])
                if review_list:
                    log.info(f"Found {len(review_list)} reviews from {url}")
                    for review in review_list:
                        review_id = review.get("review_id") or review.get("ugc_id")
                        # Skip duplicates
                        if review_id and review_id in seen_review_ids:
                            continue
                        if review_id:
                            seen_review_ids.add(review_id)
                        
                        # Extract only useful information
                        details = review.get("details", {})
                        metrics = review.get("metrics", {})
                        badges = review.get("badges", {})
                        media = review.get("media", [])
                        
                        parsed_review = {
                            "review_id": review_id,
                            "rating": metrics.get("rating"),
                            "headline": details.get("headline", ""),
                            "comments": details.get("comments", ""),
                            "nickname": details.get("nickname", ""),
                            "location": details.get("location", ""),
                            "created_date": _timestamp_to_iso(details.get("created_date")),
                            "is_verified_buyer": badges.get("is_verified_buyer", False),
                            "helpful_votes": metrics.get("helpful_votes", 0),
                            "media_count": len(media),
                        }
                        reviews.append(parsed_review)
                else:
                    log.debug(f"No reviews in results for URL: {url}")
            except Exception as e:
                log.error(f"Error processing XHR call {url}: {e}")

    log.info(f"Total reviews parsed: {len(reviews)}")
    return reviews

def parse_product(response: ScrapeApiResponse) -> ZoroProduct:
    sel = response.selector

    json_ld = sel.xpath('//script[@type="application/ld+json"][@data-za="product-microdata"]/text()').get()
    if not json_ld:
        log.error(f"Could not find JSON-LD data on {response.context['url']}")
        raise ValueError("No product data found")

    data = json.loads(json_ld)

    # Extract basic product info from JSON-LD data
    sku = data.get("sku", "")
    mpn = data.get("mpn", "")
    name = data.get("name", "")
    brand = data.get("brand", {}).get("name", "") if data.get("brand") else ""
    description_html = data.get("description", "")
    description = re.sub(r'<[^>]+>', '', description_html).strip()

    # Extract pricing and availability from JSON-LD data
    offers = data.get("offers", {})
    price = offers.get("price", "")
    currency = offers.get("priceCurrency", "USD")
    availability = offers.get("availability", "").replace("http://schema.org/", "")
    url = offers.get("url", response.context.get("url", ""))

    # Extract image urls from JSON-LD data
    images = []
    for img in data.get("image", []):
        if isinstance(img, dict):
            images.append(img.get("contentUrl", ""))
        else:
            images.append(img)


    # Extract rating and review count from JSON-LD data
    rating_data = data.get("aggregateRating", {})
    rating = rating_data.get("ratingValue") if rating_data else None
    review_count = rating_data.get("reviewCount", 0) if rating_data else 0

    # Extract specifications from product attributes tables
    specifications = {}
    # Find all tables within product-attributes div
    tables = sel.xpath('//div[contains(@class, "product-attributes")]//table')
    for table in tables:        
        # Extract rows from the table
        rows = table.xpath('.//tbody//tr')
        for row in rows:
            # First td contains the label, second td contains the value
            tds = row.xpath('./td')
            if len(tds) >= 2:
                # Extract text from first td (label) and second td (value)
                label_parts = tds[0].xpath('.//text()').getall()
                value_parts = tds[1].xpath('.//text()').getall()
                label = ' '.join(part.strip() for part in label_parts if part.strip())
                value = ' '.join(part.strip() for part in value_parts if part.strip())
                
                if label and value:
                    label_clean = label.strip().rstrip(':')
                    value_clean = value.strip()
                    specifications[label_clean] = value_clean

    # Extract reviews from XHR calls
    reviews = []
    if "browser_data" in response.scrape_result:
        browser_data = response.scrape_result["browser_data"]
        xhr_calls = browser_data.get("xhr_call", [])
        reviews = parse_reviews(xhr_calls)

    return {
        "sku": sku,
        "mpn": mpn,
        "name": name,
        "brand": brand,
        "description": description,
        "price": price,
        "currency": currency,
        "availability": availability,
        "url": url,
        "specifications": specifications,
        "images": images,
        "rating": rating,
        "review_count": review_count,
        "reviews": reviews,
    }




async def scrape_product(urls: List[str]) -> List[ZoroProduct]:
    """
    Scrape Zoro product pages for product data

    Args:
        urls: List of product URLs to scrape

    Returns:
        List of ZoroProduct dictionaries
    """
    log.info(f"Scraping {len(urls)} product pages")
    # JavaScript code to click the "Show more" button  to get all the product data
    JS = [
        {
            "execute": {
                "script": "async function clickUntilDisabled() { const maxClicks = 50; let clicks = 0; while (clicks < maxClicks) { const btn = document.querySelector('button.pr-rd-show-more:not([disabled])'); if (!btn || btn.disabled || btn.style.display === 'none' || !btn.offsetParent) { break; } btn.click(); clicks++; await new Promise(r => setTimeout(r, 1500)); } return clicks; } return await clickUntilDisabled();",
                "timeout": 5000,  # you can increase this if needed to get more reviews
            }
        }
    ]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True, js_scenario=JS) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            products.append(parse_product(response))
        except Exception as e:
            log.error(f"Error scraping product page {response.context['url']}: {e}")
    log.info(f"Scraped {len(products)} product pages")

    return products





def parse_search_listing(response: ScrapeApiResponse) -> ZoroSearchListing:
    pass


def scrape_search_listing(url: str) -> ZoroSearchListing:
    pass
