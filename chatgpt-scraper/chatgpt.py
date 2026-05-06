"""
This is an example web scraper for chatgpt.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from urllib.parse import quote_plus

from pathlib import Path
from typing import List, TypedDict
from loguru import logger as log

from scrapfly import ScrapeConfig, ScrapflyClient


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "country": "US",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class ChatgptConversation(TypedDict):
    pass


js_scenario = [
    {
        "click": {
            "ignore_if_not_visible": True,
            "selector": "#credentials-picker-container #close",
            "multiple": False,
            "ignore": True,
        }
    },
    {
        "click": {
            "ignore": True,
            "ignore_if_not_visible": True,
            "selector": "div[aria-live='polite'] button:first-of-type",
            "multiple": False,
        }
    },
    {
        "wait_for_selector": {
            "selector": "button[data-testid='send-button']",
            "timeout": 15000,
        }
    },
    {"condition": {
        "selector": "button[data-testid='send-button']",
        "selector_state": "not_existing",
        "action": "exit_failed",
    }
    },
    {
        "click": {
            "selector": "button[data-testid='send-button']",
            "ignore_if_not_visible": False,
            "multiple": False,
        }
    },
    {"wait": 10000},
    {
        "condition": {
            "selector": "button[data-testid='send-button']",
            "selector_state": "existing",
            "action": "exit_success",
        }
    },
    {"wait": 5000},
    {
        "wait_for_selector": {
            "selector": "button[data-testid='send-button']",
            "state": "visible",
            "timeout": 15000,
        }
    },
]
    
async def scrape_conversation(prompt: str) -> str:
    url = f"https://chatgpt.com/?prompt={quote_plus(prompt)}"
    log.info("scraping conversation for prompt: {}", prompt)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            format="markdown",
            render_js=True,
            js_scenario=js_scenario,
            rendering_wait=5000,
            **BASE_CONFIG,
        )
    )
    log.debug("scrapfly log: {}", response.scrape_result["log_url"])
    return response.content


def parse_search_queries_from_sse(sse_data: str) -> List[str]:
    queries = []
    for line in sse_data.splitlines():
        line = line.strip()
        if not line.startswith("data:") or line == "data: [DONE]":
            continue
        try:
            data = json.loads(line[len("data:"):].strip())
            smq = data.get("v", {}).get("message", {}).get("metadata", {}).get("search_model_queries", {})
            if smq:
                queries.extend(smq.get("queries", []))
        except (json.JSONDecodeError, AttributeError):
            pass
    return queries


async def scrape_search_queries(prompt: str) -> List[str]:
    queries: List[str] = []
    url = f"https://chatgpt.com/?prompt={quote_plus(prompt)}"
    log.info("scraping search queries for prompt: {}", prompt)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            render_js=True,
            js_scenario=js_scenario,
            rendering_wait=5000,
            **BASE_CONFIG,
        )
    )
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    conversation_calls = [
        x for x in _xhr_calls
        if "backend-anon/f/conversation" in x["url"]
        and x.get("response", {}).get("content_type", "").startswith("text/event-stream")
    ]
    log.debug("scrapfly log: {}", response.scrape_result["log_url"])
    for xhr in conversation_calls:
        if not xhr.get("response"):
            continue
        queries.extend(parse_search_queries_from_sse(xhr["response"]["body"]))
        
    return queries

