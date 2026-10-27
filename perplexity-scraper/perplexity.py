"""
This is an example web scraper for perplexity.ai.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import base64
import os
import json
from pathlib import Path
from typing import List, TypedDict
from urllib.parse import urlparse
from loguru import logger as log
from playwright.async_api import async_playwright
from scrapfly import BrowserConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
# perplexity answers anonymous questions asked from a real browser on a residential connection; questions sent
# straight to its answer API get the sign-up wall. The question is asked in Scrapfly's cloud browser like a visitor.
BASE_CONFIG = {
    "proxy_pool": "residential",
    "country": "US",
    "os": "macos",
    "cache": True,  # cache static resources (scripts, styles) between sessions
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class PerplexityAnswer(TypedDict):
    query: str
    answer_markdown: str
    cited_domains: List[str]
    source_count: int
    follow_ups: List[str]


def parse_answer(content: str) -> PerplexityAnswer:
    """parse the answer from the final event of the server-sent event stream"""
    events = []
    for line in content.splitlines():
        if line.startswith("data:") and line[5:].strip().startswith("{"):
            events.append(json.loads(line[5:]))
    final = next((event for event in reversed(events) if event.get("final")), None)
    if final is None:
        raise ValueError("perplexity.ai returned no final answer event")

    answer = ""
    web_results = []
    for block in final.get("blocks", []):
        for step in (block.get("workflow_block") or {}).get("steps", []):
            for item in step.get("items", []):
                text_payload = (item.get("payload") or {}).get("text_payload") or {}
                if text_payload.get("variant") == "answer" and text_payload.get("text"):
                    answer = text_payload["text"]
        web_results = (block.get("web_result_block") or {}).get("web_results") or web_results

    cited_domains = []
    for result in web_results:
        domain = urlparse(result["url"]).netloc.removeprefix("www.")
        if domain not in cited_domains:
            cited_domains.append(domain)

    return {
        "query": final.get("query_str"),
        "answer_markdown": answer,
        "cited_domains": cited_domains,
        "source_count": len(web_results),
        "follow_ups": final.get("related_queries") or [],
    }


async def scrape_answer(prompt: str) -> PerplexityAnswer:
    """Single-turn: ask one prompt on perplexity.ai in Scrapfly's cloud browser and parse the answer"""
    config = BrowserConfig(**BASE_CONFIG, target_url="https://www.perplexity.ai/")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(SCRAPFLY.cloud_browser(config), timeout=120_000)
        try:
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            # the page asks its answer API itself; its answer is a server-sent event stream that stays open after
            # the final event, so the stream is read from the browser's network events while it arrives
            stream = {"request_id": None, "chunks": []}
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.enable")

            def request_sent(event):
                if "/rest/sse/perplexity_ask" in event["request"]["url"] and stream["request_id"] is None:
                    stream["request_id"] = event["requestId"]

            async def read_stream(event):
                if event["requestId"] == stream["request_id"]:
                    result = await cdp.send("Network.streamResourceContent", {"requestId": event["requestId"]})
                    stream["chunks"].append(base64.b64decode(result.get("bufferedData", "")).decode("utf-8", "replace"))

            def data_received(event):
                if event["requestId"] == stream["request_id"] and event.get("data"):
                    stream["chunks"].append(base64.b64decode(event["data"]).decode("utf-8", "replace"))

            cdp.on("Network.requestWillBeSent", request_sent)
            cdp.on("Network.responseReceived", lambda event: asyncio.ensure_future(read_stream(event)))
            cdp.on("Network.dataReceived", data_received)

            log.info(f"asking perplexity: {prompt}")
            await page.goto("https://www.perplexity.ai/", wait_until="domcontentloaded", timeout=120_000)
            ask_input = page.locator("#ask-input")
            await ask_input.wait_for(timeout=30_000)
            try:
                await ask_input.click(timeout=10_000)
            except Exception:  # a dialog in front of the page: focus the input instead
                await ask_input.focus()
            await page.keyboard.type(prompt, delay=50)
            await page.keyboard.press("Enter")

            content = ""
            for _ in range(90):  # the answer usually arrives within 15 seconds
                content = "".join(stream["chunks"])
                # perplexity answers some anonymous visitors with a sign-up wall instead of the answer
                if "Sign up and repeat your request." in content:
                    raise ValueError(
                        f"perplexity.ai returned its sign-up wall instead of an answer for the prompt: {prompt}"
                    )
                try:
                    data = parse_answer(content)
                except ValueError:  # no final event yet
                    data = None
                if data and data["answer_markdown"]:
                    log.success(f"scraped perplexity answer for the prompt: {prompt}")
                    return data
                await page.wait_for_timeout(1000)
            raise ValueError(f"perplexity.ai sent no answer within 90 seconds for the prompt: {prompt}")
        finally:
            await browser.close()
