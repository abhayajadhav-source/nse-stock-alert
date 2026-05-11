"""
Stock price analyzer.

Pulls intraday + historical data from Yahoo Finance and computes:
  - Gap %      (today's open vs yesterday's close)
  - Intraday % (current price vs today's open)
  - Volume spike (today's volume vs 20-day average)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import yfinance as yf

from config import (
    GAP_DOWN_THRESHOLD,
    GAP_UP_THRESHOLD,
    INTRADAY_MOVE_THRESHOLD,
    VOLUME_SPIKE_MULTIPLIER,
    YF_RETRIES,
)
from stock_list import get_yf_symbol

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    symbol: str
    current_price: float
    prev_close: float
    day_open: float
    day_high: float
    day_low: float
    volume: int
    avg_volume_20d: float

    gap_pct: float = 0.0
    intraday_pct: float = 0.0
    volume_ratio: float = 0.0

    is_gap_up: bool = False
    is_gap_down: bool = False
    is_breakout_up: bool = False
    is_breakout_down: bool = False
    has_volume_spike: bool = False

    def __post_init__(self):
        if self.prev_close > 0:
            self.gap_pct = ((self.day_open - self.prev_close) / self.prev_close) * 100
        if self.day_open > 0:
            self.intraday_pct = ((self.current_price - self.day_open) / self.day_open) * 100
        if self.avg_volume_20d > 0:
            self.volume_ratio = self.volume / self.avg_volume_20d

        self.is_gap_up        = self.gap_pct >= GAP_UP_THRESHOLD
        self.is_gap_down      = self.gap_pct <= GAP_DOWN_THRESHOLD
        self.is_breakout_up   = self.intraday_pct >= INTRADAY_MOVE_THRESHOLD
        self.is_breakout_down = self.intraday_pct <= -INTRADAY_MOVE_THRESHOLD
        self.has_volume_spike = self.volume_ratio >= VOLUME_SPIKE_MULTIPLIER

    @property
    def is_significant(self) -> bool:
        return any([
            self.is_gap_up, self.is_gap_down,
            self.is_breakout_up, self.is_breakout_down,
            self.has_volume_spike,
        ])

    @property
    def total_pct_change(self) -> float:
        if self.prev_close <= 0:
            return 0.0
        return ((self.current_price - self.prev_close) / self.prev_close) * 100


def fetch_stock_data(symbol: str) -> Optional[StockData]:
    """Fetch and analyze one stock. Returns None on failure."""
    yf_symbol = get_yf_symbol(symbol)
    for attempt in range(YF_RETRIES + 1):
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="21d", interval="1d")
            if hist.empty or len(hist) < 2:
                return None
            today     = hist.iloc[-1]
            yesterday = hist.iloc[-2]
            avg_volume = (hist["Volume"].iloc[-21:-1].mean() if len(hist) >= 21
                          else hist["Volume"].iloc[:-1].mean())
            return StockData(
                symbol=symbol,
                current_price=float(today["Close"]),
                prev_close=float(yesterday["Close"]),
                day_open=float(today["Open"]),
                day_high=float(today["High"]),
                day_low=float(today["Low"]),
                volume=int(today["Volume"]),
                avg_volume_20d=float(avg_volume) if avg_volume else 0.0,
            )
        except Exception as e:
            if attempt < YF_RETRIES:
                time.sleep(1 + attempt)
                continue
            logger.warning("Failed to fetch %s: %s", symbol, e)
            return None
    return None


def get_movement_emoji(data: StockData) -> str:
    if data.is_gap_up or data.is_breakout_up:
        return "🚀"
    if data.is_gap_down or data.is_breakout_down:
        return "📉"
    if data.has_volume_spike:
        return "📊"
    return "➡️"


def get_signal_tags(data: StockData) -> list[str]:
    tags = []
    if data.is_gap_up:        tags.append(f"GAP UP {data.gap_pct:+.2f}%")
    if data.is_gap_down:      tags.append(f"GAP DOWN {data.gap_pct:+.2f}%")
    if data.is_breakout_up:   tags.append(f"BREAKOUT UP {data.intraday_pct:+.2f}%")
    if data.is_breakout_down: tags.append(f"BREAKOUT DOWN {data.intraday_pct:+.2f}%")
    if data.has_volume_spike: tags.append(f"VOL {data.volume_ratio:.1f}x")
    return tags
