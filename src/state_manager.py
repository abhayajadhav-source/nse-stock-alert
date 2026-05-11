"""
Alert-state persistence — tracks already-sent alerts so we don't
spam the same alert every 5 minutes.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Dict

from config import ALERT_COOLDOWN_SECONDS, STATE_FILE

logger = logging.getLogger(__name__)


def _load_state() -> Dict[str, float]:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("State file corrupt, resetting: %s", e)
        return {}


def _save_state(state: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        logger.error("Failed to save state: %s", e)


def _make_key(symbol: str, signal_type: str) -> str:
    return f"{symbol}:{signal_type}"


def should_send_alert(symbol: str, signal_type: str) -> bool:
    """True if we should alert — False if same signal sent within cooldown."""
    state = _load_state()
    last  = state.get(_make_key(symbol, signal_type))
    if last is None:
        return True
    return (datetime.now().timestamp() - last) >= ALERT_COOLDOWN_SECONDS


def mark_alert_sent(symbol: str, signal_type: str) -> None:
    state = _load_state()
    state[_make_key(symbol, signal_type)] = datetime.now().timestamp()
    _save_state(state)


def cleanup_old_entries(max_age_seconds: int = 86400) -> None:
    """Drop entries older than max_age_seconds (default 1 day)."""
    state = _load_state()
    now   = datetime.now().timestamp()
    fresh = {k: v for k, v in state.items() if (now - v) < max_age_seconds}
    if len(fresh) < len(state):
        _save_state(fresh)
