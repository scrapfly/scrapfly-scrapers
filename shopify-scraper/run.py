"""
This example run script shows how to run the Shopify scraper defined in ./shopify.py
It scrapes product data from Shopify storefronts and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import shopify

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# apple.com is included on purpose: it answers /products.json with HTML and HTTP 200,
# which is the semantic mismatch the preflight has to reject
STORE_URLS = [
    "https://www.allbirds.com",
    "https://www.deathwishcoffee.com",
    "https://www.apple.com",
]

PRODUCT_URLS = [
    "https://www.allbirds.com/products/mens-strider-medium-grey",
    "https://www.deathwishcoffee.com/products/vanilla-10oz",
]


async def run():
    shopify.BASE_CONFIG["cache"] = True
    shopify.CLASSIFY_CONFIG["cache"] = True

    print("running Shopify scrape and saving results to ./results directory")

    preflight = await shopify.check_shopify_stores(store_urls=STORE_URLS)
    with open(output / "preflight.json", "w", encoding="utf-8") as f:
        json.dump(preflight, f, indent=2, ensure_ascii=False)

    catalog = await shopify.scrape_catalog(store_url="https://www.allbirds.com", max_pages=2, limit=20)
    with open(output / "catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    collection = await shopify.scrape_collection(
        store_url="https://www.deathwishcoffee.com", collection="coffee", max_pages=1, limit=20
    )
    with open(output / "collection.json", "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)

    product_pages = await shopify.scrape_product_pages(urls=PRODUCT_URLS)
    with open(output / "product_pages.json", "w", encoding="utf-8") as f:
        json.dump(product_pages, f, indent=2, ensure_ascii=False)

    product_urls = await shopify.scrape_product_urls(store_url="https://www.allbirds.com")
    with open(output / "product_urls.json", "w", encoding="utf-8") as f:
        json.dump(product_urls, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
