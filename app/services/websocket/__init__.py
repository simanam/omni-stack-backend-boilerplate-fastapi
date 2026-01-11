"""
WebSocket service module.
Provides real-time communication with Redis pub/sub support for scaling.
"""

from app.services.websocket.events import (
    ErrorMessage,
    EventType,
    NotificationMessage,
    PresenceMessage,
    SubscribeMessage,
    UnsubscribeMessage,
    UpdateMessage,
    WebSocketMessage,
)
from app.services.websocket.manager import (
    Connection,
    ConnectionManager,
    connection_manager,
    get_connection_manager,
)

__all__ = [
    # Manager
    "ConnectionManager",
    "Connection",
    "connection_manager",
    "get_connection_manager",
    # Events
    "EventType",
    "WebSocketMessage",
    "SubscribeMessage",
    "UnsubscribeMessage",
    "NotificationMessage",
    "UpdateMessage",
    "ErrorMessage",
    "PresenceMessage",
]
