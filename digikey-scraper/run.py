"""
This example run script shows how to run the DigiKey scraper defined in ./digikey.py
It scrapes product, category, and search data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import digikey

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    print("running DigiKey scrape and saving results to ./results directory")

    products = await digikey.scrape_products(
        urls=[
            "https://www.digikey.com/en/products/detail/adafruit-industries-llc/3111/6198256",
            "https://www.digikey.com/en/products/detail/phoenix-contact/2938235/2553505",
            "https://www.digikey.com/en/products/detail/triad-magnetics/F16-150-C2/3986399",
        ]
    )
    with open(output / "products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    category_results = await digikey.scrape_category(
        url="https://www.digikey.com/en/products/filter/industrial-automation-accessories/800",
        max_pages=3
    )
    with open(output / "category.json", "w", encoding="utf-8") as f:
        json.dump(category_results, f, indent=2, ensure_ascii=False)

    search_results = await digikey.scrape_search(keywords="Power Transformers")
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
