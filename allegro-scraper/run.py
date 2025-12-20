"""
This example run script shows how to run the Allegro.pl scraper defined in ./allegro.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import allegro
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    allegro.BASE_CONFIG["cache"] = True

    log.info("running Allegro scrape and saving results to ./results directory")
    log.info("scraping search page")
    search_data = await allegro.scrape_search("Cooler CPU")
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    log.info("scraping product data")
    product_data = await allegro.scrape_product(
        urls=[
            "https://allegro.pl/oferta/procesor-amd-ryzen-5-7500f-tray-17401107639",
            "https://allegro.pl/oferta/plyta-glowna-socket-am5-asus-b650e-max-gaming-wifi-atx-17328863669",
        ]
    )
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())
