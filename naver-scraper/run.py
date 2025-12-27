"""
This example run script shows how to run the Naver.com scraper defined in ./naver.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import naver

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # Enable scrapfly cache for basic use
    naver.BASE_CONFIG["cache"] = True

    print("running Naver scrape and saving results to ./results directory")

    # Scrape web search results
    search_data = await naver.scrape_web_search(query="파이썬", max_pages=3, period="6m")
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())
