"""
This example run script shows how to run the Allegro.pl scraper defined in ./allegro.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import allegro

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    allegro.BASE_CONFIG["cache"] = True
    allegro.BASE_CONFIG["country"] = "PL"

    print("running Allegro scrape and saving results to ./results directory")

    product_data = await allegro.scrape_product(
        urls=[
            "https://allegro.pl/oferta/procesor-amd-ryzen-5-7500f-tray-17401107639",
            "https://allegro.pl/oferta/procesor-amd-ryzen-7-9800x3d-8-x-4-7-ghz-gen-9-tray-oem-17252109693",
        ]
    )
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(run())
