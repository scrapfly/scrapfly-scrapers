"""
This example run script shows how to run the wellfound.com scraper defined in ./wellfound.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import wellfound

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    wellfound.BASE_CONFIG["cache"] = False

    print("running Wellfound scrape and saving results to ./results directory")

    companies_data = await wellfound.scrape_companies(
        urls = [
            "https://www.wellfound.com/company/moxion-power-co/jobs"
        ]
    )
    with open(output.joinpath("companies.json"), "w", encoding="utf-8") as file:
        json.dump(companies_data, file, indent=2, ensure_ascii=False) 

    search_data = await wellfound.scrape_search(
        # you can also add a location parameter
        role="python-developer", max_pages=2
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)    


if __name__ == "__main__":
    asyncio.run(run())
