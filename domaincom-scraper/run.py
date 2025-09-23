"""
This example run script shows how to run the domain.com.au scraper defined in ./domaincom.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
import domaincom
from pathlib import Path

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    domaincom.BASE_CONFIG["cache"] = False

    print("running Domain.com.au scrape and saving results to ./results directory")

    properties_data = await domaincom.scrape_properties(
        urls = [
            "https://www.domain.com.au/610-399-bourke-street-melbourne-vic-3000-2018835548",
            "https://www.domain.com.au/property-profile/308-9-degraves-street-melbourne-vic-3000",
            "https://www.domain.com.au/1518-474-flinders-street-melbourne-vic-3000-17773317"
        ]
    )
    with open(output.joinpath("properties.json"), "w", encoding="utf-8") as file:
        json.dump(properties_data, file, indent=2, ensure_ascii=False)

    search_data = await domaincom.scrape_search(
        # you can change "sale" to "rent" in the search URL to search for properties for rent
        url="https://www.domain.com.au/sale/melbourne-vic-3000/", max_scrape_pages=1
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
