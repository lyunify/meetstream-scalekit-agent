"""
MeetStream **REST** API (HTTP) for Track 2 — fetch bot details and post-call transcripts.

Separate from ``app/meetstream/`` (WebSocket / bridge). Docs:
https://docs.meetstream.ai/guides/get-started/create-bot-with-post-call-transcription
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = os.getenv("MEETSTREAM_API_BASE", "https://api.meetstream.ai/api/v1")


def meetstream_api_key() -> str:
    """Prefer MEETSTREAM_API_KEY; fall back to MEET_STREAM_API_KEY (scalekit-meetstream style)."""
    return (os.getenv("MEETSTREAM_API_KEY") or os.getenv("MEET_STREAM_API_KEY") or "").strip()


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Token {api_key}"}


def extract_transcript_id(
    webhook_payload: dict[str, Any],
    bot_details: dict[str, Any] | None,
) -> str | None:
    """Resolve transcript id from webhook or nested bot detail fields."""
    tid = webhook_payload.get("transcript_id")
    if tid:
        return str(tid)
    if not bot_details:
        return None
    return _deep_find_transcript_id(bot_details)


def _deep_find_transcript_id(obj: Any, depth: int = 0) -> str | None:
    if obj is None or depth > 14:
        return None
    if isinstance(obj, dict):
        for key, val in obj.items():
            key_l = key.lower() if isinstance(key, str) else ""
            if key_l in ("transcript_id", "transcriptid") and val is not None and str(val).strip():
                return str(val).strip()
            found = _deep_find_transcript_id(val, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_transcript_id(item, depth + 1)
            if found:
                return found
    return None


async def fetch_bot_details(api_key: str, bot_id: str) -> dict[str, Any]:
    url = f"{API_BASE.rstrip('/')}/bots/{bot_id}/detail"
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.get(url, headers=_auth_headers(api_key))
        response.raise_for_status()
        data = response.json()
        return data.get("bot_details") or data.get("bot_detail") or {}


async def fetch_transcript(
    api_key: str,
    transcript_id: str,
    *,
    raw: bool = False,
) -> Any:
    url = f"{API_BASE.rstrip('/')}/transcript/{transcript_id}/get_transcript"
    params = {"raw": "True"} if raw else {}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            url,
            headers=_auth_headers(api_key),
            params=params,
        )
        response.raise_for_status()
        ct = (response.headers.get("content-type") or "").lower()
        if "application/json" in ct:
            return response.json()
        return response.text
