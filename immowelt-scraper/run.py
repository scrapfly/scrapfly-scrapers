"""
This example run script shows how to run the immowelt.de scraper defined in ./immowelt.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import immowelt

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

async def run():
    # enable scrapfly cache for basic use
    immowelt.BASE_CONFIG["cache"] = True

    print("running Immowelt scrape and saving results to ./results directory")

    properties_data = await immowelt.scrape_properties(
        urls = [
            "https://www.immowelt.de/expose/2czpn55",
            "https://www.immowelt.de/expose/2cw6u5d",
            "https://www.immowelt.de/expose/2c3a95e",
            "https://www.immowelt.de/expose/2cxhm5c",
            "https://www.immowelt.de/expose/2cv4h5c"
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)    
    
    search_data = await immowelt.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=3,
        # the locations ids represent the search address
        # to get the locations ids, search for proeprties on immowet.de and inspect the API requests payload
        location_ids=[4916]
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False) 


if __name__ == "__main__":
    asyncio.run(run())