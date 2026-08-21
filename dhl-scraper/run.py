"""
This example run script shows how to run the DHL scraper defined in ./dhl.py
It scrapes tracking data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path

import dhl

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():

    print("running DHL scrape and saving results to ./results directory")

    tracking = await dhl.scrape_tracking("LBAA19526")
    with open(output / "tracking.json", "w", encoding="utf-8") as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
