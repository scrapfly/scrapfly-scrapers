"""
This example run script shows how to run the Mouser.com scraper defined in ./mouser.py
It scrapes product data and product search and saves it to ./results/
To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import mouser
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# enable scrapfly cache for basic use
mouser.BASE_CONFIG["cache"] = True

async def run():

    log.info("running Mouser scrape and saving results to ./results directory")
    log.info("scraping search page")
    search_data = await mouser.scrape_search("Tool boxs")
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    log.info("scraping product data")
    product_data = await mouser.scrape_product(
        urls=[
            "https://www.mouser.com/ProductDetail/BusBoard-Prototype-Systems/BOX3-1455N-BK?qs=I13xAFqYpRSd61TQKf31Yw%3D%3D",
            "https://www.mouser.com/ProductDetail/Olimex-Ltd/BOX-ESP32-GATEWAY-F?qs=%252BXxaIXUDbq2PKdoOW6%252BSdA%3D%3D",
            "https://www.mouser.com/ProductDetail/Olimex-Ltd/BOX-ESP32-GATEWAY-EA?qs=Rp5uXu7WBW8AcjUyETTTSg%3D%3D"
        ]
    )
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())

