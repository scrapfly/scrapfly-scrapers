"""
This example run script shows how to run the Naver.com scraper defined in ./naver.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import naver

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # Enable scrapfly cache for basic use
    naver.BASE_CONFIG["cache"] = False

    print("running Naver scrape and saving results to ./results directory")

    # Scrape web search results
    search_data = await naver.scrape_web_search(query="파이썬", max_pages=3, period="6m")
    with open(output.joinpath("web_search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)
    
    # Scrape image search results
    image_data = await naver.scrape_image_search(query="파이썬", max_pages=3, period="6m")
    with open(output.joinpath("image_search.json"), "w", encoding="utf-8") as file:
        json.dump(image_data, file, indent=2, ensure_ascii=False)

    # Scrape blog posts
    blog_posts = await naver.scrape_blog_post([
        "https://blog.naver.com/cherry_27_/224290687381",
        "https://blog.naver.com/jylove_0120/224289170856",
        "https://blog.naver.com/oro-mam/224289142276"
    ])
    with open(output.joinpath("blog_post.json"), "w", encoding="utf-8") as file:
        json.dump(blog_posts, file, indent=2, ensure_ascii=False)

    # Scrape news articles
    news_articles = await naver.scrape_news_article([
        "https://n.news.naver.com/article/001/0015234567",
        "https://n.news.naver.com/article/001/0015234568",
        "https://n.news.naver.com/article/001/0015234569",
    ])
    with open(output.joinpath("news_article.json"), "w", encoding="utf-8") as file:
        json.dump(news_articles, file, indent=2, ensure_ascii=False)
if __name__ == "__main__":
    asyncio.run(run())
