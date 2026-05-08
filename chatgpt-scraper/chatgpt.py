"""
This is an example web scraper for chatgpt.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import time
from pathlib import Path
from urllib.parse import quote_plus
from uuid import uuid4
from typing import Dict, List, Optional, TypedDict

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "country": "US",
    "debug": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class ChatgptMessage(TypedDict):
    role: str
    content: str


class ChatgptConversation(TypedDict):
    conversation_id: str
    messages: List[ChatgptMessage]


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
    {
        "condition": {
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
    {"wait": 10000},
]


async def scrape_conversation(prompt: str) -> str:
    url = f"https://chatgpt.com/?prompt={quote_plus(prompt)}"
    log.info("scraping conversation for prompt: {}", prompt)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            format="markdown",
            format_options=["only_content"],
            render_js=True,
            js_scenario=js_scenario,
            rendering_wait=5000,
            **BASE_CONFIG,
        )
    )
    log.success("finished scraping ChatGPT for the prompt: {}", prompt)
    return response.content


def parse_chatgpt_stream(raw_sse: str) -> Dict:
    """Parse a ChatGPT SSE stream body into structured messages JSON object.

    ChatGPT SSE events come in three shapes (besides "input_message"):
      1. "v={"message": {...}}" - seed/finalization of a message object.
      2. "v=[{p, o, v}, ...]"  - list of JSON-Patch-like operations.
      3. "v="text"" with sticky "p"/"o" inherited from the previous event.
    """
    messages: Dict[str, dict] = {}
    conversation_id: Optional[str] = None
    current_id: Optional[str] = None
    last_o: Optional[str] = None
    last_p: Optional[str] = None

    def store(msg: dict) -> Optional[str]:
        msg_id = msg.get("id")
        if not msg_id:
            return None
        parts = msg.get("content", {}).get("parts") or [""]
        messages[msg_id] = {
            "role": msg.get("author", {}).get("role", ""),
            "content": parts[0] if isinstance(parts[0], str) else "",
        }
        return msg_id

    def append(path: Optional[str], op: Optional[str], val) -> None:
        if (
            op == "append"
            and isinstance(val, str)
            and path
            and "content/parts/0" in path
            and current_id in messages
        ):
            messages[current_id]["content"] += val

    for line in raw_sse.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        raw = line[len("data:") :].strip()
        if raw == "[DONE]":
            break
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        if data.get("type") == "input_message":
            current_id = store(data.get("input_message", {})) or current_id
            conversation_id = conversation_id or data.get("conversation_id")
            continue

        # Inherit sticky path/op when the event omits them.
        last_o = data.get("o", last_o)
        last_p = data.get("p", last_p)
        v = data.get("v")

        if isinstance(v, dict) and "message" in v:
            current_id = store(v["message"]) or current_id
            conversation_id = (
                conversation_id
                or v.get("conversation_id")
                or v["message"].get("metadata", {}).get("conversation_id")
            )
        elif isinstance(v, list):
            for patch in v:
                append(patch.get("p"), patch.get("o"), patch.get("v"))
        else:
            append(last_p, last_o, v)

    parent_message_id = next(
        (mid for mid, m in reversed(messages.items()) if m["role"] == "assistant"),
        None,
    )
    result_messages: List[ChatgptMessage] = [
        {"role": m["role"], "content": m["content"]}
        for m in messages.values()
        if m["role"] and m["content"]
    ]

    return {
        "conversation_id": conversation_id,
        "parent_message_id": parent_message_id,
        "messages": result_messages,
    }


def _build_post_request(
    prompt: str,
    conversation_id: str,
    parent_message_id: str,
    original_body: dict,
    headers: dict,
) -> dict:
    """Build the JSON body and Headers for a ChatGPT /backend-anon/conversation POST request."""
    new_body = original_body.copy()
    new_body["conversation_id"] = conversation_id
    new_body["parent_message_id"] = parent_message_id
    new_body["messages"] = [
        {
            "id": str(uuid4()),
            "author": {"role": "user"},
            "create_time": time.time(),
            "content": {"content_type": "text", "parts": [prompt]},
        }
    ]

    return {
        "headers": headers,
        "body": new_body,
    }


async def scrape_conversations(prompt: List[str]) -> List[ChatgptConversation]:
    prompt_index = 0
    url = f"https://chatgpt.com/?prompt={quote_plus(prompt[prompt_index])}"
    session = "chatgpt-" + str(uuid4()).replace("-", "")
    conversations: List[ChatgptConversation] = []
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            session=session,
            render_js=True,
            js_scenario=js_scenario,
            rendering_wait=5000,
            **BASE_CONFIG,
        )
    )

    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    conversation_calls = [
        x
        for x in _xhr_calls
        if "backend-anon/f/conversation" in x["url"]
        and x.get("response", {})
        .get("content_type", "")
        .startswith("text/event-stream")
    ]
    for xhr in conversation_calls:
        if not xhr.get("response"):
            continue

        # Parse initial GET SSE stream
        parsed = parse_chatgpt_stream(xhr["response"]["body"])
        conversation_id = parsed.get("conversation_id")
        parent_message_id = parsed.get("parent_message_id")

        if conversation_id:
            conversations.append(
                {
                    "conversation_id": conversation_id,
                    "messages": parsed.get("messages", []),
                }
            )

        original_body = json.loads(xhr["body"])
        headers = xhr.get("headers", {}).copy()

        while prompt_index < len(prompt) - 1:
            prompt_index += 1
            post_request = _build_post_request(
                prompt[prompt_index],
                conversation_id,
                parent_message_id,
                original_body,
                headers,
            )
            post_response = await SCRAPFLY.async_scrape(
                ScrapeConfig(
                    url="https://chatgpt.com/backend-anon/conversation",
                    session=session,
                    method="POST",
                    body=json.dumps(post_request["body"]),
                    headers=post_request["headers"],
                    **BASE_CONFIG,
                )
            )

            # Parse POST SSE response and update state for next iteration
            post_parsed = parse_chatgpt_stream(post_response.content)
            if post_parsed.get("parent_message_id"):
                parent_message_id = post_parsed["parent_message_id"]

            if conversations and post_parsed.get("messages"):
                conversations[-1]["messages"].extend(post_parsed["messages"])

    return conversations
