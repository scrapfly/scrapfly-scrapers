"""
This example run script shows how to run the Crunchbase.com scraper defined in ./crunchbase.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
from pathlib import Path
import asyncio
import json
import crunchbase

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache?
    crunchbase.BASE_CONFIG["cache"] = True

    print("running Crunchbase scrape and saving results to ./results directory")

    url = "https://www.crunchbase.com/organization/tesla-motors/people"
    company = await crunchbase.scrape_company(url)
    output.joinpath("company.json").write_text(json.dumps(company, indent=2, ensure_ascii=False))

    url = "https://www.crunchbase.com/person/danny-hayes-8e1b"
    person = await crunchbase.scrape_person(url)
    output.joinpath("person.json").write_text(json.dumps(person, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
