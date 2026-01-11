"""
WebSocket endpoints for real-time communication.
Supports authentication, channels, and broadcasting.
"""

import json
import logging
from typing import Any

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.security import get_jwks_client
from app.services.websocket import (
    EventType,
    WebSocketMessage,
    connection_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def verify_websocket_token(token: str) -> dict[str, Any] | None:
    """
    Verify JWT token for WebSocket connections.
    Similar to verify_token in security.py but returns None instead of raising.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        if settings.jwt_algorithm == "RS256":
            jwks_client = get_jwks_client()
            if not jwks_client:
                logger.error("JWKS client not configured")
                return None
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        else:
            if not settings.SUPABASE_JWT_SECRET:
                logger.error("JWT secret not configured")
                return None
            key = settings.SUPABASE_JWT_SECRET

        payload = jwt.decode(
            token,
            key=key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,
                "verify_iss": False,
            },
        )

        if not payload.get("sub"):
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.debug("WebSocket token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"WebSocket token invalid: {e}")
        return None
    except Exception as e:
        logger.error(f"WebSocket token verification error: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
):
    """
    WebSocket endpoint for real-time communication.

    ## Authentication
    Pass JWT token as query parameter: `/ws?token=<jwt_token>`

    ## Message Format
    All messages are JSON with the following structure:
    ```json
    {
        "type": "<event_type>",
        "data": {...},
        "channel": "<optional_channel>"
    }
    ```

    ## Supported Event Types

    ### Client -> Server
    - `subscribe`: Subscribe to a channel
      ```json
      {"type": "subscribe", "channel": "notifications"}
      ```
    - `unsubscribe`: Unsubscribe from a channel
      ```json
      {"type": "unsubscribe", "channel": "notifications"}
      ```
    - `ping`: Keep-alive ping (server responds with pong)
      ```json
      {"type": "ping"}
      ```

    ### Server -> Client
    - `connected`: Connection established
    - `subscribed`: Successfully subscribed to channel
    - `unsubscribed`: Successfully unsubscribed from channel
    - `notification`: Push notification
    - `update`: Resource update (CRUD events)
    - `user_online`: User came online
    - `user_offline`: User went offline
    - `pong`: Response to ping
    - `error`: Error message

    ## Example Client Code (JavaScript)
    ```javascript
    const ws = new WebSocket(`wss://api.example.com/api/v1/app/ws?token=${jwt}`);

    ws.onopen = () => {
        // Subscribe to notifications
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'notifications' }));
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
    };
    ```
    """
    # Verify token
    payload = await verify_websocket_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["sub"]

    # Connect
    connection = await connection_manager.connect(websocket, user_id)

    # Send connected message
    await connection_manager.send_to_connection(
        connection,
        WebSocketMessage(
            type=EventType.CONNECTED,
            data={
                "user_id": user_id,
                "message": "Connected to WebSocket",
            },
        ),
    )

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event_type = message.get("type")

                if event_type == EventType.PING.value:
                    # Respond with pong
                    await connection_manager.send_to_connection(
                        connection,
                        WebSocketMessage(type=EventType.PONG),
                    )

                elif event_type == EventType.SUBSCRIBE.value:
                    channel = message.get("channel")
                    if channel:
                        await connection_manager.subscribe(connection, channel)
                    else:
                        await connection_manager.send_error(
                            connection,
                            code="INVALID_REQUEST",
                            message="Channel name required for subscribe",
                        )

                elif event_type == EventType.UNSUBSCRIBE.value:
                    channel = message.get("channel")
                    if channel:
                        await connection_manager.unsubscribe(connection, channel)
                    else:
                        await connection_manager.send_error(
                            connection,
                            code="INVALID_REQUEST",
                            message="Channel name required for unsubscribe",
                        )

                elif event_type == EventType.MESSAGE.value:
                    # Client sending a message to a channel
                    channel = message.get("channel")
                    msg_data = message.get("data")
                    if channel and msg_data:
                        # Broadcast to channel (excluding sender)
                        await connection_manager.broadcast_to_channel(
                            channel,
                            WebSocketMessage(
                                type=EventType.MESSAGE,
                                channel=channel,
                                data={
                                    "from_user_id": user_id,
                                    "content": msg_data,
                                },
                            ),
                            exclude_user_id=user_id,
                        )
                    else:
                        await connection_manager.send_error(
                            connection,
                            code="INVALID_REQUEST",
                            message="Channel and data required for message",
                        )

                else:
                    # Unknown event type
                    await connection_manager.send_error(
                        connection,
                        code="UNKNOWN_EVENT",
                        message=f"Unknown event type: {event_type}",
                    )

            except json.JSONDecodeError:
                await connection_manager.send_error(
                    connection,
                    code="INVALID_JSON",
                    message="Invalid JSON message",
                )

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(connection)


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket service status.

    Returns connection statistics and online users.
    """
    online_users = await connection_manager.get_online_users()
    return {
        "status": "running",
        "local_connections": connection_manager.connection_count,
        "local_users": connection_manager.user_count,
        "total_online_users": len(online_users),
        "online_user_ids": online_users[:100],  # Limit to first 100
    }
