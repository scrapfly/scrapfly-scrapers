"""
This example run script shows how to run the Pinterest.com scraper defined in ./pinterest.py
It scrapes pin search results, a board, a profile, a single pin, and downloads pin
images, saving everything to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path

import pinterest

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    pinterest.BASE_CONFIG["debug"] = True

    print("running Pinterest scrape and saving results to ./results directory")

    query = "home office desk"
    search_data = await pinterest.scrape_search(query=query, max_pages=3)
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, indent=2, ensure_ascii=False)
    print(f"saved {len(search_data['pins'])} pins to results/search.json")

    board_data = await pinterest.scrape_board("https://www.pinterest.com/nasa/mars/", max_pages=2)
    with open(output / "board.json", "w", encoding="utf-8") as f:
        json.dump(board_data, f, indent=2, ensure_ascii=False)
    print(f"saved {len(board_data['pins'])} pins to results/board.json")

    profile_data = await pinterest.scrape_profile("nasa", max_pages=2)
    with open(output / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    print(f"saved {len(profile_data['pins'])} pins to results/profile.json")

    pin_data = await pinterest.scrape_pin("https://www.pinterest.com/pin/4608941770563535744/")
    with open(output / "pin.json", "w", encoding="utf-8") as f:
        json.dump(pin_data, f, indent=2, ensure_ascii=False)
    print("saved pin details to results/pin.json")

    download_results = await pinterest.download_pin_images(board_data["pins"][:1], output / "downloads")
    print(f"downloaded {sum(r['success'] for r in download_results)} pin images to results/downloads")


if __name__ == "__main__":
    asyncio.run(run())
