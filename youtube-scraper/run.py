"""
This example run script shows how to run the YouTube.com scraper defined in ./youtube.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import youtube

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache
    youtube.BASE_CONFIG["cache"] = True
    youtube.BASE_CONFIG["debug"] = True

    print("running YouTube scrape and saving results to ./results directory")

    video_data = await youtube.scrape_video(
        ids = [
            "1Y-XvvWlyzk",
            "muo6I9XY8K4",
            "y7FbFJ4jOW8"
        ]
    )
    with open(output.joinpath("videos.json"), "w", encoding="utf-8") as file:
        json.dump(video_data, file, indent=2, ensure_ascii=False)

    comment_data = await youtube.scrape_comments(
        video_id="FgakZw6K1QQ",
        max_scrape_pages=3
    )
    with open(output.joinpath("comments.json"), "w", encoding="utf-8") as file:
        json.dump(comment_data, file, indent=2, ensure_ascii=False)

    channel_data = await youtube.scrape_channel(
        channel_ids=[
            "scrapfly"
        ]
    )
    with open(output.joinpath("channels.json"), "w", encoding="utf-8") as file:
        json.dump(channel_data, file, indent=2, ensure_ascii=False)

    channel_videos = await youtube.scrape_channel_videos(
        channel_id="statquest", sort_by="Latest", max_scrape_pages=2
    )
    with open(output.joinpath("channel_videos.json"), "w", encoding="utf-8") as file:
        json.dump(channel_videos, file, indent=2, ensure_ascii=False)

    search_data = await youtube.scrape_search(
        search_query="python",
        # params are the additional search query filter
        # to get the search query param string, apply filters on the web app and copy the sp value
        search_params="EgQIAxAB", # filter by video results only
        max_scrape_pages=2
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    shorts_data = await youtube.scrape_shorts(
        ids=[
            "rZ2qqtNPSBk"
        ]
    )
    with open(output.joinpath("shorts.json"), "w", encoding="utf-8") as file:
        json.dump(shorts_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
