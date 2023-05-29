"""
This example run script shows how to run the Glassdoor.com scraper defined in ./glassdoor.py
It scrapes job, review and salary (TODO OVERVIEW?) data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import glassdoor

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    glassdoor.BASE_CONFIG["cache"] = True

    print("running Glassdoor scrape and saving results to ./results directory")

    url = "https://www.glassdoor.com/Jobs/eBay-Jobs-E7853.htm?filter.countryId=1"
    # or use URL builder to build urls from company name and ID
    url = glassdoor.Url.jobs("eBay", "7853", region=glassdoor.Region.UNITED_STATES)
    result_jobs = await glassdoor.scrape_jobs(url, max_pages=3)
    output.joinpath("jobs.json").write_text(json.dumps(result_jobs, indent=2, ensure_ascii=False))

    url = "https://www.glassdoor.com/Salary/eBay-Salaries-E7853.htm"
    result_salaries = await glassdoor.scrape_salaries(url, max_pages=3)
    output.joinpath("salaries.json").write_text(json.dumps(result_salaries, indent=2, ensure_ascii=False))

    url = "https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm"
    result_reviews = await glassdoor.scrape_reviews(url, max_pages=3)
    output.joinpath("reviews.json").write_text(json.dumps(result_reviews, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
