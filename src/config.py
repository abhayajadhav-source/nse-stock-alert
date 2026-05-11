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
GMAIL_SENDER       = os.getenv("GMAIL_SENDER", "")        # your_account@gmail.com
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")  # 16-char app password (no spaces)
GMAIL_RECIPIENT    = os.getenv("GMAIL_RECIPIENT", "")     # where alerts get delivered

# ---------------------------------------------------------------------------
# MARKET HOURS (Indian Standard Time)
# ---------------------------------------------------------------------------
IST = ZoneInfo("Asia/Kolkata")

# Pre-market: 09:00 IST (catches gap-up/down candidates before open)
# Regular   : 09:15 - 15:30 IST
SCAN_START_TIME = dtime(9, 0)
SCAN_END_TIME   = dtime(15, 45)

# ---------------------------------------------------------------------------
# GAP DETECTION THRESHOLDS
# ---------------------------------------------------------------------------
GAP_UP_THRESHOLD   = 2.0    # >= +2.0%
GAP_DOWN_THRESHOLD = -2.0   # <= -2.0%

INTRADAY_MOVE_THRESHOLD = 3.0   # +/- 3.0% from day open
VOLUME_SPIKE_MULTIPLIER = 2.0   # 2x average daily volume

# ---------------------------------------------------------------------------
# NEWS FILTER
# ---------------------------------------------------------------------------
NEWS_LOOKBACK_HOURS = 24

HIGH_PRIORITY_KEYWORDS = [
    # corporate actions
    "buyback", "bonus", "split", "dividend", "rights issue",
    # results & guidance
    "results", "profit", "loss", "revenue", "earnings", "guidance",
    "beats estimates", "misses estimates",
    # deals & corporate events
    "acquisition", "acquires", "merger", "demerger", "stake", "deal",
    "partnership", "joint venture", "JV",
    # regulatory & legal
    "SEBI", "RBI", "investigation", "raid", "fraud", "ban", "penalty",
    "approval", "license", "tender", "order win", "contract",
    # ratings & price action
    "upgrade", "downgrade", "target price", "rating", "broker",
    "block deal", "bulk deal", "promoter",
    # operational
    "production", "expansion", "capex", "shutdown", "strike",
    # management
    "CEO", "MD", "resigns", "appointed", "appoints",
]

# ---------------------------------------------------------------------------
# SCANNING BEHAVIOUR
# ---------------------------------------------------------------------------
SCAN_INTERVAL_SECONDS  = 300     # 5 min between cycles
ALERT_COOLDOWN_SECONDS = 3600    # 1 hour cooldown per (stock, signal)
STATE_FILE             = "data/alert_state.json"
YF_RETRIES             = 2
MAX_ALERTS_PER_CYCLE   = 15

# ---------------------------------------------------------------------------
# EMAIL BEHAVIOUR
# ---------------------------------------------------------------------------
# Gmail edition sends ONE consolidated email per scan cycle instead of
# one email per alert. This avoids spamming your inbox and keeps Gmail's
# sending limits comfortable (500/day free, but we'll use ~80/day max).
EMAIL_BATCH_MODE = True

# Subject prefix — helps you create a Gmail filter to auto-route alerts
EMAIL_SUBJECT_PREFIX = "[NSE Alert]"
