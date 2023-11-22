"""
This example run script shows how to run the Twitter.com scraper defined in ./twitter.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
from pathlib import Path
import asyncio
import json
import twitter

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    twitter.BASE_CONFIG["debug"] = True

    print("running X.com tweet scrape and saving results to ./results directory")

    url = "https://x.com/robinhanson/status/1621310291030974465"
    tweet = await twitter.scrape_tweet(url)
    output.joinpath("tweet.json").write_text(json.dumps(tweet, indent=2, ensure_ascii=False))
    
    url = "https://twitter.com/scrapfly_dev"
    profile = await twitter.scrape_profile(url)
    output.joinpath("profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False))



if __name__ == "__main__":
    asyncio.run(run())
