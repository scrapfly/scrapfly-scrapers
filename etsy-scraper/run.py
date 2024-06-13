"""
This example run script shows how to run the etsy.com scraper defined in ./etsy.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import etsy

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    etsy.BASE_CONFIG["cache"] = False

    print("running Etsy scrape and saving results to ./results directory")

    search_data = await etsy.scrape_search(
        url="https://www.etsy.com/search?q=wood+laptop+stand", max_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    product_data = await etsy.scrape_product(
        urls = [
            "https://www.etsy.com/listing/971370843",
            "https://www.etsy.com/listing/529765307",
            "https://www.etsy.com/listing/949905096"
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)

    product_data = await etsy.scrape_shop(
        urls = [
            "https://www.etsy.com/shop/FalkelDesign",
            "https://www.etsy.com/shop/JoshuaHouseCrafts",
            "https://www.etsy.com/shop/Oakywood"
        ]
    )
    with open(output.joinpath("shops.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)  


if __name__ == "__main__":
    asyncio.run(run())
