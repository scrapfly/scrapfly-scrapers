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

    print("running Twitter scrape and saving results to ./results directory")

    url = "https://twitter.com/robinhanson/status/1621310291030974465"
    tweets = await twitter.scrape_tweet(url)
    output.joinpath("tweet.json").write_text(json.dumps(tweets, indent=2, ensure_ascii=False))
    
    url = "https://twitter.com/scrapfly_dev"
    profile = await twitter.scrape_profile(url)
    output.joinpath("profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False))

    url = "https://twitter.com/i/topics/853980498816679937"
    topic = await twitter.scrape_topic(url)
    output.joinpath("topic.json").write_text(json.dumps(topic, indent=2, ensure_ascii=False))



if __name__ == "__main__":
    asyncio.run(run())
