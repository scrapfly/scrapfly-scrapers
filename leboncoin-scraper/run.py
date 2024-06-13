"""
This example run script shows how to run the leboncoin.com scraper defined in ./leboncoin.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import leboncoin

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    leboncoin.BASE_CONFIG['cache'] = False

    print("running Leboncoin scrape and saving results to ./results directory")
    
    # search = await leboncoin.scrape_search(url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=2, scrape_all_pages=False)
    # with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
    #     json.dump(search, file, indent=2, ensure_ascii=False)

    ad = await leboncoin.scrape_ad(url="https://www.leboncoin.fr/arts_de_la_table/2426724825.htm")
    with open(output.joinpath("ad.json"), "w", encoding="utf-8") as file:
        json.dump(ad, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
