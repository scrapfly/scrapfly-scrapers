"""
This example run script shows how to run the perplexity.ai scraper defined in ./perplexity.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import perplexity

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    perplexity.BASE_CONFIG["debug"] = True

    print("running Perplexity scrape and saving results to ./results directory")

    result = await perplexity.scrape_answer("What is the best web scraping API in 2026?")
    with open(output / "answer.json", "w", encoding="utf-8") as f:
        if isinstance(result, str):
            f.write(result)
        else:
            json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
