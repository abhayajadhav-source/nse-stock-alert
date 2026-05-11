"""
Configuration for the NSE Stock News Alert System (Gmail edition).
All thresholds and runtime parameters live here so you can tune
behaviour without touching the rest of the codebase.
"""

import os
from datetime import time as dtime
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# SECRETS — loaded from environment / GitHub Actions secrets
# ---------------------------------------------------------------------------
GMAIL_SENDER       = os.getenv("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_RECIPIENT    = os.getenv("GMAIL_RECIPIENT", "")

# ---------------------------------------------------------------------------
# MARKET HOURS (Indian Standard Time)
# ---------------------------------------------------------------------------
IST = ZoneInfo("Asia/Kolkata")
SCAN_START_TIME = dtime(9, 0)
SCAN_END_TIME   = dtime(15, 45)

# ---------------------------------------------------------------------------
# GAP DETECTION THRESHOLDS
# ---------------------------------------------------------------------------
GAP_UP_THRESHOLD   = 2.0
GAP_DOWN_THRESHOLD = -2.0

INTRADAY_MOVE_THRESHOLD = 3.0
VOLUME_SPIKE_MULTIPLIER = 2.0

# ---------------------------------------------------------------------------
# 52-WEEK HIGH/LOW DETECTION
# ---------------------------------------------------------------------------
# "Near 52w high" = within this % of the 52-week high
# "Near 52w low"  = within this % of the 52-week low
# A "new" 52w high/low is when current price equals or exceeds the prior level.
NEAR_52W_HIGH_PCT = 2.0
NEAR_52W_LOW_PCT  = 2.0

# Only flag 52w-high/low if the price is also meaningfully up/down for the day.
# This filters out stocks that are merely *near* an old high but flat today.
# Set to 0 to disable this filter.
MIN_DAILY_MOVE_FOR_52W = 1.0

# ---------------------------------------------------------------------------
# NEWS FILTER
# ---------------------------------------------------------------------------
NEWS_LOOKBACK_HOURS = 24

HIGH_PRIORITY_KEYWORDS = [
    "buyback", "bonus", "split", "dividend", "rights issue",
    "results", "profit", "loss", "revenue", "earnings", "guidance",
    "beats estimates", "misses estimates",
    "acquisition", "acquires", "merger", "demerger", "stake", "deal",
    "partnership", "joint venture", "JV",
    "SEBI", "RBI", "investigation", "raid", "fraud", "ban", "penalty",
    "approval", "license", "tender", "order win", "contract",
    "upgrade", "downgrade", "target price", "rating", "broker",
    "block deal", "bulk deal", "promoter",
    "production", "expansion", "capex", "shutdown", "strike",
    "CEO", "MD", "resigns", "appointed", "appoints",
    "52-week high", "52 week high", "52-week low", "52 week low",   # NEW
    "all-time high", "record high", "lifetime high",                  # NEW
]

# ---------------------------------------------------------------------------
# SCANNING BEHAVIOUR
# ---------------------------------------------------------------------------
SCAN_INTERVAL_SECONDS  = 300
ALERT_COOLDOWN_SECONDS = 3600
STATE_FILE             = "data/alert_state.json"
YF_RETRIES             = 2
MAX_ALERTS_PER_CYCLE   = 15

# ---------------------------------------------------------------------------
# EMAIL BEHAVIOUR
# ---------------------------------------------------------------------------
EMAIL_BATCH_MODE     = True
EMAIL_SUBJECT_PREFIX = "[NSE Alert]"
