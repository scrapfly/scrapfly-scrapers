"""
This example run script shows how to run the TikTok.com scraper defined in ./tiktok.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import tiktok

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache
    tiktok.BASE_CONFIG["cache"] = False
    tiktok.BASE_CONFIG["debug"] = True

    print("running TikTok scrape and saving results to ./results directory")

    commnets_data = await tiktok.scrape_comments(
        # the post/video URL containing the comments
        post_url='https://www.tiktok.com/@oddanimalspecimens/video/7198206283571285294',
        # total comments to scrape, omitting it will scrape all the avilable comments
        max_comments=24,
        # default is 20, it can be overriden to scrape more comments in each call but it can't be > the total comments on the post
        comments_count=20
    )
    with open(output.joinpath("comments.json"), "w", encoding="utf-8") as file:
        json.dump(commnets_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
