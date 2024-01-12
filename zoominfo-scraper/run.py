"""
This example run script shows how to run the zoominfo.com scraper defined in ./zoominfo.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import zoominfo

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache
    zoominfo.BASE_CONFIG["cache"] = True

    print("running Zoominfo scrape and saving results to ./results directory")

    companies_data = await zoominfo.scrape_comapnies(
        urls=[
            "https://www.zoominfo.com/c/tesla-inc/104333869",
            "https://www.zoominfo.com/c/microsoft/24904409",
            "https://www.zoominfo.com/c/nvidia-corp/136118787",
        ]
    )
    with open(output.joinpath("companies.json"), "w", encoding="utf-8") as file:
        json.dump(companies_data, file, indent=2, ensure_ascii=False)

    directory_data = await zoominfo.scrape_directory(
        # scrape company page URLs, you can later use these URLs with the scrape_comapnies function to scrape each company data
        url="https://www.zoominfo.com/companies-search/location-usa--california--los-angeles-industry-software",
        scrape_pagination=True,
    )
    with open(output.joinpath("directory.json"), "w", encoding="utf-8") as file:
        json.dump(directory_data, file, indent=2, ensure_ascii=False)

    faq_data = await zoominfo.scrape_faqs(
        url = "https://www.zoominfo.com/c/tesla-inc/104333869",
    )
    with open(output.joinpath("faqs.json"), "w", encoding="utf-8") as file:
        json.dump(faq_data, file, indent=2, ensure_ascii=False)    

if __name__ == "__main__":
    asyncio.run(run())
