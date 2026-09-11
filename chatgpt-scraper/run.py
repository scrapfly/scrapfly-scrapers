"""
This example run script shows how to run the chatgpt.com scraper defined in ./chatgpt.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
from pathlib import Path
import chatgpt

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    chatgpt.BASE_CONFIG["debug"] = True

    print("running ChatGPT scrape and saving results to ./results directory")

    conversation = await chatgpt.scrape_conversation("What's the capital of France? with Brief History of the city.")
    with open(output / "conversation.md", "w", encoding="utf-8") as f:
        f.write(conversation)


if __name__ == "__main__":
    asyncio.run(run())
