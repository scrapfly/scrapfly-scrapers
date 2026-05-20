# Perplexity.ai Scraper

This scraper uses [scrapfly.io](https://scrapfly.io/) and Python to scrape data from perplexity.ai.

## What it scrapes
- Answer pages: query, answer markdown, cited domains, source count, follow-up suggestions

## Fair Use Disclaimer

This code is provided for educational purposes only. Review perplexity.ai's Terms of Service before scraping.

## Setup and Use

0. Requires Python 3.10+ and [Poetry](https://python-poetry.org/docs/#installation).
1. Get a Scrapfly API key from https://scrapfly.io/dashboard and export it:
   ```shell
   export SCRAPFLY_KEY="YOUR KEY"
   ```
2. Install:
   ```shell
   cd perplexity-scraper
   poetry install --no-root
   ```
3. Run example:
   ```shell
   poetry run python run.py
   ```
4. Run tests:
   ```shell
   poetry install
   poetry run pytest test.py
   poetry run pytest test.py -k test_scrape_answer 
   ```
