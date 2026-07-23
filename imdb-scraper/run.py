"""
This example run script shows how to run the imdb.com scraper defined in ./imdb.py
It scrapes title, review, search, chart and person data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import imdb

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    imdb.BASE_CONFIG["cache"] = False

    print("running IMDb scrape and saving results to ./results directory")

    titles = await imdb.scrape_titles(urls=["https://www.imdb.com/title/tt0111161/"])
    with open(output.joinpath("title.json"), "w", encoding="utf-8") as file:
        json.dump(titles, file, indent=2, ensure_ascii=False)

    reviews = await imdb.scrape_reviews(title_id="tt0111161")
    with open(output.joinpath("reviews.json"), "w", encoding="utf-8") as file:
        json.dump(reviews, file, indent=2, ensure_ascii=False)

    search_results = await imdb.scrape_search(query="shawshank")
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_results, file, indent=2, ensure_ascii=False)

    chart = await imdb.scrape_chart(chart_type="top")
    with open(output.joinpath("chart.json"), "w", encoding="utf-8") as file:
        json.dump(chart, file, indent=2, ensure_ascii=False)

    person = await imdb.scrape_person(person_id="nm0000209")
    with open(output.joinpath("person.json"), "w", encoding="utf-8") as file:
        json.dump(person, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
