"""
This example run script shows how to run the zoro.com scraper defined in ./zoro.py
It scrapes product, search listing and review data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import zoro
from loguru import logger as log



output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)



async def run():
    # enable scrapfly cache for basic use
    zoro.BASE_CONFIG["cache"] = True

    log.info("running Zoro scrape and saving results to ./results directory")

    # scrape product
    log.info("scraping product")
    urls = [
        "https://www.zoro.com/proto-general-purpose-double-latch-tool-box-with-tray-steel-red-20-w-x-85-d-x-95-h-j9975r/i/G0067825/",
        "https://www.zoro.com/stanley-series-2000-tool-box-plastic-blackyellow-19-in-w-x-10-14-in-d-x-10-in-h-019151m/i/G6197466/",
        "https://www.zoro.com/ansell-hyflex-coated-gloves-polyurethane-dipped-palm-coated-ansi-abrasion-level-3-black-large-1-pair-48-101/i/G0050565/"
    ]
    product = await zoro.scrape_product(urls)
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product, file, indent=2, ensure_ascii=False)

    # log.info("scraping search listing")
    # search_listing = await zoro.scrape_search_listing("https://www.zoro.com/zoro-search-listing-1")
    # with open(output.joinpath("search_listing.json"), "w", encoding="utf-8") as file:
    #     json.dump(search_listing, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())