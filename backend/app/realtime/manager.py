from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect 

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[UUID, set[WebSocket]] ={} ## um dicionário que mapeia o ID da conversa para um conjunto de WebSockets 

    def add(self, conversation_id: UUID, websocket: WebSocket): ## Adiciona um WebSocket a uma sala de conversa específica, identificada pelo ID
        self.rooms.setdefault(conversation_id, set()).add(websocket)

    def remove(self, conversation_id: UUID, websocket: WebSocket):
        clients = self.rooms.get(conversation_id)
        if clients is None:
            return
        clients.discard(websocket)

        if not clients:
            self.rooms.pop(conversation_id, None)


    def active(self, conversation_id: UUID)-> int:
        return len(self.rooms.get(conversation_id, set()))

    async def broadcast(self, conversation_id: UUID, event: dict): ## Envia um evento para todos os WebSockets conectados a uma sala de conversa específica
        for websocket in tuple(self.rooms.get(conversation_id, set())): ## Cria uma tupla a partir do conjunto de WebSockets para evitar problemas
            try: 
                await websocket.send_json(event) ## Envia o evento como JSON para o WebSocket
            except (WebSocketDisconnect, RuntimeError, OSError): ## Captura exceções que podem ocorrer durante o envio do evento
                self.remove(conversation_id, websocket)


manager = ConnectionManager()
