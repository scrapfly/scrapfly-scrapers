"""
This example run script shows how to run the zoopla.com scraper defined in ./zoopla.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import zoopla

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

async def run():
    # enable scrapfly cache for basic use
    zoopla.BASE_CONFIG["cache"] = True

    print("running zoopla scrape and saving results to ./results directory")

    properties_data = await zoopla.scrape_properties(
        urls=[
            "https://www.zoopla.co.uk/new-homes/details/67644732/",
            "https://www.zoopla.co.uk/new-homes/details/66702316/",
            "https://www.zoopla.co.uk/new-homes/details/67644753/"
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)

    search_data = await zoopla.scrape_search(
        scrape_all_pages=False,
        max_scrape_pages=2,
        # make sure you location_slug is valid first by using it in the search
        location_slug="london/islington",
        query_type= "to-rent"
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())