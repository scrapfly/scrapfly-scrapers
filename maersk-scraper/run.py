"""
This example run script shows how to run the maersk.com scraper defined in ./maersk.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path

import maersk

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    maersk.BASE_CONFIG["cache"] = False
    maersk.BASE_CONFIG["debug"] = True

    print("running Maersk scrape and saving results to ./results directory")

    tracking = await maersk.scrape_tracking("269124324")
    with open(output / "tracking.json", "w", encoding="utf-8") as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)

    schedule = await maersk.scrape_schedule_search(
        from_location="2IW9P6J7XAW72",
        to_location="1JUKNJGWHQBNJ",
        from_rkst_code="CNSGH",
        to_rkst_code="NLROT",
        departure_date="2026-08-15",
    )
    with open(output / "schedule.json", "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
