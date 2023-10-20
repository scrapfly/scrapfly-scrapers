import asyncio
import json
from pathlib import Path
import leboncoin

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    leboncoin.BASE_CONFIG = True

    print("running Leboncoin scrape and saving results to ./results directory")
    
    search = await leboncoin.scrape_search(url="https://www.leboncoin.fr/recherche?text=coffe", max_pages=2, scrape_all_pages=False)
    output.joinpath("search.json").write_text(json.dumps(search, indent=2, ensure_ascii=False))

    ad = asyncio.run(leboncoin.scrape_ad(url="https://www.leboncoin.fr/arts_de_la_table/2426724825.htm"))
    output.joinpath("search.json").write_text(json.dumps(ad, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
