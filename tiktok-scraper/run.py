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

    posts_data = await tiktok.scrape_posts(
        urls=[
            "https://www.tiktok.com/@oddanimalspecimens/video/7198206283571285294"
        ]
    )
    with open(output.joinpath("posts.json"), "w", encoding="utf-8") as file:
        json.dump(posts_data, file, indent=2, ensure_ascii=False)

    commnets_data = await tiktok.scrape_comments(
        # the post/video URL containing the comments
        post_url='https://www.tiktok.com/@oddanimalspecimens/video/7198206283571285294',
    )
    with open(output.joinpath("comments.json"), "w", encoding="utf-8") as file:
        json.dump(commnets_data, file, indent=2, ensure_ascii=False)

    profiles_data = await tiktok.scrape_profiles(
        urls=[
            "https://www.tiktok.com/@oddanimalspecimens"
        ]
    )
    with open(output.joinpath("profiles.json"), "w", encoding="utf-8") as file:
        json.dump(profiles_data, file, indent=2, ensure_ascii=False)

    search_data = await tiktok.scrape_search(keyword="whales")
    # the search scraper scrolls the search page to load results dynamically
    # it will scroll up to 15 times (configurable in the js scroll code)
    # the results are extracted from XHR calls captured during scrolling
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


    channel_data = await tiktok.scrape_channel(
        url="https://www.tiktok.com/@oddanimalspecimens"
    )
    with open(output.joinpath("channel.json"), "w", encoding="utf-8") as file:
        json.dump(channel_data, file, indent=2, ensure_ascii=False)    


if __name__ == "__main__":
    asyncio.run(run())
