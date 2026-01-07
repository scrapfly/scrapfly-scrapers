# https://gist.github.com/scrapfly-dev/ef74e0947ef0794b0dc893b65fb7664d
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

def parse_alternatives(response: ScrapeApiResponse):
    """parse G2 alternative pages"""
    try:
        selector = response.selector
    except:
        return []
    
    data = []
    
    # The correct selector for individual product cards
    for alt in selector.xpath("//div[@data-ordered-events-item='products']"):
        # Check for sponsored content - skip it
        sponsored = alt.xpath(".//span[text()='Sponsored']").get()
        if sponsored:
            continue
            
        # Extract product name
        name = alt.xpath(".//div[contains(@class, 'elv-text-lg') and contains(@class, 'elv-font-bold')]/text()").get()
        
        # Extract product link
        link = alt.xpath(".//a[contains(@href, '/products/')]/@href").get()
        if link and not link.startswith('http'):
            link = f"https://www.g2.com{link}"
            
        # Extract ranking from the position meta tag
        ranking = alt.xpath(".//meta[@itemprop='position']/@content").get()
        
        # Extract rating and number of reviews
        rating_text = alt.xpath(".//label[contains(@class, 'elv-font-semibold')]/text()").get()
        reviews_text = alt.xpath(".//label[contains(@class, 'elv-font-light')]/text()").get()
        
        # Clean up the reviews count
        number_of_reviews = None
        if reviews_text:
            # Remove parentheses and commas, then convert to int
            clean_reviews = reviews_text.strip('()').replace(',', '')
            try:
                number_of_reviews = int(clean_reviews)
            except ValueError:
                pass
                
        # Clean up rating
        rate = None
        if rating_text:
            try:
                rate = float(rating_text.split('/')[0])
            except (ValueError, IndexError):
                pass
        
        # Extract description
        description = alt.xpath(".//p[contains(@class, 'elv-text-default')]/text()").get()
        
        # Only add if we have at least a name
        if name:
            data.append({
                "name": name.strip(),
                "link": link,
                "ranking": int(ranking) if ranking else None,
                "numberOfReviews": number_of_reviews,
                "rate": rate,
                "description": description.strip() if description else None,
            })
    
    return data


async def scrape_alternatives(
    product: str,
    alternatives: Literal["small-business", "mid-market", "enterprise"] = "",
) -> Dict:
    """scrape product alternatives from G2 alternative pages"""
    # the default alternative is top 10, which takes to argument
    url = f"https://www.g2.com/products/{product}/competitors/alternatives/{alternatives}"
    data = []
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_alternatives(response)

    print(f"Scraped {len(data)} company alternatives from G2 alternative pages")
    return data


async def main():
    alternatives_data = await scrape_alternatives(
        product="digitalocean"
    )

    # save the results to a json file
    with open("alternatives_data.json", "w", encoding="utf-8") as file:
        json.dump(alternatives_data, file, indent=2, ensure_ascii=False)    


if __name__ == "__main__":
    asyncio.run(main())