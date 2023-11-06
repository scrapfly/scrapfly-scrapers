"""
This example run script shows how to run the immoscout24.ch scraper defined in ./immoscout24.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import immoscout24

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    immoscout24.BASE_CONFIG["cache"] = True

    print("running Immoscout24 scrape and saving results to ./results directory")

    properties_data = await immoscout24.scrape_properties(
        urls=[
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8068164",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/7940339",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8068179",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8068176",
            "https://www.immoscout24.ch/en/d/flat-rent-bern/8029198",
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)

    search_data = await immoscout24.scrape_search(
        # change the "rent" in the URL to "buy" to search for properties for sale
        url="https://www.immoscout24.ch/en/real-estate/rent/city-bern",
        scrape_all_pages=False,
        max_scrape_pages=2,
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2)


if __name__ == "__main__":
    asyncio.run(run())
