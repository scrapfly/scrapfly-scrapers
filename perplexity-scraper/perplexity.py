"""
This is an example web scraper for perplexity.ai.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import uuid
from pathlib import Path
from typing import List, TypedDict
from urllib.parse import urlparse
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # the answer API is called directly, so no browser rendering is needed, and with asp
    # perplexity answers with its sign-up wall more often
    "asp": False,
    "country": "US",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# the same parameters the web app sends when a question is asked from the home page
ASK_PARAMS = {
    "attachments": [],
    "language": "en-US",
    "timezone": "America/New_York",
    "search_focus": "internet",
    "sources": ["web"],
    "mode": "copilot",
    "model_preference": "turbo",
    "is_related_query": False,
    "is_sponsored": False,
    "prompt_source": "autosuggest",
    "query_source": "autosuggest",
    "is_incognito": False,
    "local_search_enabled": False,
    "use_schematized_api": True,
    "send_back_text_in_streaming_api": False,
    "supported_block_use_cases": [
        "answer_modes",
        "media_items",
        "inline_entity_cards",
        "place_widgets",
        "finance_widgets",
        "sports_widgets",
        "news_widgets",
        "shopping_widgets",
        "jobs_widgets",
        "search_result_widgets",
        "inline_images",
        "inline_assets",
        "placeholder_cards",
        "diff_blocks",
        "entity_group_v2",
        "refinement_filters",
        "canvas_mode",
        "maps_preview",
        "answer_tabs",
        "price_comparison_widgets",
        "preserve_latex",
        "generic_onboarding_widgets",
        "in_context_suggestions",
        "pending_followups",
        "inline_claims",
        "unified_assets",
        "workflow_steps",
        "workflow_widgets",
        "navigation_results",
        "background_agents",
    ],
    "client_coordinates": None,
    "mentions": [],
    "skip_search_enabled": True,
    "is_nav_suggestions_disabled": False,
    "source": "default",
    "always_search_override": False,
    "override_no_search": False,
    "version": "2.18",
}


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
    """Single-turn: submit one prompt to the perplexity answer API and parse the answer"""
    # the prompt goes in the POST body, the answer comes back as a server-sent event stream
    url = "https://www.perplexity.ai/rest/sse/perplexity_ask"
    params = {**ASK_PARAMS, "frontend_uuid": str(uuid.uuid4()), "frontend_context_uuid": str(uuid.uuid4())}
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            method="POST",
            body=json.dumps({"params": params, "query_str": prompt}),
            render_js=False,
            **BASE_CONFIG,
        )
    )
    content = response.scrape_result["content"]
    # perplexity answers some anonymous requests with a sign-up wall instead of the answer
    if "Sign up and repeat your request." in content:
        raise ValueError(f"perplexity.ai returned its sign-up wall instead of an answer for the prompt: {prompt}")
    data = parse_answer(content)
    if not data["answer_markdown"]:
        raise ValueError(f"perplexity.ai returned no answer text (see log: {response.scrape_result.get('log_url')})")
    log.success(f"scraped perplexity answer for the prompt: {prompt}")
    return data
