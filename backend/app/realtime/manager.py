from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        # Conversa -> conexao -> usuario
        self.rooms: dict[
            UUID, dict[WebSocket, UUID | None]
        ] = {}

        # Somente clientes que solicitaram presença.
        self.subscribers: dict[
            UUID, set[WebSocket]
        ] = {}

    def add(
        self,
        conversation_id: UUID,
        websocket: WebSocket,
        user_id: UUID | None = None,
    ) -> bool:
        room = self.rooms.setdefault(
            conversation_id, {}
        )

        if websocket in room:
            return False

        was_online = (
            user_id is not None
            and user_id in room.values()
        )

        room[websocket] = user_id

        # True somente na primeira conexao do usuario.
        return user_id is not None and not was_online

    def remove(
        self,
        conversation_id: UUID,
        websocket: WebSocket,
    ) -> tuple[UUID | None, bool]:
        room = self.rooms.get(conversation_id)

        if room is None or websocket not in room:
            return None, False

        user_id = room.pop(websocket)

        subscribers = self.subscribers.get(
            conversation_id
        )

        if subscribers is not None:
            subscribers.discard(websocket)

            if not subscribers:
                self.subscribers.pop(
                    conversation_id, None
                )

        became_offline = (
            user_id is not None
            and user_id not in room.values()
        )

        if not room:
            self.rooms.pop(conversation_id, None)

        return user_id, became_offline

    def active(self, conversation_id: UUID) -> int:
        return len(
            self.rooms.get(conversation_id, {})
        )

    def is_online(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> bool:
        return user_id in self.rooms.get(
            conversation_id, {}
        ).values()

    def online_users(
        self,
        conversation_id: UUID,
    ) -> list[str]:
        users = {
            str(user_id)
            for user_id in self.rooms.get(
                conversation_id, {}
            ).values()
            if user_id is not None
        }

        return sorted(users)

    def subscribe(
        self,
        conversation_id: UUID,
        websocket: WebSocket,
    ) -> None:
        room = self.rooms.get(
            conversation_id, {}
        )

        if room.get(websocket) is None:
            raise ValueError(
                "Conexao nao autenticada"
            )

        self.subscribers.setdefault(
            conversation_id, set()
        ).add(websocket)

    async def _deliver(
        self,
        conversation_id: UUID,
        sockets,
        event: dict,
    ) -> None:
        offline_users = set()

        for websocket in tuple(sockets):
            try:
                await websocket.send_json(event)

            except (
                WebSocketDisconnect,
                RuntimeError,
                OSError,
            ):
                user_id, became_offline = self.remove(
                    conversation_id,
                    websocket,
                )

                if became_offline:
                    offline_users.add(user_id)

        for user_id in offline_users:
            await self.notify_presence(
                conversation_id,
                user_id,
                False,
            )

    async def broadcast(
        self,
        conversation_id: UUID,
        event: dict,
    ) -> None:
        await self._deliver(
            conversation_id,
            self.rooms.get(conversation_id, {}),
            event,
        )

    async def notify_presence(
        self,
        conversation_id: UUID,
        user_id: UUID,
        online: bool,
    ) -> None:
        await self._deliver(
            conversation_id,
            self.subscribers.get(
                conversation_id, set()
            ),
            {
                "type": "presence",
                "user_id": str(user_id),
                "online": online,
            },
        )


manager = ConnectionManager()
