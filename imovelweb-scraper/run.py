import asyncio
import os
import json
import re
from pathlib import Path
import imovelweb
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# enable scrapfly cache
imovelweb.BASE_CONFIG["cache"] = True


async def run():
    log.info("running Imovelweb scrape and saving results to ./results directory")

    log.info("scraping search page")
    search_data = await imovelweb.scrape_search(
        location="sao-paulo-sp",
        property_type="apartamentos",
        for_sale=False,
        max_pages=3,
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    log.info("scraping property page")
    urls = [item["url"] for item in search_data["search_properties"] if item.get("url")][:3]
    property_data = await imovelweb.scrape_properties(urls=urls)
    with open(output.joinpath("property.json"), "w", encoding="utf-8") as file:
        json.dump(property_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())