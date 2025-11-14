import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from models import WebSocketMessage, EstimationResult


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            self.active_connections[session_id].add(websocket)
    
    async def disconnect(self, session_id: str, websocket: WebSocket):
        async with self.lock:
            if session_id in self.active_connections:
                self.active_connections[session_id].discard(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
    
    async def broadcast(self, session_id: str, results: list[EstimationResult]):
        message = WebSocketMessage(session_id=session_id, results=results)
        message_json = message.model_dump_json()
        
        async with self.lock:
            if session_id in self.active_connections:
                disconnected = set()
                for connection in self.active_connections[session_id]:
                    try:
                        await connection.send_text(message_json)
                    except Exception:
                        disconnected.add(connection)
                
                for conn in disconnected:
                    self.active_connections[session_id].discard(conn)


ws_manager = WebSocketManager()

