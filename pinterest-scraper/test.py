import os

import pinterest
import pytest
from cerberus import Validator

pinterest.BASE_CONFIG["cache"] = os.getenv("SCRAPFLY_CACHE") == "true"

pin_schema = {
    "pin_id": {"type": "string"},
    "url": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "alt_text": {"type": "string", "nullable": True},
    "image": {"type": "string", "nullable": True},
    "image_thumb": {"type": "string", "nullable": True},
    "destination_link": {"type": "string", "nullable": True},
    "video_url": {"type": "string", "nullable": True},
    "is_product": {"type": "boolean"},
    "board": {"type": "string", "nullable": True},
    "owner": {"type": "string", "nullable": True},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    result = await pinterest.scrape_pinterest(query="home office desk", max_pages=2)
    assert len(result["pins"]) >= 5

    validator = Validator(pin_schema, allow_unknown=True)
    for pin in result["pins"]:
        assert validator.validate(pin), {"pin": pin, "errors": validator.errors}
