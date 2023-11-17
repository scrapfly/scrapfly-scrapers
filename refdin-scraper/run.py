"""
This example run script shows how to run the Refdin scraper defined in ./refdin.py
It scrapes real estate data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import refdin

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    refdin.BASE_CONFIG["cache"] = True

    print("running Refdin scrape and saving results to ./results directory")

    search_data = await refdin.scrape_search(
        url="https://www.redfin.com/city/16163/WA/Seattle"
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    properties_sale_data = await refdin.scrape_property_for_sale(
        urls=[
            "https://www.redfin.com/WA/Seattle/506-E-Howell-St-98122/unit-W303/home/46456",
            "https://www.redfin.com/WA/Seattle/1105-Spring-St-98104/unit-405/home/12305595",
            "https://www.redfin.com/WA/Seattle/10116-Myers-Way-S-98168/home/186647",
            
        ]
    )
    with open(output.joinpath("properties_for_sale.json"), "w", encoding="utf-8") as file:
        json.dump(properties_sale_data, file, indent=2, ensure_ascii=False)

    properties_rent_data = await refdin.scrape_property_for_rent(
        urls=[
            "https://www.redfin.com/WA/Seattle/Onni-South-Lake-Union/apartment/147020546",
            "https://www.redfin.com/WA/Seattle/The-Ivey-on-Boren/apartment/146904423",
            "https://www.redfin.com/WA/Seattle/Broadstone-Strata/apartment/178439949",
        ]
    )
    with open(output.joinpath("properties_for_rent.json"), "w", encoding="utf-8") as file:
        json.dump(properties_rent_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
