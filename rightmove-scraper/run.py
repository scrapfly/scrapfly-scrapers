"""
This example run script shows how to run the rightmove.com scraper defined in ./rightmove.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import rightmove

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    rightmove.BASE_CONFIG["cache"] = True

    print("running rightmove scrape and saving results to ./results directory")

    properties_data = await rightmove.scrape_properties(
        urls=[
            "https://www.rightmove.co.uk/properties/149360984#/",
            "https://www.rightmove.co.uk/properties/136408088#/",
            "https://www.rightmove.co.uk/properties/148922639#/",
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)

    cornwall_id = (await rightmove.find_locations("cornwall"))[0]
    cornwall_results = await rightmove.scrape_search(
        cornwall_id, max_properties=50, scrape_all_properties=False
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(cornwall_results, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
