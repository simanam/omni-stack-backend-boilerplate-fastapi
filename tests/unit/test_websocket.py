"""
Unit tests for WebSocket service.
Tests connection manager, events, and message handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.websocket import (
    Connection,
    ConnectionManager,
    EventType,
    NotificationMessage,
    UpdateMessage,
    WebSocketMessage,
)


class TestEventTypes:
    """Tests for WebSocket event types and messages."""

    def test_event_type_values(self):
        """Test event type enum values."""
        assert EventType.CONNECTED.value == "connected"
        assert EventType.DISCONNECTED.value == "disconnected"
        assert EventType.SUBSCRIBE.value == "subscribe"
        assert EventType.NOTIFICATION.value == "notification"
        assert EventType.PING.value == "ping"
        assert EventType.PONG.value == "pong"

    def test_websocket_message_creation(self):
        """Test WebSocketMessage schema."""
        message = WebSocketMessage(
            type=EventType.NOTIFICATION,
            data={"test": "data"},
            channel="test-channel",
        )
        assert message.type == EventType.NOTIFICATION
        assert message.data == {"test": "data"}
        assert message.channel == "test-channel"
        assert isinstance(message.timestamp, datetime)

    def test_notification_message(self):
        """Test NotificationMessage schema."""
        notification = NotificationMessage(
            title="Test Title",
            body="Test body message",
            data={"extra": "info"},
        )
        assert notification.type == EventType.NOTIFICATION
        assert notification.title == "Test Title"
        assert notification.body == "Test body message"
        assert notification.data == {"extra": "info"}

    def test_update_message(self):
        """Test UpdateMessage schema."""
        update = UpdateMessage(
            resource="project",
            action="created",
            resource_id="123",
            data={"name": "New Project"},
        )
        assert update.type == EventType.UPDATE
        assert update.resource == "project"
        assert update.action == "created"
        assert update.resource_id == "123"


class TestConnection:
    """Tests for Connection dataclass."""

    def test_connection_creation(self):
        """Test Connection dataclass."""
        mock_ws = MagicMock()
        connection = Connection(
            websocket=mock_ws,
            user_id="user-123",
        )
        assert connection.websocket == mock_ws
        assert connection.user_id == "user-123"
        assert isinstance(connection.connected_at, datetime)
        assert connection.channels == set()

    def test_connection_channels(self):
        """Test Connection channel management."""
        mock_ws = MagicMock()
        connection = Connection(
            websocket=mock_ws,
            user_id="user-123",
        )
        connection.channels.add("channel-1")
        connection.channels.add("channel-2")
        assert "channel-1" in connection.channels
        assert "channel-2" in connection.channels


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_manager_start_stop(self, manager):
        """Test manager start and stop."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            await manager.start()
            assert manager._running is True

            await manager.stop()
            assert manager._running is False

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")

            assert connection.user_id == "user-123"
            assert connection.websocket == mock_websocket
            mock_websocket.accept.assert_called_once()
            assert manager.connection_count == 1
            assert manager.user_count == 1
            assert manager.is_user_online("user-123")

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")
            await manager.disconnect(connection)

            assert manager.connection_count == 0
            assert manager.user_count == 0
            assert not manager.is_user_online("user-123")

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self, manager):
        """Test multiple connections from the same user."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            ws1 = AsyncMock()
            ws2 = AsyncMock()

            conn1 = await manager.connect(ws1, "user-123")
            conn2 = await manager.connect(ws2, "user-123")

            assert manager.connection_count == 2
            assert manager.user_count == 1

            # Disconnect one, user should still be online
            await manager.disconnect(conn1)
            assert manager.connection_count == 1
            assert manager.is_user_online("user-123")

            # Disconnect second, user should be offline
            await manager.disconnect(conn2)
            assert not manager.is_user_online("user-123")

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, manager, mock_websocket):
        """Test channel subscription."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")

            await manager.subscribe(connection, "notifications")
            assert "notifications" in connection.channels
            subscribers = manager.get_channel_subscribers("notifications")
            assert "user-123" in subscribers

            await manager.unsubscribe(connection, "notifications")
            assert "notifications" not in connection.channels
            subscribers = manager.get_channel_subscribers("notifications")
            assert "user-123" not in subscribers

    @pytest.mark.asyncio
    async def test_send_to_connection(self, manager, mock_websocket):
        """Test sending message to a connection."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")
            message = WebSocketMessage(
                type=EventType.NOTIFICATION,
                data={"test": "data"},
            )

            result = await manager.send_to_connection(connection, message)
            assert result is True
            mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Test sending message to a user."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            await manager.connect(mock_websocket, "user-123")
            message = WebSocketMessage(
                type=EventType.NOTIFICATION,
                data={"test": "data"},
            )

            sent = await manager.send_to_user("user-123", message)
            assert sent == 1
            mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager):
        """Test broadcasting to a channel."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            ws1 = AsyncMock()
            ws2 = AsyncMock()
            ws3 = AsyncMock()

            conn1 = await manager.connect(ws1, "user-1")
            conn2 = await manager.connect(ws2, "user-2")
            await manager.connect(ws3, "user-3")  # user-3 not subscribed

            await manager.subscribe(conn1, "channel-1")
            await manager.subscribe(conn2, "channel-1")
            # user-3 not subscribed

            message = WebSocketMessage(
                type=EventType.MESSAGE,
                data={"text": "Hello"},
                channel="channel-1",
            )

            sent = await manager.broadcast_to_channel("channel-1", message)
            assert sent == 2  # Only user-1 and user-2

    @pytest.mark.asyncio
    async def test_broadcast_to_channel_exclude_user(self, manager):
        """Test broadcasting to channel with exclusion."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            ws1 = AsyncMock()
            ws2 = AsyncMock()

            conn1 = await manager.connect(ws1, "user-1")
            conn2 = await manager.connect(ws2, "user-2")

            await manager.subscribe(conn1, "channel-1")
            await manager.subscribe(conn2, "channel-1")

            message = WebSocketMessage(
                type=EventType.MESSAGE,
                data={"text": "Hello"},
            )

            # Exclude user-1 from broadcast
            sent = await manager.broadcast_to_channel(
                "channel-1",
                message,
                exclude_user_id="user-1",
            )
            assert sent == 1  # Only user-2

    @pytest.mark.asyncio
    async def test_broadcast_all(self, manager):
        """Test broadcasting to all connections."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            ws1 = AsyncMock()
            ws2 = AsyncMock()
            ws3 = AsyncMock()

            await manager.connect(ws1, "user-1")
            await manager.connect(ws2, "user-2")
            await manager.connect(ws3, "user-3")

            message = WebSocketMessage(
                type=EventType.NOTIFICATION,
                data={"announcement": "Server maintenance"},
            )

            sent = await manager.broadcast_all(message)
            assert sent == 3

    @pytest.mark.asyncio
    async def test_send_error(self, manager, mock_websocket):
        """Test sending error message."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")

            result = await manager.send_error(
                connection,
                code="INVALID_REQUEST",
                message="Something went wrong",
                details={"field": "test"},
            )

            assert result is True
            mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_connections(self, manager):
        """Test getting user connections."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            ws1 = AsyncMock()
            ws2 = AsyncMock()

            await manager.connect(ws1, "user-1")
            await manager.connect(ws2, "user-1")

            connections = manager.get_user_connections("user-1")
            assert len(connections) == 2

            # Non-existent user
            connections = manager.get_user_connections("user-999")
            assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_cleanup_on_disconnect(self, manager, mock_websocket):
        """Test that channel subscriptions are cleaned up on disconnect."""
        with patch("app.services.websocket.manager.get_redis", return_value=None):
            connection = await manager.connect(mock_websocket, "user-123")
            await manager.subscribe(connection, "channel-1")
            await manager.subscribe(connection, "channel-2")

            assert "channel-1" in connection.channels
            assert "channel-2" in connection.channels

            await manager.disconnect(connection)

            # Channel subscriptions should be empty
            assert len(manager.get_channel_subscribers("channel-1")) == 0
            assert len(manager.get_channel_subscribers("channel-2")) == 0


