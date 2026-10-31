import asyncio
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.Database.database import SessionLocal
from app.clients.auth_service import AuthServiceClient
from app.models.conversation import Conversation
from app.models.message import Message
from app.realtime.manager import manager
from app.routers.messages import MessageCreate, MessagePublic
from app.services.profiles import ensure_profile


router = APIRouter(tags=["WebSocket"])


def check_ws_access(token: str, conversation_id: UUID) -> UUID:
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

        identity = auth.call(
            "GET",
            "/auth/me",
            token=token,
        )

    with SessionLocal() as db:
        user = ensure_profile(db, identity)
        conversation = db.get(Conversation, conversation_id)

        if (
            conversation is None
            or user.id not in (
                conversation.user_a_id,
                conversation.user_b_id,
            )
        ):
            raise HTTPException(
                status_code=404,
                detail="Conversa nao encontrada",
            )

        return user.id


def persist_ws_message(
    conversation_id: UUID,
    sender_id: UUID,
    body: str,
) -> dict:
    with SessionLocal() as db:
        try:
            conversation = db.get(
                Conversation,
                conversation_id,
            )

            if (
                conversation is None
                or sender_id not in (
                    conversation.user_a_id,
                    conversation.user_b_id,
                )
            ):
                raise HTTPException(
                    status_code=404,
                    detail="Conversa nao encontrada",
                )

            message = Message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                body=body,
            )

            db.add(message)
            db.commit()
            db.refresh(message)

            return MessagePublic.model_validate(
                message
            ).model_dump(mode="json")

        except HTTPException:
            raise

        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Nao foi possivel salvar a mensagem",
            ) from exc


@router.websocket("/api/v1/conversations/{conversation_id}/ws")
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
):
    await websocket.accept()
    registered = False

    try:
        try:
            first = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10,
            )
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return

        if not isinstance(first, dict):
            await websocket.close(code=1008)
            return

        token = first.get("token")

        if (
            first.get("type") != "auth"
            or not isinstance(token, str)
            or not 0 < len(token) <= 4096
        ):
            await websocket.close(code=1008)
            return

        try:
            user_id = await run_in_threadpool(
                check_ws_access,
                token,
                conversation_id,
            )
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

            if not isinstance(event, dict):
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_event",
                })
                continue

            event_type = event.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if event_type == "send_message":
                try:
                    payload = MessageCreate.model_validate({
                        "body": event.get("body"),
                    })
                except ValidationError:
                    await websocket.send_json({
                        "type": "error",
                        "code": "invalid_message",
                    })
                    continue

                try:
                    saved = await run_in_threadpool(
                        persist_ws_message,
                        conversation_id,
                        user_id,
                        payload.body,
                    )
                except HTTPException as exc:
                    await websocket.send_json({
                        "type": "error",
                        "code": "message_not_saved",
                        "status": exc.status_code,
                    })

                    if exc.status_code in (401, 403, 404):
                        await websocket.close(code=1008)
                        break

                    continue

                await manager.broadcast(
                    conversation_id,
                    {
                        "type": "message",
                        "data": saved,
                    },
                )
                continue

            await websocket.send_json({
                "type": "error",
                "code": "unsupported_event",
            })

    except WebSocketDisconnect:
        pass
    except (ValueError, TypeError):
        await websocket.close(code=1003)
    finally:
        if registered:
            manager.remove(conversation_id, websocket)
