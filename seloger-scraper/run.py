"""
This example run script shows how to run the seloger.com scraper defined in ./seloger.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import seloger

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    seloger.BASE_CONFIG["cache"] = True

    print("running Seloger scrape and saving results to ./results directory")

    search_data = await seloger.scrape_search(
        url="https://www.seloger.com/immobilier/achat/immo-bordeaux-33/bien-appartement/",
        scrape_all_pages=False,
        max_pages=2,
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    property_data = await seloger.scrape_property(
        url="https://www.seloger.com/annonces/achat/appartement/bordeaux-33/grand-parc-chartrons-paul-doumer/207269613.htm"
    )
    with open(output.joinpath("property.json"), "w", encoding="utf-8") as file:
        json.dump(property_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
