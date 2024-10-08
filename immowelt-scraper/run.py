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
            "https://www.immowelt.de/expose/27t9c5f",
            "https://www.immowelt.de/expose/27dgc5f",
            "https://www.immowelt.de/expose/9175275c-9b96-454f-a770-7f4ef0e720be",
            "https://www.immowelt.de/expose/95aba3fb-8449-47d3-8394-9ab71e705160",
            "https://www.immowelt.de/expose/ac9dc8d0-a729-4d79-849e-93ec9d4cf16a"
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)    
    
    search_data = await immowelt.scrape_search(
        url="https://www.immowelt.de/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08DE6345",
        max_scrape_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False) 


if __name__ == "__main__":
    asyncio.run(run())