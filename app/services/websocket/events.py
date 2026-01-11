"""
WebSocket event types and message schemas.
Defines the structure for real-time communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types for client-server communication."""

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Subscription events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # Data events
    NOTIFICATION = "notification"
    UPDATE = "update"
    MESSAGE = "message"

    # Presence events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    PRESENCE_UPDATE = "presence_update"

    # System events
    PING = "ping"
    PONG = "pong"
    HEARTBEAT = "heartbeat"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""

    type: EventType
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    channel: str | None = None


class SubscribeMessage(BaseModel):
    """Message to subscribe to a channel."""

    type: EventType = EventType.SUBSCRIBE
    channel: str


class UnsubscribeMessage(BaseModel):
    """Message to unsubscribe from a channel."""

    type: EventType = EventType.UNSUBSCRIBE
    channel: str


class NotificationMessage(BaseModel):
    """Notification message sent to clients."""

    type: EventType = EventType.NOTIFICATION
    title: str
    body: str
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UpdateMessage(BaseModel):
    """Data update message for real-time sync."""

    type: EventType = EventType.UPDATE
    resource: str  # e.g., "project", "user"
    action: str  # e.g., "created", "updated", "deleted"
    resource_id: str
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorMessage(BaseModel):
    """Error message sent to clients."""

    type: EventType = EventType.ERROR
    code: str
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PresenceMessage(BaseModel):
    """Presence update message."""

    type: EventType
    user_id: str
    status: str  # e.g., "online", "offline", "away"
    channel: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
