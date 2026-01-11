"""
WebSocket connection manager with Redis pub/sub support.
Handles connections, channels, broadcasting, and multi-instance coordination.
"""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.core.cache import get_redis
from app.services.websocket.events import (
    ErrorMessage,
    EventType,
    WebSocketMessage,
)

logger = logging.getLogger(__name__)

# Redis channel prefix for pub/sub
REDIS_CHANNEL_PREFIX = "ws:"
REDIS_PRESENCE_KEY = "ws:presence"


@dataclass
class Connection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    channels: set[str] = field(default_factory=set)


class ConnectionManager:
    """
    Manages WebSocket connections with Redis pub/sub for multi-instance support.

    Features:
    - Track connections by user ID
    - Channel/room subscriptions
    - Broadcast to specific users or channels
    - Redis pub/sub for horizontal scaling
    - Heartbeat/ping-pong handling
    """

    def __init__(self) -> None:
        # Local connection tracking
        self._connections: dict[str, list[Connection]] = {}  # user_id -> connections
        self._channel_subscribers: dict[str, set[str]] = {}  # channel -> user_ids
        self._pubsub_task: asyncio.Task | None = None
        self._running = False

    @property
    def connection_count(self) -> int:
        """Total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def user_count(self) -> int:
        """Number of unique connected users."""
        return len(self._connections)

    async def start(self) -> None:
        """Start the connection manager and Redis pub/sub listener."""
        if self._running:
            return

        self._running = True
        redis = get_redis()
        if redis:
            self._pubsub_task = asyncio.create_task(self._listen_redis_pubsub())
            logger.info("WebSocket manager started with Redis pub/sub")
        else:
            logger.info("WebSocket manager started (single-instance mode)")

    async def stop(self) -> None:
        """Stop the connection manager and cleanup."""
        self._running = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pubsub_task
        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
    ) -> Connection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: Authenticated user ID

        Returns:
            Connection object for the new connection
        """
        await websocket.accept()

        connection = Connection(
            websocket=websocket,
            user_id=user_id,
        )

        # Add to local tracking
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(connection)

        # Update presence in Redis
        await self._update_presence(user_id, online=True)

        # Broadcast user online event
        await self._publish_event(
            EventType.USER_ONLINE,
            {"user_id": user_id},
            channel="presence",
        )

        logger.info(f"WebSocket connected: user={user_id}, total={self.connection_count}")
        return connection

    async def disconnect(self, connection: Connection) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            connection: The connection to remove
        """
        user_id = connection.user_id

        # Remove from local tracking
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c != connection
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

        # Remove from channel subscriptions
        for channel in connection.channels:
            if channel in self._channel_subscribers:
                self._channel_subscribers[channel].discard(user_id)
                if not self._channel_subscribers[channel]:
                    del self._channel_subscribers[channel]

        # Update presence if no more connections for this user
        if user_id not in self._connections:
            await self._update_presence(user_id, online=False)

            # Broadcast user offline event
            await self._publish_event(
                EventType.USER_OFFLINE,
                {"user_id": user_id},
                channel="presence",
            )

        logger.info(f"WebSocket disconnected: user={user_id}, total={self.connection_count}")

    async def subscribe(self, connection: Connection, channel: str) -> None:
        """
        Subscribe a connection to a channel.

        Args:
            connection: The connection to subscribe
            channel: Channel name to subscribe to
        """
        connection.channels.add(channel)

        if channel not in self._channel_subscribers:
            self._channel_subscribers[channel] = set()
        self._channel_subscribers[channel].add(connection.user_id)

        # Send confirmation
        await self.send_to_connection(
            connection,
            WebSocketMessage(
                type=EventType.SUBSCRIBED,
                channel=channel,
                data={"channel": channel},
            ),
        )

        logger.debug(f"User {connection.user_id} subscribed to channel: {channel}")

    async def unsubscribe(self, connection: Connection, channel: str) -> None:
        """
        Unsubscribe a connection from a channel.

        Args:
            connection: The connection to unsubscribe
            channel: Channel name to unsubscribe from
        """
        connection.channels.discard(channel)

        if channel in self._channel_subscribers:
            self._channel_subscribers[channel].discard(connection.user_id)
            if not self._channel_subscribers[channel]:
                del self._channel_subscribers[channel]

        # Send confirmation
        await self.send_to_connection(
            connection,
            WebSocketMessage(
                type=EventType.UNSUBSCRIBED,
                channel=channel,
                data={"channel": channel},
            ),
        )

        logger.debug(f"User {connection.user_id} unsubscribed from channel: {channel}")

    async def send_to_connection(
        self,
        connection: Connection,
        message: WebSocketMessage | dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection: Target connection
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if isinstance(message, WebSocketMessage):
                data = message.model_dump(mode="json")
            else:
                data = message
            await connection.websocket.send_json(data)
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection)
            return False
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            return False

    async def send_to_user(
        self,
        user_id: str,
        message: WebSocketMessage | dict[str, Any],
    ) -> int:
        """
        Send a message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message: Message to send

        Returns:
            Number of successful sends
        """
        # First try local connections
        sent = 0
        if user_id in self._connections:
            for connection in self._connections[user_id]:
                if await self.send_to_connection(connection, message):
                    sent += 1

        # Also publish to Redis for other instances
        await self._publish_to_redis(
            f"user:{user_id}",
            message,
        )

        return sent

    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage | dict[str, Any],
        exclude_user_id: str | None = None,
    ) -> int:
        """
        Broadcast a message to all subscribers of a channel.

        Args:
            channel: Target channel
            message: Message to send
            exclude_user_id: Optional user ID to exclude from broadcast

        Returns:
            Number of successful sends
        """
        sent = 0

        # Send to local subscribers
        if channel in self._channel_subscribers:
            for user_id in self._channel_subscribers[channel]:
                if user_id == exclude_user_id:
                    continue
                if user_id in self._connections:
                    for connection in self._connections[user_id]:
                        if await self.send_to_connection(connection, message):
                            sent += 1

        # Publish to Redis for other instances
        await self._publish_to_redis(
            f"channel:{channel}",
            message,
            exclude_user_id=exclude_user_id,
        )

        return sent

    async def broadcast_all(
        self,
        message: WebSocketMessage | dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all connected users.

        Args:
            message: Message to send

        Returns:
            Number of successful sends
        """
        sent = 0

        # Send to all local connections
        for connections in self._connections.values():
            for connection in connections:
                if await self.send_to_connection(connection, message):
                    sent += 1

        # Publish to Redis for other instances
        await self._publish_to_redis("broadcast", message)

        return sent

    async def send_error(
        self,
        connection: Connection,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Send an error message to a connection."""
        error = ErrorMessage(
            code=code,
            message=message,
            details=details,
        )
        return await self.send_to_connection(
            connection,
            WebSocketMessage(
                type=EventType.ERROR,
                data=error.model_dump(mode="json"),
            ),
        )

    def get_user_connections(self, user_id: str) -> list[Connection]:
        """Get all connections for a specific user."""
        return self._connections.get(user_id, [])

    def is_user_online(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_channel_subscribers(self, channel: str) -> set[str]:
        """Get all user IDs subscribed to a channel."""
        return self._channel_subscribers.get(channel, set()).copy()

    # --- Redis Pub/Sub Methods ---

    async def _publish_to_redis(
        self,
        target: str,
        message: WebSocketMessage | dict[str, Any],
        exclude_user_id: str | None = None,
    ) -> None:
        """Publish a message to Redis for cross-instance delivery."""
        redis = get_redis()
        if not redis:
            return

        try:
            if isinstance(message, WebSocketMessage):
                data = message.model_dump(mode="json")
            else:
                data = message

            payload = {
                "target": target,
                "message": data,
                "exclude_user_id": exclude_user_id,
            }

            await redis.publish(
                f"{REDIS_CHANNEL_PREFIX}messages",
                json.dumps(payload, default=str),
            )
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")

    async def _publish_event(
        self,
        event_type: EventType,
        data: dict[str, Any],
        channel: str | None = None,
    ) -> None:
        """Publish a WebSocket event via Redis."""
        message = WebSocketMessage(
            type=event_type,
            data=data,
            channel=channel,
        )
        if channel:
            await self.broadcast_to_channel(channel, message)
        else:
            await self.broadcast_all(message)

    async def _listen_redis_pubsub(self) -> None:
        """Listen for Redis pub/sub messages and deliver locally."""
        redis = get_redis()
        if not redis:
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(f"{REDIS_CHANNEL_PREFIX}messages")

        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message["type"] == "message":
                    await self._handle_redis_message(message["data"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis pub/sub error: {e}")
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    async def _handle_redis_message(self, data: str) -> None:
        """Handle a message received from Redis pub/sub."""
        try:
            payload = json.loads(data)
            target = payload["target"]
            message = payload["message"]
            exclude_user_id = payload.get("exclude_user_id")

            if target == "broadcast":
                # Broadcast to all local connections
                for connections in self._connections.values():
                    for connection in connections:
                        await self.send_to_connection(connection, message)

            elif target.startswith("user:"):
                # Send to specific user
                user_id = target.split(":", 1)[1]
                if user_id in self._connections:
                    for connection in self._connections[user_id]:
                        await self.send_to_connection(connection, message)

            elif target.startswith("channel:"):
                # Broadcast to channel subscribers
                channel = target.split(":", 1)[1]
                if channel in self._channel_subscribers:
                    for user_id in self._channel_subscribers[channel]:
                        if user_id == exclude_user_id:
                            continue
                        if user_id in self._connections:
                            for connection in self._connections[user_id]:
                                await self.send_to_connection(connection, message)

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _update_presence(self, user_id: str, online: bool) -> None:
        """Update user presence in Redis for cross-instance awareness."""
        redis = get_redis()
        if not redis:
            return

        try:
            if online:
                # Add user to presence set with timestamp
                await redis.hset(
                    REDIS_PRESENCE_KEY,
                    user_id,
                    datetime.utcnow().isoformat(),
                )
            else:
                # Remove user from presence set
                await redis.hdel(REDIS_PRESENCE_KEY, user_id)
        except Exception as e:
            logger.error(f"Error updating presence: {e}")

    async def get_online_users(self) -> list[str]:
        """Get list of online users across all instances."""
        redis = get_redis()
        if not redis:
            # Return local only
            return list(self._connections.keys())

        try:
            presence = await redis.hgetall(REDIS_PRESENCE_KEY)
            return list(presence.keys())
        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return list(self._connections.keys())


# Singleton instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the connection manager singleton."""
    return connection_manager
