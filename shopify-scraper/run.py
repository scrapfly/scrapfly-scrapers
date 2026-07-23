"""
This example run script shows how to run the Shopify scraper defined in ./shopify.py
It scrapes catalog data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import shopify

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    shopify.BASE_CONFIG["cache"] = True

    print("running Shopify scrape and saving results to ./results directory")

    catalog = await shopify.scrape_catalog(store_url="https://www.allbirds.com", limit=10, max_pages=2)
    with open(output / "catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    products = await shopify.scrape_products(
        handles=["mens-cruiser-shadow-blue-natural-white-sole"],
        store_url="https://www.allbirds.com",
    )
    with open(output / "product.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


    sitemap = await shopify.scrape_sitemap(sitemap_url="https://www.gymshark.com/sitemap_pages_1.xml")
    with open(output / "sitemap.json", "w", encoding="utf-8") as f:
        json.dump(sitemap, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
