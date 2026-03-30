"""
Track 2 — MeetStream callback webhook (HTTP).

MeetStream sends POST requests to your public URL when bot lifecycle or transcript
events happen. This module receives them so you can log, then later: fetch the
transcript, call an LLM, and trigger Scalekit actions.

Docs: https://docs.meetstream.ai/guides/get-started/webhooks-and-events
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app.routes.track2_tasks import process_transcription_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["track2"])


@router.get("/webhooks/meetstream")
async def meetstream_webhook_probe() -> dict[str, Any]:
    """
    Lets you open the URL in a browser to confirm ngrok + routing work.
    MeetStream itself always uses POST with a JSON body.
    """
    return {
        "ok": True,
        "message": "Webhook path is live. Use POST for real MeetStream events.",
        "hint": 'create_bot callback_url should end with /webhooks/meetstream — e.g. https://YOUR-NGROKOK/webhooks/meetstream',
    }


@router.post("/webhooks/meetstream")
async def meetstream_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Track 2 entry: log payload, return 200 quickly.

    On ``transcription.*`` events, a background task fetches bot detail + transcript
    when ``MEETSTREAM_API_KEY`` is set (see ``app/meetstream_rest.py``).
    """
    raw = await request.body()
    if not raw:
        logger.info("meetstream_webhook: empty body")
        return JSONResponse({"received": True, "note": "empty body"}, status_code=200)

    try:
        payload: Any = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("meetstream_webhook: non-json body, first_200=%r", raw[:200])
        return JSONResponse(
            {"received": True, "note": "body was not JSON"},
            status_code=200,
        )

    event = payload.get("event") if isinstance(payload, dict) else None
    bot_id = payload.get("bot_id") if isinstance(payload, dict) else None
    logger.info(
        "meetstream_webhook: event=%s bot_id=%s keys=%s",
        event,
        bot_id,
        list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
    )
    logger.debug("meetstream_webhook: full_payload=%s", payload)

    if (
        isinstance(payload, dict)
        and isinstance(event, str)
        and event.startswith("transcription.")
    ):
        background_tasks.add_task(process_transcription_event, payload)

    return JSONResponse({"received": True, "event": event, "bot_id": bot_id}, status_code=200)
