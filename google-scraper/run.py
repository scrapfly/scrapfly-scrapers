"""
This example run script shows how to run the google.com scraper defined in ./google.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import google

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():

    # enable scrapfly cache for basic usage
    google.BASE_CONFIG["cache"] = True

    print("running Google scrape and saving results to ./results directory")

    search_data = await google.scrape_serp(
        query="scrapgly blog web scraping",
        max_pages=3,
    )
    with open(output.joinpath("serp.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    keyword_data = await google.scrape_keywords(
        query="web scraping emails",
    )
    with open(output.joinpath("keywords.json"), "w", encoding="utf-8") as file:
        json.dump(keyword_data, file, indent=2, ensure_ascii=False)

    google_map_places_urls = await google.find_google_map_places(
        query="museum in paris",
    )
    with open(
        output.joinpath("google_map_places_urls.json"), "w", encoding="utf-8"
    ) as file:
        json.dump(google_map_places_urls, file, indent=2, ensure_ascii=False)

    google_map_places = await google.scrape_google_map_places(
        urls=[
            "https://www.google.com/maps/place/Mus%C3%A9e+d%27Orsay/data=!4m7!3m6!1s0x47e66e2bb630941b:0xd071bd8cb14423d8!8m2!3d48.8599614!4d2.3265614!16zL20vMGYzYjk!19sChIJG5Qwtitu5kcR2CNEsYy9cdA?authuser=0&hl=en&rclk=1",
            "https://www.google.com/maps/place/The+Centre+Pompidou/data=!4m7!3m6!1s0x47e66e1c09b820a3:0xb7ac6c7e59dc3345!8m2!3d48.860642!4d2.352245!16zL20vMGYzMnA!19sChIJoyC4CRxu5kcRRTPcWX5srLc?authuser=0&hl=en&rclk=1",
            "https://www.google.com/maps/place/Mus%C3%A9e+de+l%27Orangerie/data=!4m7!3m6!1s0x47e66e2eeaaaaaa3:0xdc3fd08aa701960a!8m2!3d48.8637884!4d2.3226724!16zL20vMGR0M21s!19sChIJo6qq6i5u5kcRCpYBp4rQP9w?authuser=0&hl=en&rclk=1",
        ]
    )
    with open(output.joinpath("google_map_places.json"), "w", encoding="utf-8") as file:
        json.dump(google_map_places, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
