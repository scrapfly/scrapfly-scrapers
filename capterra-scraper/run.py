"""
This example run script shows how to run the capterra.com scraper defined in ./capterra.py
It scrapes category and review data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import capterra

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():

    # print("running Capterra scrape and saving results to ./results directory")

    category_data = await capterra.scrape_category(
        category="project-management-software",
        max_pages=3,
    )
    with open(output.joinpath("category.json"), "w", encoding="utf-8") as file:
        json.dump(category_data, file, indent=2, ensure_ascii=False)

    reviews_data = await capterra.scrape_reviews(
        url="https://www.capterra.com/p/211559/Trello/",
        max_review_pages=3,
    )
    with open(output.joinpath("reviews.json"), "w", encoding="utf-8") as file:
        json.dump(reviews_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
