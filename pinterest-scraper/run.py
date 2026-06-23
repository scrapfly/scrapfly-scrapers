"""
This example run script shows how to run the Pinterest.com scraper defined in ./pinterest.py
It scrapes pin search results and saves them to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path

import pinterest

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    pinterest.BASE_CONFIG["debug"] = True

    print("running Pinterest scrape and saving results to ./results directory")

    query = "home office desk"
    search_data = await pinterest.scrape_pinterest(query=query, max_pages=3)
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, indent=2, ensure_ascii=False)
    print(f"saved {len(search_data['pins'])} pins to results/search.json")


if __name__ == "__main__":
    asyncio.run(run())
