"""
This example run script shows how to run the bing.com scraper defined in ./bing.py
It scrapes ads data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import bing

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    bing.BASE_CONFIG["cache"] = True

    print("running Bing scrape and saving results to ./results directory")

    serp_data = await bing.scrape_search(query="web scraping emails", max_pages=3)
    with open(output.joinpath("serps.json"), "w", encoding="utf-8") as file:
        json.dump(serp_data, file, indent=2, ensure_ascii=False)

    keyword_data = await bing.scrape_keywords(query="web scraping emails")
    with open(output.joinpath("keywords.json"), "w", encoding="utf-8") as file:
        json.dump(keyword_data, file, indent=2, ensure_ascii=False)

    rich_snippet_data = await bing.scrape_rich_snippets(query="Google Chrome")
    with open(output.joinpath("rich_snippets.json"), "w", encoding="utf-8") as file:
        json.dump(rich_snippet_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
