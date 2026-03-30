"""Background work for Track 2 webhooks (keep HTTP handler fast)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.meetstream_rest import (
    extract_transcript_id,
    fetch_bot_details,
    fetch_transcript,
    meetstream_api_key,
)

logger = logging.getLogger(__name__)


async def process_transcription_event(payload: dict[str, Any]) -> None:
    """
    After ``transcription.*`` webhook: try to load bot metadata and full transcript.

    For ``meeting_captions``-only bots there may be no ``transcript_id``; see MeetStream
    docs for downloading captions from bot detail.
    """
    api_key = meetstream_api_key()
    if not api_key:
        logger.warning(
            "track2: set MEETSTREAM_API_KEY (or MEET_STREAM_API_KEY) to fetch transcripts",
        )
        return

    bot_id = payload.get("bot_id")
    if not bot_id:
        logger.warning("track2: transcription webhook missing bot_id")
        return

    event = payload.get("event")
    try:
        bot_details = await fetch_bot_details(api_key, str(bot_id))
    except httpx.HTTPError as exc:
        logger.exception("track2: fetch_bot_details failed bot_id=%s: %s", bot_id, exc)
        return

    transcript_id = extract_transcript_id(payload, bot_details)
    if not transcript_id:
        logger.info(
            "track2: no transcript_id for bot_id=%s event=%s — "
            "if you use deepgram/assemblyai/jigsawstack, ensure create_bot returned "
            "transcript_id or it appears in bot detail; meeting_captions uses caption_file",
            bot_id,
            event,
        )
        return

    try:
        transcript = await fetch_transcript(api_key, transcript_id, raw=False)
    except httpx.HTTPError as exc:
        logger.exception(
            "track2: get_transcript failed bot_id=%s transcript_id=%s: %s",
            bot_id,
            transcript_id,
            exc,
        )
        return

    preview = transcript
    if isinstance(transcript, (dict, list)):
        preview = json.dumps(transcript, indent=2, ensure_ascii=False)
    if isinstance(preview, str) and len(preview) > 4000:
        preview = preview[:4000] + "\n… [truncated log]"

    logger.info(
        "track2: transcript fetched bot_id=%s transcript_id=%s chars=%s",
        bot_id,
        transcript_id,
        len(preview) if isinstance(preview, str) else "json",
    )
    logger.debug("track2: transcript preview:\n%s", preview)
