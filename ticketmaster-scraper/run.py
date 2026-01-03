"""
This example run script shows how to run the Ticketmaster.com scraper defined in ./ticketmaster.py
It scrapes artist and event data and saves it to ./results/
To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import ticketmaster
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    ticketmaster.BASE_CONFIG["cache"] = True

    log.info("running Ticketmaster scrape and saving results to ./results directory")
    
    log.info("scraping artist page")
    artist_data = await ticketmaster.scrape_artist(
        urls=[
            "https://www.ticketmaster.com/imagine-dragons-tickets/artist/1435919",
            "https://www.ticketmaster.com/george-lopez-tickets/artist/770234"
        ]
    )
    with open(output.joinpath("artist.json"), "w", encoding="utf-8") as file:
        json.dump(artist_data, file, indent=2, ensure_ascii=False)

    log.info("scraping discovery page")
    filters = {
        "classificationId": "KnvZfZ7vAvv",
        "startDate": "2026-01-03",
        "endDate": "2026-01-10"
    }
    discovery_data = await ticketmaster.scrape_discovery("https://www.ticketmaster.com/discover/concerts", **filters)
    with open(output.joinpath("discovery.json"), "w", encoding="utf-8") as file:
        json.dump(discovery_data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())
