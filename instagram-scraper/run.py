"""
This example run script shows how to run the Instagram.com scraper defined in ./instagram.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
from pathlib import Path
from loguru import logger as log
import asyncio
import json
import instagram

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache?
    instagram.BASE_CONFIG["cache"] = True
    instagram.BASE_CONFIG["debug"] = True

    print("running Instagram scrape and saving results to ./results directory")

    user = await instagram.scrape_user("google")
    output.joinpath("user.json").write_text(json.dumps(user, indent=2, ensure_ascii=False), encoding='utf-8')

    post_video = await instagram.scrape_post("https://www.instagram.com/p/Cs9iEotsiGY/")
    output.joinpath("video-post.json").write_text(json.dumps(post_video, indent=2, ensure_ascii=False), encoding='utf-8')

    post_multi_image = await instagram.scrape_post("https://www.instagram.com/p/Csthn7EO99u/")
    output.joinpath("multi-image-post.json").write_text(json.dumps(post_multi_image, indent=2, ensure_ascii=False), encoding='utf-8')

    # scrape_user_posts requires the profile username
    posts_all = []
    async for post in instagram.scrape_user_posts("google", max_pages=3):
        posts_all.append(post)
    log.success("scraped {} posts", len(posts_all))
    output.joinpath("all-user-posts.json").write_text(json.dumps(posts_all, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == "__main__":
    asyncio.run(run())
