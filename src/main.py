"""
Main scanner — orchestrates the full pipeline (Gmail edition).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from typing import List, Tuple

from config import (
    EMAIL_BATCH_MODE,
    IST,
    MAX_ALERTS_PER_CYCLE,
    SCAN_END_TIME,
    SCAN_START_TIME,
)
from gmail_notifier import send_batch_alert, send_single_alert
from news_fetcher import NewsItem, fetch_news_for_stock
from state_manager import cleanup_old_entries, mark_alert_sent, should_send_alert
from stock_analyzer import StockData, fetch_stock_data
from stock_list import get_all_symbols

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """True if currently a weekday and within IST scan window."""
    now = datetime.now(IST)
    if now.weekday() >= 5:   # 5=Sat, 6=Sun
        return False
    return SCAN_START_TIME <= now.time() <= SCAN_END_TIME


def get_primary_signal(data: StockData) -> str:
    if data.is_gap_up:        return "gap_up"
    if data.is_gap_down:      return "gap_down"
    if data.is_breakout_up:   return "breakout_up"
    if data.is_breakout_down: return "breakout_down"
    if data.has_volume_spike: return "volume_spike"
    return "none"


def filter_significant_stocks(symbols: List[str]) -> List[StockData]:
    """Stage 1 — price/volume filter, returns only significant stocks."""
    significant = []
    total       = len(symbols)
    for i, symbol in enumerate(symbols, 1):
        if i % 25 == 0:
            logger.info("Progress: %d/%d", i, total)
        data = fetch_stock_data(symbol)
        if data is None:
            continue
        if data.is_significant:
            significant.append(data)
            logger.info("✓ %s — gap=%.2f%% intraday=%.2f%% vol=%.1fx",
                        symbol, data.gap_pct, data.intraday_pct, data.volume_ratio)
    return significant


def rank_alerts(stocks: List[StockData]) -> List[StockData]:
    """Most actionable first: gap moves weighted heaviest."""
    def score(s: StockData) -> float:
        return (
            abs(s.gap_pct)      * 2.0 +
            abs(s.intraday_pct) * 1.5 +
            (s.volume_ratio if s.volume_ratio > 1 else 0) * 0.5
        )
    return sorted(stocks, key=score, reverse=True)


def run_scan_cycle() -> dict:
    """Execute one full scan; return summary stats."""
    logger.info("=" * 60)
    logger.info("Starting scan at %s IST", datetime.now(IST).strftime("%H:%M:%S"))
    logger.info("=" * 60)

    symbols = get_all_symbols()
    logger.info("Universe: %d stocks", len(symbols))

    significant = filter_significant_stocks(symbols)
    logger.info("Significant stocks: %d", len(significant))

    ranked   = rank_alerts(significant)
    to_alert = ranked[:MAX_ALERTS_PER_CYCLE]

    # Apply cooldown filter — collect only stocks not on cooldown
    alerts_to_send: List[Tuple[StockData, List[NewsItem]]] = []
    for stock in to_alert:
        signal = get_primary_signal(stock)
        if not should_send_alert(stock.symbol, signal):
            logger.info("⏭  %s — cooldown active", stock.symbol)
            continue
        news_items = fetch_news_for_stock(stock.symbol)
        alerts_to_send.append((stock, news_items))

    # Send: batch mode = 1 email total; single mode = 1 email per stock
    sent = 0
    if alerts_to_send:
        if EMAIL_BATCH_MODE:
            if send_batch_alert(alerts_to_send):
                for stock, _ in alerts_to_send:
                    mark_alert_sent(stock.symbol, get_primary_signal(stock))
                sent = len(alerts_to_send)
                logger.info("📤 Sent batch email with %d alerts", sent)
            else:
                logger.error("✗ Batch email failed")
        else:
            for stock, news in alerts_to_send:
                if send_single_alert(stock, news):
                    mark_alert_sent(stock.symbol, get_primary_signal(stock))
                    sent += 1
                    logger.info("📤 Sent: %s", stock.symbol)
                else:
                    logger.error("✗ Failed: %s", stock.symbol)

    cleanup_old_entries()

    return {
        "total_scanned": len(symbols),
        "significant":   len(significant),
        "alerts_sent":   sent,
        "gap_ups":       sum(1 for s, _ in alerts_to_send if s.is_gap_up),
        "gap_downs":     sum(1 for s, _ in alerts_to_send if s.is_gap_down),
        "with_news":     sum(1 for _, n in alerts_to_send if n),
    }


def run_once() -> int:
    if not is_market_hours():
        logger.info("Outside market hours — skipping scan")
        return 0
    try:
        stats = run_scan_cycle()
        logger.info("Scan complete: %s", stats)
        return 0
    except Exception as e:
        logger.exception("Scan failed: %s", e)
        return 1


def main():
    parser = argparse.ArgumentParser(description="NSE Stock News Alert Scanner")
    parser.add_argument("--force", action="store_true",
                        help="Run even outside market hours (for testing)")
    parser.add_argument("--test-email", action="store_true",
                        help="Send a test email and exit")
    args = parser.parse_args()

    if args.test_email:
        from gmail_notifier import send_test_email
        ok = send_test_email()
        print("✓ Test email sent" if ok else "✗ Test email failed")
        return 0 if ok else 1

    if args.force:
        try:
            stats = run_scan_cycle()
            logger.info("Forced scan complete: %s", stats)
            return 0
        except Exception as e:
            logger.exception("Forced scan failed: %s", e)
            return 1

    return run_once()


if __name__ == "__main__":
    sys.exit(main())
