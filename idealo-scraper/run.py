"""
This example run script shows how to run the idealo.de scraper defined in ./idealo.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path

import idealo

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    idealo.BASE_CONFIG["cache"] = True
    idealo.BASE_CONFIG["debug"] = True

    print("running idealo.de scrape and saving results to ./results directory")

    products = await idealo.scrape_products(
        urls=[
            "https://www.idealo.de/preisvergleich/OffersOfProduct/207643424.html",
            "https://www.idealo.de/preisvergleich/OffersOfProduct/207644441.html",
        ]
    )
    with open(output / "products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    search_results = await idealo.scrape_search(query="sonnenfinsternis brillen")
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_results, f, indent=2, ensure_ascii=False)

    manufacturer = await idealo.scrape_manufacturer(url="https://www.idealo.de/preisvergleich/Hersteller/1274.html")
    with open(output / "manufacturer.json", "w", encoding="utf-8") as f:
        json.dump(manufacturer, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
