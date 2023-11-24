"""
This example run script shows how to run the bookingcom scraper defined in ./bookingcom.py
It scrapes search and hotel data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import bookingcom

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


TODAY = datetime.now().strftime('%Y-%m-%d')
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
MONTH_FROM_NOW = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

async def run():
    print("running Booking.com example scrapes and saving results to ./results directory")

    result_search = await bookingcom.scrape_search(
        query="Malta",
        checkin=TODAY,
        checkout=WEEK_FROM_NOW,
        max_pages=2
    )
    output.joinpath("search.json").write_text(json.dumps(result_search, indent=2, ensure_ascii=False), encoding="utf-8")

    result_hotel = await bookingcom.scrape_hotel(
        "https://www.booking.com/hotel/gb/gardencourthotel.en-gb.html",
        checkin=WEEK_FROM_NOW, 
        price_n_days=7,
    )
    output.joinpath("hotel.json").write_text(json.dumps(result_hotel, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
