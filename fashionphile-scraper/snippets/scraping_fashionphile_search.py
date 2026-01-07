# https://gist.github.com/scrapfly-dev/f8216fea5df53fcb2be625ad3f9a7ec6
import os
import re
import json
import asyncio

from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_price(price_text: str) -> int:
    if not price_text:
        return 0
    # Remove $ and commas, convert to int
    return int(re.sub(r'[$,]', '', price_text.strip()))


def extract_product_from_card(card_selector) -> Dict:
    """Extract product data from a product card HTML element"""
    
    # Get product ID from data attribute
    product_id = card_selector.css('::attr(data-product-id)').get('')
    
    # Get brand name
    brand_name = card_selector.css('.fp-card__vendor::text').get('').strip()
    
    # Get product name
    product_name = card_selector.css('.fp-card__link__product-name::text').get('').strip()
    
    # Get condition
    condition = card_selector.css('.fp-condition::text').get('').strip()
        
    # Get prices
    regular_price_text = card_selector.css('.price-item--regular::text').get('').strip()
    sale_price_text = card_selector.css('.price-item--sale.price-item--last::text').get('').strip()
    
    # If no sale price, use regular price as final price
    if sale_price_text:
        price_text = sale_price_text
    elif regular_price_text:
        price_text = regular_price_text
    else:
        # Fallback: try to find any price
        price_text = card_selector.css('.price-item::text').get('$0').strip()
    
    price = parse_price(price_text)
    
    # Calculate discounted price
    if regular_price_text and sale_price_text:
        regular = parse_price(regular_price_text)
        discounted_price = regular - price
    else:
        discounted_price = 0
    

    # Build result matching search_schema
    result = {
        "brand_name": brand_name,
        "product_name" : product_name,
        "condition": condition,
        "discounted_price": discounted_price,
        "price": price,
        "id": int(product_id) if product_id else 0
    }
    
    return result


async def scrape_search(url: str, max_pages: int = 10) -> List[Dict]:
    """scrape product listing data from Fashionphile search pages"""
    # Scrape first page
    result_first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    selector = result_first_page.selector
    
    # Find all product cards
    product_cards = selector.css('.fp-algolia-product-card')
    print(f"found {len(product_cards)} products on first page")
    
    # Extract data from each card
    results = []
    for card in product_cards:
        product_data = extract_product_from_card(card)
        results.append(product_data)

    # Find total pages from pagination
    pagination_href = selector.css('.ais-Pagination-item--lastPage a::attr(href)').get('')
    if pagination_href:
        match = re.search(r'page=(\d+)', pagination_href)
        if match:
            total_pages = int(match.group(1))
        else:
            total_pages = 1
    else:
        total_pages = 1
    
    if max_pages and max_pages < total_pages:
        total_pages = max_pages
    
    print(f"total pages: {total_pages}")
    
    # Scrape remaining pages
    if total_pages > 1:
        print(f"scraping pagination ({total_pages-1} more pages)")
        
        # Build URLs for remaining pages
        base_url = url.split('?')[0]
        to_scrape = []
        for page in range(2, total_pages + 1):
            page_url = f"{base_url}?page={page}"
            to_scrape.append(ScrapeConfig(page_url, **BASE_CONFIG))
        
        # Scrape concurrently
        async for result in SCRAPFLY.concurrent_scrape(to_scrape):
            product_cards = result.selector.css('.fp-algolia-product-card')
            
            for card in product_cards:
                product_data = extract_product_from_card(card)
                results.append(product_data)
    
    print(f"scraped {len(results)} product listings from search pages")
    return results


async def main():
    search_data = await scrape_search(
        url="https://www.fashionphile.com/shop/discounted/all", max_pages=3
    )

    # save the results to a json file
    with open("search_data.json", "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())