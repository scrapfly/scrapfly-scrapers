"""
This is an example web scraper for Allegro.pl used in scrapfly blog article:
https://scrapfly.io/blog/posts/how-to-scrape-allegro

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""

import os
import json
import re
import urllib.parse
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Allegro.pl requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "render_js":True,
    "retry": True,
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


class AllegroSearch(TypedDict):
    """Allegro search results"""
    products: List[Dict]
    scraped_pages: int      # Number of pages actually scraped
    products_count: int     # Number of products scraped
    total_pages: int        # Total pages available on Allegro
    total_count: int        # Total products available on Allegro

def parse_search(result: ScrapeApiResponse) -> AllegroSearch:
    """Parse Allegro search page for product listings"""
    # Find the main JSON data with search results
    search_meta_json = result.selector.xpath(
        '//script[@data-serialize-box-id and contains(text(), "searchMeta")]/text()'
    ).get()
    if not search_meta_json:
        log.error("Could not find searchMeta JSON")
        return {"products": [], "total_pages": 0}
    
    search_meta = json.loads(search_meta_json)
    last_page = search_meta.get("props", {}).get("searchMeta", {}).get("lastAvailablePage", 1)
    total_count = search_meta.get("props", {}).get("searchMeta", {}).get("totalCount", 0)
    # Find the product listing JSON
    listing_json = result.selector.xpath(
        '//script[contains(text(), "__listing_StoreState")]/text()'
    ).get()
    
    products = []
    if listing_json:
        listing_data = json.loads(listing_json)
        elements = listing_data.get("__listing_StoreState", {}).get("items", {}).get("elements", [])
        
        for item in elements:
            # Skip promoted/sponsored items if needed  (Advertised product)
            if item.get("context") == "PROMOTED":
                continue
                
            # Extract product data
            price_info = item.get("price", {})
            main_price = price_info.get("mainPrice", {}) if price_info else {}

            products.append({
                "product_id": item.get("id", ""),
                "offer_id": item.get("eventData", {}).get("offer_id", ""),
                "title": item.get("alt", ""),
                "price": main_price.get("amount", ""),
                "currency": main_price.get("currency", "PLN"),
                "url": f"https://allegro.pl/oferta/{item.get('eventData', {}).get('offer_id', '')}",
                "image": item.get("mainThumbnail", ""),
                "seller": item.get("seller", {}).get("login", ""),
                "delivery_info": item.get("deliveryInfo", {}).get("text", "")
            })
    
    log.info(f"Parsed {len(products)} products from search page")
    data = {
        "products": products,
        "scraped_pages": 1,
        "products_count": len(products),
        "total_pages": last_page,
        "total_count": total_count,
    }
    return data

async def scrape_search(query: str, max_pages: int = 3, scrape_all_pages: bool = False) -> List[AllegroSearch]:
    """
    Scrape Allegro search pages for product listings

    Args:
        query: Search query string
        max_pages: Maximum number of pages to scrape (default: 3)
        scrape_all_pages: If True, scrape all available pages (overrides max_pages)
    """
    encoded_query = urllib.parse.quote(query)
    base_url = f"https://allegro.pl/listing?string={encoded_query}"
    log.info(f"scraping base url {base_url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))

    # Parse first page
    first_page_data = parse_search(first_page)
    search_results = first_page_data["products"]
    total_pages = first_page_data["total_pages"]
    log.info(f"Found {total_pages} total pages with {first_page_data['total_count']} total products")

    if scrape_all_pages:
        pages_to_scrape = total_pages
    else:
        pages_to_scrape = min(max_pages, total_pages)

    log.info(f"Scraping {pages_to_scrape - 1} additional pages (total: {pages_to_scrape})")
    scraped_pages = 0
    if pages_to_scrape > 1:
        other_pages = [
            ScrapeConfig(f"{base_url}&p={page}", **BASE_CONFIG)
            for page in range(2, pages_to_scrape + 1)
        ]
        
        log.info(f"Scraping {len(other_pages)} additional pages")
        async for result in SCRAPFLY.concurrent_scrape(other_pages):
            if isinstance(result, ScrapflyScrapeError):
                log.error("ASP protection failed - skipping page")
                continue
            try:
                page_data = parse_search(result)
                search_results.extend(page_data["products"])
                scraped_pages += 1
            except Exception as e:
                log.error(f"Error parsing search page: {e}")
                continue
        log.success(f"Scraped {len(search_results)} total products from {scraped_pages} pages") 
    data = {
        "products": search_results,
        "scraped_pages": scraped_pages,
        "products_count": len(search_results),
        "total_pages": total_pages,
        "total_count": first_page_data["total_count"],
    }
    return data

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
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data.append(parse_product(response))
        except Exception as e:
            log.error(f"Error parsing Allegro product: {e}")
            continue
    log.success(f"scraped {len(data)} products from product pages")
    return data
