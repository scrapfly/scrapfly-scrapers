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
from typing import List, Dict, TypedDict, Optional, Any
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
    "render_js": True,
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
    total_pages: int
    total_results: int
    products: List[Dict[str, Any]]


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
                    log.info(f"Found {len(review_list)}")
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
                            "created_date": _timestamp_to_iso(
                                details.get("created_date")
                            ),
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
    description = re.sub(r"<[^>]+>", "", description_html).strip()

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
        rows = table.xpath(".//tbody//tr")
        for row in rows:
            # First td contains the label, second td contains the value
            tds = row.xpath("./td")
            if len(tds) >= 2:
                # Extract text from first td (label) and second td (value)
                label_parts = tds[0].xpath(".//text()").getall()
                value_parts = tds[1].xpath(".//text()").getall()
                label = " ".join(part.strip() for part in label_parts if part.strip())
                value = " ".join(part.strip() for part in value_parts if part.strip())

                if label and value:
                    label_clean = label.strip().rstrip(":")
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
                "script": "async function clickUntilDisabled(){const maxClicks=50;const waitBetweenClicks=1500;let clicks=0;while(clicks<maxClicks){const btn=document.querySelector('button.pr-rd-show-more:not([disabled])');if(!btn||!btn.offsetParent){break;}try{btn.click();clicks++;await new Promise(r=>setTimeout(r,waitBetweenClicks));}catch(e){break;}}return clicks;}return await clickUntilDisabled();",
                "timeout": 5000,  # you can increase this if needed to get more reviews
            }
        }
    ]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, js_scenario=JS) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            products.append(parse_product(response))
        except Exception as e:
            log.error(f"Error scraping product page {response.context['url']}: {e}")
    log.info(f"Scraped {len(products)} product pages")

    return products


def parse_search_listing(response: ScrapeApiResponse) -> ZoroSearchListing:
    sel = response.selector
    # Extract total pages from pagination info from html
    total_pages = 0
    page_text = (
        sel.css('span[data-za="pagination-label"]::text').get()
        or sel.css("#pagination-label-info::text").get()
    )
    if page_text:
        pages_match = re.search(r"of\s+(\d+)\s+pages", page_text.strip())
        if pages_match:
            total_pages = int(pages_match.group(1))

    total_results = 0
    results_text = sel.css("span.result-count::text").get()
    if results_text:
        results_match = re.search(r"\(([\d,]+)\+?\s+items?\)", results_text)
        if results_match:
            # Remove commas and convert to int
            total_results = int(results_match.group(1).replace(",", ""))

    # Extract product listings from xhr calls
    products = []
    if "browser_data" in response.scrape_result:
        browser_data = response.scrape_result["browser_data"]
        xhr_calls = browser_data.get("xhr_call", [])
        for xhr in xhr_calls:
            url = xhr.get("url", "")
            if url.startswith("https://api.prod.zoro.com/catalog/v1/catalog/product"):
                try:
                    response_data = xhr.get("response", {})
                    body = response_data.get("body", "")
                    if body:
                        data = json.loads(body)
                        products.extend(data.get("products", []))
                except Exception as e:
                    log.error(f"Error parsing XHR data from {url}: {e}")
    log.info(f"Scraped {len(products)} products from search listing")
    return {
        "total_pages": total_pages,
        "total_results": total_results,
        "products": products,
    }


async def scrape_search_listing(query: str, max_pages: int = 3, scrape_all_pages: bool = False) -> ZoroSearchListing:
    """
    Scrape Zoro search pages for product listings

    Args:
        query: Search query string
        max_pages: Maximum number of pages to scrape (default: 3)
        scrape_all_pages: Whether to scrape all pages (default: False)
    Returns:
        ZoroSearchListing dictionary with products and metadata
    """
    log.info(f"Scraping Zoro search page for query: {query}")
    encoded_query = urllib.parse.quote(query)
    base_url = f"https://www.zoro.com/search?q={encoded_query}"
    log.info(f"Scraping first page of search listing: {base_url}")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(base_url, auto_scroll=True, **BASE_CONFIG)
    )

    # first page data
    first_page_data = parse_search_listing(first_page)
    total_pages = first_page_data["total_pages"]
    total_results = first_page_data["total_results"]
    products = first_page_data["products"]

    if scrape_all_pages:
        pages_to_scrape = total_pages
    else:
        pages_to_scrape = min(max_pages, total_pages)

    log.info(
        f"Scraping {pages_to_scrape - 1} additional pages (total: {pages_to_scrape})"
    )
    scraped_pages = 1
    if pages_to_scrape > 1:
        other_pages = [
            ScrapeConfig(f"{base_url}&page={page}", auto_scroll=True, **BASE_CONFIG)
            for page in range(2, pages_to_scrape + 1)
        ]
        async for response in SCRAPFLY.concurrent_scrape(other_pages):
            scraped_pages += 1
            if isinstance(response, ScrapflyScrapeError):
                log.error(f"Error scraping page {scraped_pages}: {response.error}")
                continue
            log.info(f"Scraped page {scraped_pages} of {pages_to_scrape}")
            page_data = parse_search_listing(response)
            products.extend(page_data["products"])
    log.info(f"Scraped {len(products)} products from {pages_to_scrape} pages")

    data = {
        "total_pages": total_pages,
        "total_results": total_results,
        "products": products,
    }
    return data
