"""
Stock price analyzer.

Pulls daily bars from Yahoo Finance and computes:
  - Gap %         (today's open vs yesterday's close)
  - Intraday %    (current price vs today's open)
  - Volume spike  (today's volume vs 20-day average)
  - 52-week high/low proximity and breakouts
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
    MIN_DAILY_MOVE_FOR_52W,
    NEAR_52W_HIGH_PCT,
    NEAR_52W_LOW_PCT,
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

    # 52-week stats — populated from history
    high_52w: float = 0.0
    low_52w:  float = 0.0

    # Computed in __post_init__
    gap_pct:      float = 0.0
    intraday_pct: float = 0.0
    volume_ratio: float = 0.0
    pct_from_52w_high: float = 0.0   # negative or zero (e.g. -1.5 = 1.5% below)
    pct_from_52w_low:  float = 0.0   # positive or zero (e.g. +1.5 = 1.5% above)

    # Flags
    is_gap_up:           bool = False
    is_gap_down:         bool = False
    is_breakout_up:      bool = False
    is_breakout_down:    bool = False
    has_volume_spike:    bool = False
    is_near_52w_high:    bool = False
    is_near_52w_low:     bool = False
    is_new_52w_high:     bool = False
    is_new_52w_low:      bool = False

    def __post_init__(self):
        # --- Basic price/volume math ---
        if self.prev_close > 0:
            self.gap_pct = ((self.day_open - self.prev_close) / self.prev_close) * 100
        if self.day_open > 0:
            self.intraday_pct = ((self.current_price - self.day_open) / self.day_open) * 100
        if self.avg_volume_20d > 0:
            self.volume_ratio = self.volume / self.avg_volume_20d

        # --- 52-week proximity ---
        # pct_from_52w_high is <= 0 when price is below the high.
        # pct_from_52w_low  is >= 0 when price is above the low.
        if self.high_52w > 0:
            self.pct_from_52w_high = ((self.current_price - self.high_52w) / self.high_52w) * 100
        if self.low_52w > 0:
            self.pct_from_52w_low  = ((self.current_price - self.low_52w)  / self.low_52w)  * 100

        # --- Standard flags ---
        self.is_gap_up        = self.gap_pct >= GAP_UP_THRESHOLD
        self.is_gap_down      = self.gap_pct <= GAP_DOWN_THRESHOLD
        self.is_breakout_up   = self.intraday_pct >= INTRADAY_MOVE_THRESHOLD
        self.is_breakout_down = self.intraday_pct <= -INTRADAY_MOVE_THRESHOLD
        self.has_volume_spike = self.volume_ratio >= VOLUME_SPIKE_MULTIPLIER

        # --- 52-week flags ---
        # Apply the daily-move filter so we don't alert on a stock that's
        # *near* its high but isn't actually moving today.
        daily_move = abs(self.total_pct_change)
        meets_daily_move = daily_move >= MIN_DAILY_MOVE_FOR_52W

        if self.high_52w > 0:
            # "New" high: today's high meets/exceeds 52w high
            self.is_new_52w_high = self.day_high >= self.high_52w
            # "Near" high: within X% of 52w high AND meaningful daily move
            within_high_band = self.pct_from_52w_high >= -NEAR_52W_HIGH_PCT
            self.is_near_52w_high = (
                within_high_band and meets_daily_move and not self.is_new_52w_high
            )

        if self.low_52w > 0:
            self.is_new_52w_low = self.day_low <= self.low_52w
            within_low_band = self.pct_from_52w_low <= NEAR_52W_LOW_PCT
            self.is_near_52w_low = (
                within_low_band and meets_daily_move and not self.is_new_52w_low
            )

    @property
    def is_significant(self) -> bool:
        """Stock has at least one notable signal."""
        return any([
            self.is_gap_up, self.is_gap_down,
            self.is_breakout_up, self.is_breakout_down,
            self.has_volume_spike,
            self.is_near_52w_high, self.is_near_52w_low,
            self.is_new_52w_high, self.is_new_52w_low,
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

            # 1 year of daily bars — enough for 52-week high/low + 20-day avg vol.
            # "1y" gives ~252 trading days which is exactly what we want.
            hist = ticker.history(period="1y", interval="1d")
            if hist.empty or len(hist) < 2:
                return None

            today     = hist.iloc[-1]
            yesterday = hist.iloc[-2]

            # 20-day avg volume, excluding today
            if len(hist) >= 21:
                avg_volume = hist["Volume"].iloc[-21:-1].mean()
            else:
                avg_volume = hist["Volume"].iloc[:-1].mean()

            # 52-week high/low — use the full history excluding today's bar
            # so a fresh intraday high properly registers as a "new" high.
            hist_excl_today = hist.iloc[:-1]
            high_52w = float(hist_excl_today["High"].max()) if not hist_excl_today.empty else 0.0
            low_52w  = float(hist_excl_today["Low"].min())  if not hist_excl_today.empty else 0.0

            return StockData(
                symbol=symbol,
                current_price=float(today["Close"]),
                prev_close=float(yesterday["Close"]),
                day_open=float(today["Open"]),
                day_high=float(today["High"]),
                day_low=float(today["Low"]),
                volume=int(today["Volume"]),
                avg_volume_20d=float(avg_volume) if avg_volume else 0.0,
                high_52w=high_52w,
                low_52w=low_52w,
            )
        except Exception as e:
            if attempt < YF_RETRIES:
                time.sleep(1 + attempt)
                continue
            logger.warning("Failed to fetch %s: %s", symbol, e)
            return None
    return None


def get_movement_emoji(data: StockData) -> str:
    """Pick an emoji that best summarizes the strongest signal."""
    # New 52-week highs/lows trump everything else — they're the strongest signal.
    if data.is_new_52w_high:                                      return "🏆"
    if data.is_new_52w_low:                                       return "⚠️"
    if data.is_gap_up or data.is_breakout_up:                     return "🚀"
    if data.is_gap_down or data.is_breakout_down:                 return "📉"
    if data.is_near_52w_high:                                     return "📈"
    if data.is_near_52w_low:                                      return "📊"
    if data.has_volume_spike:                                     return "🔊"
    return "➡️"


def get_signal_tags(data: StockData) -> list[str]:
    """Compact tags describing what triggered the alert."""
    tags = []
    # 52-week signals first — they're the most actionable
    if data.is_new_52w_high:  tags.append(f"NEW 52W HIGH ₹{data.high_52w:.2f}")
    if data.is_new_52w_low:   tags.append(f"NEW 52W LOW ₹{data.low_52w:.2f}")
    if data.is_near_52w_high: tags.append(f"NEAR 52W HIGH ({data.pct_from_52w_high:+.2f}%)")
    if data.is_near_52w_low:  tags.append(f"NEAR 52W LOW ({data.pct_from_52w_low:+.2f}%)")
    # Then the standard signals
    if data.is_gap_up:        tags.append(f"GAP UP {data.gap_pct:+.2f}%")
    if data.is_gap_down:      tags.append(f"GAP DOWN {data.gap_pct:+.2f}%")
    if data.is_breakout_up:   tags.append(f"BREAKOUT UP {data.intraday_pct:+.2f}%")
    if data.is_breakout_down: tags.append(f"BREAKOUT DOWN {data.intraday_pct:+.2f}%")
    if data.has_volume_spike: tags.append(f"VOL {data.volume_ratio:.1f}x")
    return tags
