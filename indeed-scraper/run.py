"""
This example run script shows how to run the Indeed.com scraper defined in ./indeed.py
It scrapes hotel data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import indeed

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    indeed.BASE_CONFIG["cache"] = True

    print("running Indeed scrape and saving results to ./results directory")

    url = "https://www.indeed.com/jobs?q=python&l=Texas"
    result_search = await indeed.scrape_search(url, max_results=100)
    output.joinpath("search.json").write_text(json.dumps(result_search, indent=2, ensure_ascii=False), encoding="utf-8")

    jobs = ["9100493864fe1d6e", "5361f22542fe4a95"]
    result_jobs = await indeed.scrape_jobs(jobs)
    output.joinpath("jobs.json").write_text(json.dumps(result_jobs, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
