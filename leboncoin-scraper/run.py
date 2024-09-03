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
    leboncoin.BASE_CONFIG['cache'] = True

    print("running Leboncoin scrape and saving results to ./results directory")
    
    search = await leboncoin.scrape_search(url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=2, scrape_all_pages=False)
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search, file, indent=2, ensure_ascii=False)
    
    ad_data = []
    to_scrape = [
        leboncoin.scrape_ad(url)
        for url in [
            "https://www.leboncoin.fr/ad/ventes_immobilieres/2809308201",
            "https://www.leboncoin.fr/ad/ventes_immobilieres/2820947069",
            "https://www.leboncoin.fr/ad/ventes_immobilieres/2787737700"
        ]
    ]
    for response in asyncio.as_completed(to_scrape):
        ad_data.append(await response)    
    with open(output.joinpath("ads.json"), "w", encoding="utf-8") as file:
        json.dump(ad_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
