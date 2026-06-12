"""
This example run script shows how to run the airfrance.fr scraper defined in ./airfrance.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import airfrance

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

DEPARTURE = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
RETURN = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")


def run():
    print("running Air France scrape and saving results to ./results directory")

    roundtrip = airfrance.scrape_flights(
        origin="PAR",
        destination="TYO",
        departure_date=DEPARTURE,
        return_date=RETURN,
    )
    
    with open(output / "roundtrip.json", "w", encoding="utf-8") as f:
        json.dump(roundtrip, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run()
