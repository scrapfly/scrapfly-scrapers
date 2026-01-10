# Facebook.com Scraper

This scraper can extract data from Facebook.com including:

- **Marketplace Listings** - product listings with prices, seller info, and locations
- **Events** - event details, dates, locations, and hosts

Based on the guide: [How to Scrape Facebook](https://scrapfly.io/blog/posts/how-to-scrape-facebook)

## Features

- Location-based scraping for Marketplace and Events
- Anti-bot bypass with Scrapfly's ASP
- JavaScript rendering support for dynamic content
- Structured data extraction
- Comprehensive error handling

## Installation

```bash
pip install scrapfly-sdk loguru
```

For testing:
```bash
pip install pytest pytest-asyncio pytest-rerunfailures cerberus
```

## Usage

Set your Scrapfly API key:
```bash
export SCRAPFLY_KEY="your-api-key"
```

Run the scraper:
```bash
python run.py
```

Run tests:
```bash
pytest test.py
```

## Example

```python
import asyncio
import facebook

async def main():
    # Scrape Marketplace listings
    marketplace_data = await facebook.scrape_marketplace_listings(
        location="New York, NY",
        max_items=20
    )
    
    # Scrape Events
    events_data = await facebook.scrape_facebook_events(
        location="New York, NY",
        max_events=20
    )

asyncio.run(main())
```

## Data Structure

### Marketplace Listing
```json
{
  "title": "Product Name",
  "price": "$100",
  "location": "New York, NY",
  "seller": {
    "name": "Seller Name"
  }
}
```

### Event
```json
{
  "title": "Event Name",
  "date": "2026-01-15",
  "location": "New York, NY"
}
```

## Notes

- Facebook requires authentication for most features
- Rate limiting may apply
- This scraper uses public data only
- Respect Facebook's Terms of Service

## Learn More

- [Scrapfly Documentation](https://scrapfly.io/docs)
- [How to Scrape Facebook Guide](https://scrapfly.io/blog/posts/how-to-scrape-facebook)

