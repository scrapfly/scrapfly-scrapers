"""
This is an example web scraper for Allegro.pl used in scrapfly blog article:
https://scrapfly.io/blog/posts/how-to-scrape-allegro

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""

import os
import json
import re
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Allegro.pl requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "proxy_pool": "public_residential_pool"
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class ShippingInfo(TypedDict):
    """Shipping and delivery information"""
    shipping_price: str
    return_policy: str


class Review(TypedDict):
    """Product review information"""
    author: str
    rating: int
    content: str
    pros: str
    date: str


class AllegroProduct(TypedDict):
    """Complete Allegro product data structure"""
    product_title: str
    price: str
    shipping_info: ShippingInfo
    images: List[str]
    rating: str
    reviews_count: int
    reviews: List[Review]
    seller: str
    specifications: List[Dict[str, str]]
    allegro_smart_badge: bool


def parse_product(result: ScrapeApiResponse) -> AllegroProduct:
    """Parse Allegro product page for product data"""
    sel = result.selector

    # Extract JSON data from script tags
    # Price and basic info
    price_json = sel.xpath(
        '//script[@data-serialize-box-id and contains(text(), "formattedPrice")]/text()'
    ).get()
    price_data = json.loads(price_json) if price_json else {}

    # Gallery images
    gallery_json = sel.xpath(
        '//script[@data-serialize-box-id and contains(text(), "gallery")]/text()'
    ).get()
    gallery_data = json.loads(gallery_json) if gallery_json else {}

    # Seller info
    seller_json = sel.xpath(
        '//script[@data-serialize-box-id and contains(text(), "sellerName")]/text()'
    ).get()
    seller_data = json.loads(seller_json) if seller_json else {}

    # Rating and reviews - Parse all JSON scripts that contain rating/reviews info
    rating_json_list = sel.xpath(
        '//script[@data-serialize-box-id and (contains(text(), "rating") or contains(text(), "reviews"))]/text()'
    ).getall()
    
    # Initialize variables
    rating_value = ""
    reviews_count = 0
    processed_reviews = []
    
    # Parse each JSON to find rating and reviews
    for rating_json in rating_json_list:
        try:
            data = json.loads(rating_json)
            
            # Check for rating in standard format
            if 'rating' in data and isinstance(data['rating'], dict):
                rating_value = rating_value or str(data['rating'].get('value', '') or data['rating'].get('ratingValue', ''))
                reviews_count = reviews_count or data['rating'].get('reviewsCount', 0)
                if rating_value:
                    log.info(f"Found rating: {rating_value}, reviews count: {reviews_count}")
            
            # Check for aggregateRating format
            if 'aggregateRating' in data and isinstance(data['aggregateRating'], dict):
                rating_value = rating_value or str(data['aggregateRating'].get('value', ''))
                reviews_count = reviews_count or data['aggregateRating'].get('count', {}).get('reviews', 0)
                if rating_value:
                    log.info(f"Found aggregateRating: {rating_value}, reviews count: {reviews_count}")
            
            # Extract reviews array if present
            if 'reviews' in data and isinstance(data['reviews'], list):
                for review in data['reviews']:
                    processed_reviews.append({
                        'author': review.get('author', ''),
                        'rating': review.get('rating', 0),
                        'content': review.get('content', ''),
                        'pros': review.get('pros', ''),
                        'date': review.get('datePublished', '')
                    })
                log.info(f"Found {len(data['reviews'])} reviews")
                
        except json.JSONDecodeError as e:
            log.error(f"Error parsing rating JSON: {e}")
            continue
    # Extract specifications from HTML
    specifications = []
    for spec_item in sel.xpath("//ul/li[b]"):
        key = spec_item.xpath(".//b/text()").get()
        value = spec_item.xpath("./text()").get()
        if key and value:
            specifications.append(
                {"key": key.strip().rstrip(":"), "value": value.strip()}
            )

    # Extract shipping info from HTML
    shipping_price = ""
    shipping_text = ""

    shipping_elem = sel.xpath(
        '//button[@data-analytics-view-label="ShippingInfo"]//span/text()'
    ).get()
    if shipping_elem:
        shipping_text = shipping_elem.strip()
        # Extract just the price value
        price_match = re.search(r"(\d+[.,]\d+)", shipping_text)
        if price_match:
            shipping_price = price_match.group(1)


    # Extract return policy
    return_policy = ""
    return_elem = sel.xpath(
        '//button[@data-analytics-view-label="TrustInfo"]//div/text()'
    ).get()
    if return_elem:
        return_policy = return_elem.strip()

    # Build the product data
    parsed_data = {
        "product_title": sel.xpath('//meta[@property="og:title"]/@content').get(""),
        "price": price_data.get("price", {}).get("formattedPrice", ""),
        "shipping_info": {
            "shipping_price": shipping_price,
            "return_policy": return_policy,
        },
        "images": gallery_data.get("gallery", []),
        "rating": rating_value,
        "reviews_count": reviews_count,
        "reviews": processed_reviews, 
        "seller": seller_data.get("sellerName", ""),
        "specifications": specifications,
        "allegro_smart_badge": bool(sel.xpath('//img[contains(@src, "smart")]').get()),
    }

    return parsed_data


async def scrape_product(urls: list[str]) -> List[AllegroProduct]:
    """scrape a single Allegro product"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data.append(parse_product(response))
        except Exception as e:
            log.error(f"Error parsing Allegro product: {e}")
            continue
    log.success(f"scraped {len(data)} products from product pages")
    return data
