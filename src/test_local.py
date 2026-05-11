"""Local test harness — run with: python src/test_local.py"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO)


def test_stock_list():
    print("\n=== TEST 1: Stock list ===")
    from stock_list import get_all_symbols
    symbols = get_all_symbols()
    print(f"✓ Loaded {len(symbols)} stocks")
    print(f"  Sample: {symbols[:5]}")


def test_stock_analyzer():
    print("\n=== TEST 2: Stock analyzer ===")
    from stock_analyzer import fetch_stock_data
    data = fetch_stock_data("RELIANCE")
    if data is None:
        print("✗ Could not fetch (markets closed or yfinance issue)")
        return
    print(f"✓ RELIANCE — price=₹{data.current_price:.2f}, gap={data.gap_pct:.2f}%")


def test_news_fetcher():
    print("\n=== TEST 3: News fetcher ===")
    from news_fetcher import fetch_news_for_stock
    items = fetch_news_for_stock("RELIANCE", max_items=3)
    print(f"✓ Fetched {len(items)} news items")
    for item in items:
        flag = "🔥" if item.is_high_priority else "  "
        print(f"  {flag} {item.title[:80]}")


def test_gmail():
    print("\n=== TEST 4: Gmail ===")
    required = ["GMAIL_SENDER", "GMAIL_APP_PASSWORD", "GMAIL_RECIPIENT"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"✗ Set these env vars to test: {missing}")
        return
    from gmail_notifier import send_test_email
    ok = send_test_email()
    print("✓ Test email sent" if ok else "✗ Send failed")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    test_stock_list()
    test_stock_analyzer()
    test_news_fetcher()
    test_gmail()
    print("\n✓ Done")
