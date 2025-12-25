"""
This example run script shows how to run the imovelweb.com scraper defined in ./imovelweb.py
It scrapes product data and product search and saves it to ./results/
To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import imovelweb
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# enable scrapfly cache for basic use
imovelweb.BASE_CONFIG["cache"] = True


async def run():
    log.info("running Imovelweb scrape and saving results to ./results directory")

    log.info("scraping property page")
    property_data = await imovelweb.scrape_properties(
        urls=[
            "https://www.immoweb.be/en/classified/apartment/for-rent/wemmel/1780/21247396",
            "https://www.immoweb.be/en/classified/apartment/for-rent/strombeek-bever/1853/21246666",
            "https://www.immoweb.be/en/classified/apartment/for-rent/merchtem/1785/21225730"
        ]
    )
    with open(output.joinpath("property.json"), "w", encoding="utf-8") as file:
        json.dump(property_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
