import asyncio
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.Database.database import SessionLocal
from app.clients.auth_service import AuthServiceClient
from app.models.conversation import Conversation
from app.realtime.manager import manager
from app.services.profiles import ensure_profile

router = APIRouter(tags=["WebSocket"])


def check_ws_access(token: str, conversation_id: UUID)-> UUID:
    base_url = os.getenv(
        "AUTH_SERVICE_URL",
        "http://host.docker.internal:8000",
    )
    with httpx.Client(
        base_url=base_url,
        timeout=5.0,
        trust_env=False,
    ) as client:
        auth = AuthServiceClient(client)
        identity = auth.call(
            "GET",
            "/auth/me",
            token= token,
        )

    with SessionLocal() as db:
        user = ensure_profile(db, identity)
        conversation = db.get(Conversation, conversation_id)

        if (conversation is None or user.id not in(conversation.user_a_id, conversation.user_b_id)):
            raise HTTPException(
                status_code=404,
                detail="Conversa nao encontrada",
            )
        return user.id


@router.websocket(
    "/api/v1/conversations/{conversation_id}/ws",
)
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: UUID,

):
    await websocket.accept()
    registered = False
    try:
        try:
            first = await asyncio.wait_for(websocket.receive_json(), timeout=10,)
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return
        if not isinstance(first, dict):
            await websocket.close(code=1008)
            return

        token = first.get("token")

        if (first.get("type") != "auth" or not isinstance(token, str) or not 0 < len(token) <= 4096):
            await websocket.close(code=1008)
            return
        try:
            user_id = await run_in_threadpool(check_ws_access, token, conversation_id)
        except HTTPException as exc:
            code = 1013 if exc.status_code >= 500 else 1008
            await websocket.close(code=code)
            return
        manager.add(conversation_id, websocket)
        registered = True
        await websocket.send_json({
            "type": "ready",
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
        }) 
        while True:
            event = await websocket.receive_json()
            if isinstance(event, dict) and event.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({
                    "type": "error",
                    "detail": "Evento ainda nao suportado",
                })
    except WebSocketDisconnect:
        pass
    except (ValueError, TypeError):
        await websocket.close(code=1000)
    finally:
        if registered:
            manager.remove(conversation_id, websocket)