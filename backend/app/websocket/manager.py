"""
SecureNet Backend — WebSocket Connection Manager

Manages WebSocket connections for real-time security event streaming.
"""

from typing import List, Dict
from fastapi import WebSocket
from datetime import datetime
import json
import asyncio
from app.utils.logger import logger


class ConnectionManager:
    """Manages active WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connections"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast a message to all connections of a specific user"""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, user_id)
    
    async def send_live_score(self, event_data: dict):
        """Send live anomaly score update"""
        message = {
            "type": "live_score",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": event_data
        }
        await self.broadcast(message)
    
    async def send_alert(self, alert_data: dict):
        """Send security alert"""
        message = {
            "type": "alert",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": alert_data
        }
        await self.broadcast(message)
    
    async def send_host_status(self, status_data: dict):
        """Send host status update"""
        message = {
            "type": "host_status",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": status_data
        }
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()
