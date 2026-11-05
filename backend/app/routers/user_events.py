import asyncio
import os

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.clients.auth_service import AuthServiceClient
from app.Database.database import SessionLocal
from app.realtime.manager import manager
from app.services.profiles import ensure_profile

router = APIRouter(tags=["User events"])


def check_user_event_access(token: str):
    base_url = os.getenv(
        "AUTH_SERVICE_URL",
        "http://host.docker.internal:8001",
    )
    with httpx.Client(
        base_url=base_url,
        timeout=5.0,
        trust_env=False,
    ) as client:
        auth = AuthServiceClient(client)
        identity = auth.call("GET", "/auth/me", token=token)

    with SessionLocal() as db:
        return ensure_profile(db, identity).id


@router.websocket("/api/v1/events/ws")
async def user_events_websocket(websocket: WebSocket):
    await websocket.accept()
    user_id = None

    try:
        try:
            first = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10,
            )
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return

        token = first.get("token") if isinstance(first, dict) else None
        if (
            not isinstance(first, dict)
            or first.get("type") != "auth"
            or not isinstance(token, str)
            or not 0 < len(token) <= 4096
        ):
            await websocket.close(code=1008)
            return

        try:
            user_id = await run_in_threadpool(
                check_user_event_access,
                token,
            )
        except HTTPException as exc:
            code = 1013 if exc.status_code >= 500 else 1008
            await websocket.close(code=code)
            return

        manager.add_user(user_id, websocket)
        await websocket.send_json({"type": "ready", "user_id": str(user_id)})

        while True:
            event = await websocket.receive_json()
            if not isinstance(event, dict):
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_event",
                })
            elif event.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({
                    "type": "error",
                    "code": "unsupported_event",
                })
    except WebSocketDisconnect:
        pass
    except (ValueError, TypeError):
        await websocket.close(code=1003)
    finally:
        if user_id is not None:
            manager.remove_user(user_id, websocket)
