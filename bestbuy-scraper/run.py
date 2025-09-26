"""
This example run script shows how to run the BestBuy.com scraper defined in ./bestbuy.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import bestbuy

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache/debug?
    bestbuy.BASE_CONFIG["cache"] = True
    bestbuy.BASE_CONFIG["debug"] = True    

    print("running BestBuy scrape and saving results to ./results directory")

    sitemap_data = await bestbuy.scrape_sitemaps(
        # sample scraper for one sitemap, other sitemaps can be found at:
        # https://www.bestbuy.com/robots.txt
        url="https://sitemaps.bestbuy.com/sitemaps_promos.0000.xml.gz"
    )
    with open(output.joinpath("promos.json"), "w", encoding="utf-8") as file:
        json.dump(sitemap_data, file, indent=2, ensure_ascii=False)


    product_data = await bestbuy.scrape_products(
        # note that the parsing logic for hidden data can differ based on the product type
        urls=[
            "https://www.bestbuy.com/site/apple-macbook-air-13-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/6565862.p",
            "https://www.bestbuy.com/site/apple-geek-squad-certified-refurbished-macbook-pro-16-display-intel-core-i7-16gb-memory-amd-radeon-pro-5300m-512gb-ssd-space-gray/6489615.p",
            "https://www.bestbuy.com/site/apple-macbook-pro-14-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-512gb-ssd-space-black/6602741.p",
            "https://www.bestbuy.com/product/apple-macbook-air-13-inch-laptop-apple-m2-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/JJGCQ8WQR5/sku/6602763"
        ],
        max_review_pages=1
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)


    search_data = await bestbuy.scrape_search(
        search_query="macbook",
        max_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


    review_data = await bestbuy.scrape_reviews(
        skuid="6565065",
        max_pages=3        
    )
    with open(output.joinpath("reviews.json"), "w", encoding="utf-8") as file:
        json.dump(review_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())