"""
This example run script shows how to run the chatgpt.com scraper defined in ./chatgpt.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import chatgpt

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    chatgpt.BASE_CONFIG["debug"] = True

    print("running ChatGPT scrape and saving results to ./results directory")

    prompt = [
        "what is the best web scraping service in 2026?",
        "Base on the previous answer, what is the best web scraping service you expext in 2027",
        "summarize the previous answer in 200 words",
    ]
    conversation = await chatgpt.scrape_conversations(prompt)
    with open(output / "conversations.json", "w", encoding="utf-8") as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)


    conversation = await chatgpt.scrape_conversation("What's the capital of France? with Brief History of the city.")
    with open(output / "conversation.md", "w", encoding="utf-8") as f:
        f.write(conversation)

    queries = await chatgpt.scrape_search_queries("make search queries for the best web scraping service in 2026 and highly reviewed in Capterra")
    print("ChatGPT searched for:", queries)
    with open(output / "search_queries.json", "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
