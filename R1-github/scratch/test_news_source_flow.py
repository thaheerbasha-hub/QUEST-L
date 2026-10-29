import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json

import news_sentiment

archive = news_sentiment.get_archived_articles()
print(f"Total tickers in archive: {len(archive)}")

sample_items = []
for ticker, arts in list(archive.items())[:3]:
    for a in arts[:2]:
        sample_items.append((ticker, a))

for ticker, a in sample_items:
    print(f"Ticker: {ticker}")
    print(f"  Title: {a.get('title')[:60]}...")
    print(f"  URL: {a.get('url') or a.get('link')}")
    print(f"  Provider field present: {'provider' in a}")
    print(f"  Keys available: {list(a.keys())}")
    print()