class TestConnectionManagerWithRedis:
    """Tests for ConnectionManager with Redis pub/sub."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.publish = AsyncMock()
        redis.hset = AsyncMock()
        redis.hdel = AsyncMock()
        redis.hgetall = AsyncMock(return_value={"user-1": "2024-01-01T00:00:00"})
        redis.pubsub = MagicMock()
        return redis

    @pytest.mark.asyncio
    async def test_presence_update_on_connect(self, mock_redis):
        """Test presence is updated in Redis on connect."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()

        with patch("app.services.websocket.manager.get_redis", return_value=mock_redis):
            await manager.connect(mock_ws, "user-123")

            # Should update presence in Redis
            mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_presence_update_on_disconnect(self, mock_redis):
        """Test presence is removed from Redis on disconnect."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()

        with patch("app.services.websocket.manager.get_redis", return_value=mock_redis):
            connection = await manager.connect(mock_ws, "user-123")
            await manager.disconnect(connection)

            # Should remove presence from Redis
            mock_redis.hdel.assert_called_with("ws:presence", "user-123")

    @pytest.mark.asyncio
    async def test_get_online_users_from_redis(self, mock_redis):
        """Test getting online users from Redis."""
        manager = ConnectionManager()

        with patch("app.services.websocket.manager.get_redis", return_value=mock_redis):
            online = await manager.get_online_users()
            assert "user-1" in online

    @pytest.mark.asyncio
    async def test_publish_to_redis(self, mock_redis):
        """Test publishing messages to Redis."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()

        with patch("app.services.websocket.manager.get_redis", return_value=mock_redis):
            await manager.connect(mock_ws, "user-123")

            message = WebSocketMessage(
                type=EventType.NOTIFICATION,
                data={"test": "data"},
            )

            await manager.send_to_user("user-456", message)

            # Should publish to Redis for other instances
            mock_redis.publish.assert_called()
