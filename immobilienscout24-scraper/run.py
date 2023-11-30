"""
This example run script shows how to run the immobilienscout24.de scraper defined in ./immobilienscout24.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import immobilienscout24

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

async def run():

    print("running Immobilienscout24 scrape and saving results to ./results directory")

    search_data = await immobilienscout24.scrape_search(
        url="https://www.immobilienscout24.de/Suche/de/bayern/muenchen/wohnung-mieten?pagenumber=1",
        scrape_all_pages=False,
        max_scrape_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    properties_data = await immobilienscout24.scrape_properties(
        urls = [
            "https://www.immobilienscout24.de/expose/147036156#/",
            "https://www.immobilienscout24.de/expose/145570700#/",
            "https://www.immobilienscout24.de/expose/139851227#/",
            "https://www.immobilienscout24.de/expose/146053176#/"
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())    