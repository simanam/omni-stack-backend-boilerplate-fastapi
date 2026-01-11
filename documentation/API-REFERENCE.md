# API Reference

Complete API documentation for OmniStack Backend.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Response Formats](#response-formats)
4. [Error Responses](#error-responses)
5. [Pagination](#pagination)
6. [Rate Limiting](#rate-limiting)
7. [Endpoints](#endpoints)
   - [Health](#health-endpoints)
   - [Contact Form](#contact-form-endpoints)
   - [Users](#user-endpoints)
   - [Projects](#project-endpoints)
   - [Files](#file-endpoints)
   - [AI](#ai-endpoints)
   - [Billing](#billing-endpoints)
   - [WebSocket](#websocket-endpoints)
   - [Admin](#admin-endpoints)
   - [Webhooks](#webhook-endpoints)

---

## Overview

### Base URL

```
Development: http://localhost:8000/api/v1  (or /api/v2)
Production:  https://your-domain.com/api/v1  (or /api/v2)
```

### API Versions

| Version | Status | Description |
|---------|--------|-------------|
| v1 | Stable | Original API with standard responses |
| v2 | Stable | Enhanced responses with metadata wrapper |

Both versions are available simultaneously. v2 responses include:
- Request ID for tracing
- ISO 8601 timestamps with timezone
- API version in response metadata

### Route Structure

```
/api/v1/
├── public/          # No authentication required
│   ├── health       # Health checks
│   ├── contact      # Contact form submissions
│   ├── webhooks/    # External service webhooks
│   └── metrics      # Prometheus metrics
│
├── app/             # Authentication required
│   ├── users/       # User profile management
│   ├── projects/    # Project CRUD
│   ├── files/       # File upload/download
│   ├── ai/          # AI completions
│   ├── billing/     # Subscription management
│   └── ws           # WebSocket connections
│
└── admin/           # Authentication + Admin role required
    ├── users/       # User management
    ├── jobs/        # Background job monitoring
    ├── dashboard/   # System metrics & stats
    ├── feature-flags/ # Feature flag management
    └── impersonate/ # User impersonation
```

### HTTP Methods Convention

| Method | Usage | Example |
|--------|-------|---------|
| `GET` | Retrieve resource(s) | `GET /projects` |
| `POST` | Create new resource | `POST /projects` |
| `PATCH` | Partial update | `PATCH /projects/{id}` |
| `DELETE` | Remove resource | `DELETE /projects/{id}` |

> **Note:** We use `PATCH` (not `PUT`) for updates because all update fields are optional.

---

## Authentication

### Bearer Token

All `/app/*` and `/admin/*` endpoints require a JWT token in the `Authorization` header:

```http
Authorization: Bearer <jwt_token>
```

### Supported Auth Providers

| Provider | JWT Algorithm | Token Source |
|----------|---------------|--------------|
| Supabase | RS256 (or HS256 legacy) | `supabase.auth.getSession()` |
| Clerk | RS256 | `useAuth().getToken()` |
| Custom OAuth | RS256 | Your OAuth provider |

### Token Structure (JWT Claims)

```json
{
  "sub": "user_123abc",           // User ID (required)
  "email": "user@example.com",    // User email
  "role": "user",                 // user | admin | superadmin
  "exp": 1704067200,              // Expiration timestamp
  "iat": 1704063600               // Issued at timestamp
}
```

### Authentication Errors

| Status | Code | Description |
|--------|------|-------------|
| 401 | `AUTHENTICATION_ERROR` | Missing or invalid token |
| 403 | `AUTHORIZATION_ERROR` | Insufficient permissions |

---

## Response Formats

### Success Response (Single Resource)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Project",
  "description": "Project description",
  "owner_id": "user_123abc",
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z"
}
```

### Success Response (List with Pagination)

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Project 1",
      "created_at": "2026-01-10T12:00:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Project 2",
      "created_at": "2026-01-09T12:00:00Z"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 20
}
```

### Success Response (Simple Message)

```json
{
  "message": "Operation completed successfully"
}
```

### No Content Response

For `DELETE` operations, returns `204 No Content` with empty body.

### v2 Response Format (Enhanced)

API v2 wraps all responses in a standardized format with metadata:

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_premium": true,
    "days_since_joined": 42
  },
  "meta": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": "2026-01-11T12:00:00Z",
    "version": "v2"
  }
}
```

v2 endpoints also include additional computed fields (e.g., `is_premium`, `days_since_joined`).

---

## API Version Headers

All API responses include version headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-API-Version` | API version used for this request | `v1` or `v2` |
| `X-API-Latest-Version` | Latest available API version | `v2` |

### Deprecated Version Headers (when applicable)

When a version is deprecated, responses include:

| Header | Description | Example |
|--------|-------------|---------|
| `Deprecation` | RFC 8594 deprecation flag | `true` |
| `Sunset` | RFC 8594 removal date | `Wed, 31 Dec 2025 23:59:59 GMT` |
| `X-Deprecation-Notice` | Human-readable message | `API v1 is deprecated...` |
| `Link` | Link to successor version | `</api/v2/>; rel="successor-version"` |

### Version Selection

Versions can be specified via:

1. **URL Path** (recommended): `/api/v1/...` or `/api/v2/...`
2. **Accept-Version Header**: `Accept-Version: v2`
3. **X-API-Version Header**: `X-API-Version: v2`

URL path takes precedence over headers.

---

## Error Responses

### Error Response Format

All errors follow this consistent structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "additional_info"
    }
  }
}
```

### Error Codes Reference

| HTTP Status | Code | Description | Common Causes |
|-------------|------|-------------|---------------|
| 400 | `BAD_REQUEST` | Invalid request | Malformed JSON, invalid parameters |
| 401 | `AUTHENTICATION_ERROR` | Auth failed | Missing/expired token |
| 403 | `AUTHORIZATION_ERROR` | Access denied | Wrong role, not owner |
| 404 | `NOT_FOUND` | Resource not found | Invalid ID, deleted resource |
| 409 | `CONFLICT` | Resource conflict | Duplicate entry |
| 422 | `VALIDATION_ERROR` | Validation failed | Invalid field values |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests | Rate limit hit |
| 502 | `EXTERNAL_SERVICE_ERROR` | External service failed | AI/Email/Payment error |
| 503 | `SERVICE_UNAVAILABLE` | Service not configured | Missing API keys |

### Example Error Responses

**Not Found (404)**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project not found",
    "details": {
      "resource": "Project",
      "id": "invalid-uuid"
    }
  }
}
```

**Validation Error (422)**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Name must be at least 1 character",
    "details": {
      "field": "name"
    }
  }
}
```

**Rate Limit (429)**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "retry_after": 60
    }
  }
}
```

---

## Pagination

### Query Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `skip` | integer | 0 | 0+ | Number of items to skip |
| `limit` | integer | 20 | 1-100 | Maximum items to return |

### Request Example

```http
GET /api/v1/app/projects?skip=20&limit=10
```

### Response Structure

```json
{
  "items": [...],
  "total": 100,    // Total items in database
  "skip": 20,      // Items skipped
  "limit": 10      // Max items returned
}
```

### Calculating Pagination

```javascript
// Frontend pagination helper
const totalPages = Math.ceil(response.total / response.limit);
const currentPage = Math.floor(response.skip / response.limit) + 1;
const hasNextPage = response.skip + response.items.length < response.total;
const hasPrevPage = response.skip > 0;
```

---

## Rate Limiting

### Rate Limit Headers

Every response includes these headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Max requests per window | `60` |
| `X-RateLimit-Remaining` | Remaining requests | `45` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1704067200` |

### Default Limits

| Route Pattern | Limit | Window |
|---------------|-------|--------|
| Default | 60 requests | per minute |
| `/app/ai/*` | 10 requests | per minute |
| `/public/auth/*` | 5 requests | per minute |

### Rate Limit Response (429)

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067200
Retry-After: 45

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "retry_after": 45
    }
  }
}
```

---

## Endpoints

### Health Endpoints

#### Check Health

```http
GET /api/v1/public/health
```

**Response (200)**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-10T12:00:00Z"
}
```

#### Check Readiness

```http
GET /api/v1/public/health/ready
```

**Response (200)**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-10T12:00:00Z",
  "components": {
    "database": { "status": "healthy" },
    "cache": { "status": "healthy" }
  }
}
```

---

### Contact Form Endpoints

Public endpoints for contact form submissions. No authentication required.

#### Submit Contact Form

```http
POST /api/v1/public/contact
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "message": "I'd like to learn more about your services.",
  "subject": "Product Inquiry",
  "phone": "+1-555-0123",
  "company": "Acme Inc",
  "extra_fields": {
    "budget": "$5000-$10000",
    "project_type": "web-app",
    "referral_source": "google"
  },
  "source": "homepage"
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Sender's name (2-100 chars) |
| `email` | string | Yes | Sender's email address |
| `message` | string | Yes | Message content (10-5000 chars) |
| `subject` | string | Configurable | Message subject (max 200 chars) |
| `phone` | string | Configurable | Phone number (max 50 chars) |
| `company` | string | No | Company name (max 200 chars) |
| `extra_fields` | object | No | Custom fields (any key-value pairs) |
| `source` | string | No | Form source for analytics (max 100 chars) |

> **Note:** `subject` and `phone` can be made required via `CONTACT_REQUIRE_SUBJECT` and `CONTACT_REQUIRE_PHONE` settings.

**Response (200)**
```json
{
  "success": true,
  "message": "Thank you for your message. We'll get back to you soon!",
  "reference_id": "CNT-A1B2C3D4"
}
```

**Error Response (429 - Rate Limited)**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many contact form submissions. Please try again later.",
    "details": { "retry_after": 3600 }
  }
}
```

#### Get Contact Form Status

```http
GET /api/v1/public/contact/status
```

**Response (200)**
```json
{
  "available": true,
  "rate_limit": {
    "limit": 5,
    "remaining": 4,
    "reset": 1704110400,
    "window": "5/hour"
  },
  "config": {
    "require_subject": false,
    "require_phone": false,
    "sends_confirmation": true
  }
}
```

#### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CONTACT_REQUIRE_SUBJECT` | `false` | Make subject field required |
| `CONTACT_REQUIRE_PHONE` | `false` | Make phone field required |
| `CONTACT_SEND_CONFIRMATION` | `true` | Send confirmation email to sender |
| `CONTACT_WEBHOOK_URL` | - | Webhook URL for CRM integrations |
| `CONTACT_RATE_LIMIT` | `5/hour` | Rate limit per IP address |
| `ADMIN_EMAIL` | - | Admin notification email |

#### Webhook Integration

When `CONTACT_WEBHOOK_URL` is set, submissions are sent to your webhook:

```json
{
  "event": "contact.submitted",
  "timestamp": "2026-01-11T12:00:00Z",
  "data": {
    "reference_id": "CNT-A1B2C3D4",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-0123",
    "company": "Acme Inc",
    "subject": "Product Inquiry",
    "message": "I'd like to learn more...",
    "extra_fields": { "budget": "$5000-$10000" },
    "source": "homepage",
    "submitted_at": "2026-01-11T12:00:00Z"
  }
}
```

**Webhook Headers**

| Header | Description |
|--------|-------------|
| `X-Webhook-Signature` | SHA256 signature for verification |
| `X-Reference-Id` | Submission reference ID |

---

### User Endpoints

#### Get Current User

```http
GET /api/v1/app/users/me
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "id": "user_123abc",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "role": "user",
  "is_active": true,
  "subscription_plan": "pro",
  "subscription_status": "active",
  "created_at": "2026-01-01T00:00:00Z"
}
```

#### Update Current User

```http
PATCH /api/v1/app/users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg"
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `full_name` | string | No | Display name (max 255 chars) |
| `avatar_url` | string | No | Avatar URL (max 2048 chars) |

**Response (200)**: Updated user object

---

### Project Endpoints

#### List Projects

```http
GET /api/v1/app/projects
Authorization: Bearer <token>
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Items to skip |
| `limit` | integer | 20 | Max items (1-100) |
| `search` | string | - | Search by name |

**Response (200)**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Project",
      "description": "Project description",
      "owner_id": "user_123abc",
      "created_at": "2026-01-10T12:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

#### Create Project

```http
POST /api/v1/app/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Project",
  "description": "Optional description"
}
```

**Request Body**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | Yes | 1-255 chars | Project name |
| `description` | string | No | max 2000 chars | Description |

**Response (201)**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "New Project",
  "description": "Optional description",
  "owner_id": "user_123abc",
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z"
}
```

#### Get Project

```http
GET /api/v1/app/projects/{project_id}
Authorization: Bearer <token>
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string (UUID) | Project ID |

**Response (200)**: Project object

**Errors**
- `404 NOT_FOUND`: Project doesn't exist or user doesn't own it

#### Update Project

```http
PATCH /api/v1/app/projects/{project_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New name (1-255 chars) |
| `description` | string | No | New description |

**Response (200)**: Updated project object

#### Delete Project

```http
DELETE /api/v1/app/projects/{project_id}
Authorization: Bearer <token>
```

**Response (204)**: No content

> **Note:** Projects are soft-deleted (marked with `deleted_at` timestamp).

---

### File Endpoints

#### Get Presigned Upload URL

```http
POST /api/v1/app/files/upload-url
Authorization: Bearer <token>
Content-Type: application/json

{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 1048576
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | Yes | Original filename |
| `content_type` | string | Yes | MIME type |
| `size` | integer | Yes | File size in bytes |

**Response (200)**
```json
{
  "upload_url": "https://storage.example.com/presigned-upload-url",
  "file_id": "file_abc123",
  "key": "uploads/user_123/abc123/document.pdf",
  "expires_in": 3600
}
```

#### Confirm Upload

```http
POST /api/v1/app/files/confirm
Authorization: Bearer <token>
Content-Type: application/json

{
  "file_id": "file_abc123"
}
```

**Response (200)**
```json
{
  "id": "file_abc123",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 1048576,
  "status": "uploaded",
  "created_at": "2026-01-10T12:00:00Z"
}
```

#### List Files

```http
GET /api/v1/app/files
Authorization: Bearer <token>
```

**Response (200)**: Paginated list of files

#### Get Download URL

```http
GET /api/v1/app/files/{file_id}/download-url
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "download_url": "https://storage.example.com/presigned-download-url",
  "expires_in": 3600
}
```

#### Delete File

```http
DELETE /api/v1/app/files/{file_id}
Authorization: Bearer <token>
```

**Response (204)**: No content

---

### AI Endpoints

#### Get AI Status

```http
GET /api/v1/app/ai/status
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "available": true,
  "providers": ["openai", "anthropic"],
  "default_provider": "openai",
  "default_model": "gpt-4o"
}
```

#### Chat Completion

```http
POST /api/v1/app/ai/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello, how are you?" }
  ],
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `messages` | array | Yes | - | Chat messages |
| `messages[].role` | string | Yes | - | `system`, `user`, or `assistant` |
| `messages[].content` | string | Yes | - | Message content |
| `model` | string | No | `gpt-4o` | Model to use |
| `temperature` | number | No | 0.7 | Creativity (0-2) |
| `max_tokens` | integer | No | 1000 | Max response tokens |
| `stream` | boolean | No | false | Enable streaming |

**Response (200)**
```json
{
  "content": "Hello! I'm doing well, thank you for asking.",
  "model": "gpt-4o",
  "provider": "openai",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 12,
    "total_tokens": 37
  },
  "finish_reason": "stop",
  "latency_ms": 450.5
}
```

#### Simple Chat

```http
POST /api/v1/app/ai/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "Explain quantum computing in one sentence.",
  "system": "You are a physics teacher.",
  "temperature": 0.5
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | User prompt |
| `system` | string | No | System instruction |
| `model` | string | No | Model to use |
| `temperature` | number | No | Creativity (0-2) |
| `max_tokens` | integer | No | Max response tokens |
| `stream` | boolean | No | Enable streaming |

#### Routed Chat (Auto Model Selection)

```http
POST /api/v1/app/ai/chat/routed
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "Solve this complex coding problem...",
  "complexity": "complex"
}
```

**Complexity Levels**

| Level | Model Used | Best For |
|-------|------------|----------|
| `simple` | gpt-4o-mini | Classification, extraction |
| `moderate` | gpt-4o | Summarization, analysis |
| `complex` | claude-sonnet | Reasoning, coding |
| `search` | Perplexity | Current information |

#### Streaming Response

When `stream: true`, response is Server-Sent Events:

```
data: Hello
data:  world
data: !
data: [DONE]
```

---

### Billing Endpoints

#### Get Billing Status

```http
GET /api/v1/app/billing/status
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "plan": "pro",
  "status": "active",
  "current_period_end": "2026-02-10T12:00:00Z",
  "cancel_at_period_end": false,
  "has_active_subscription": true
}
```

#### Create Checkout Session

```http
POST /api/v1/app/billing/checkout
Authorization: Bearer <token>
Content-Type: application/json

{
  "plan": "monthly",
  "success_url": "https://app.example.com/billing/success",
  "cancel_url": "https://app.example.com/billing/cancel"
}
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plan` | string | Yes | `monthly` or `yearly` |
| `success_url` | string | Yes | Redirect on success |
| `cancel_url` | string | Yes | Redirect on cancel |

**Response (200)**
```json
{
  "session_id": "cs_xxx",
  "url": "https://checkout.stripe.com/pay/cs_xxx"
}
```

#### Get Billing Portal

```http
GET /api/v1/app/billing/portal?return_url=https://app.example.com/settings
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "url": "https://billing.stripe.com/session/xxx"
}
```

#### Get Invoices

```http
GET /api/v1/app/billing/invoices?limit=10
Authorization: Bearer <token>
```

**Response (200)**
```json
[
  {
    "id": "in_xxx",
    "number": "INV-0001",
    "status": "paid",
    "amount_due": 1999,
    "amount_paid": 1999,
    "currency": "usd",
    "created": 1704067200,
    "hosted_invoice_url": "https://invoice.stripe.com/xxx",
    "invoice_pdf": "https://pay.stripe.com/invoice/xxx/pdf"
  }
]
```

#### Cancel Subscription

```http
POST /api/v1/app/billing/cancel?immediate=false
Authorization: Bearer <token>
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `immediate` | boolean | false | Cancel immediately (no refund) |

**Response (200)**
```json
{
  "message": "Subscription will cancel at the end of the billing period",
  "cancel_at_period_end": true,
  "current_period_end": "2026-02-10T12:00:00Z"
}
```

#### Resume Subscription

```http
POST /api/v1/app/billing/resume
Authorization: Bearer <token>
```

**Response (200)**
```json
{
  "message": "Subscription resumed",
  "status": "active",
  "plan": "pro"
}
```

---

### WebSocket Endpoints

Real-time communication via WebSocket connections.

#### Connect to WebSocket

```
WebSocket: ws://localhost:8000/api/v1/app/ws?token=<jwt_token>
```

**Connection Query Parameters**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `token` | Yes | JWT Bearer token for authentication |

**Connection Events**

On successful connection:
```json
{
  "type": "connected",
  "data": {
    "user_id": "user_123abc",
    "connected_at": "2026-01-11T12:00:00Z"
  }
}
```

#### Sending Messages

**Subscribe to Channel**
```json
{
  "type": "subscribe",
  "channel": "project:proj_123"
}
```

**Unsubscribe from Channel**
```json
{
  "type": "unsubscribe",
  "channel": "project:proj_123"
}
```

**Send Message to Channel**
```json
{
  "type": "message",
  "channel": "project:proj_123",
  "data": {
    "action": "update",
    "content": "Hello team!"
  }
}
```

#### Receiving Events

**Channel Message**
```json
{
  "type": "channel_message",
  "channel": "project:proj_123",
  "data": { ... },
  "sender_id": "user_456def",
  "timestamp": "2026-01-11T12:00:00Z"
}
```

**System Notification**
```json
{
  "type": "notification",
  "data": {
    "title": "New comment",
    "message": "Someone commented on your project"
  }
}
```

**Error Event**
```json
{
  "type": "error",
  "message": "Invalid channel format",
  "code": "INVALID_CHANNEL"
}
```

#### Broadcast Message (Server-side)

From your code, broadcast to connected users:

```python
from app.services.websocket import get_ws_manager

manager = get_ws_manager()

# Broadcast to specific user
await manager.send_to_user(user_id, {"type": "notification", "data": {...}})

# Broadcast to channel
await manager.broadcast_to_channel("project:proj_123", {"type": "update", "data": {...}})
```

---

### Admin Endpoints

> **Note:** All admin endpoints require `Authorization` header AND user must have `admin` or `superadmin` role.

#### List All Users

```http
GET /api/v1/admin/users?skip=0&limit=20
Authorization: Bearer <admin_token>
```

**Response (200)**: Paginated list of users with admin details

#### Get User by ID

```http
GET /api/v1/admin/users/{user_id}
Authorization: Bearer <admin_token>
```

#### Update User (Admin)

```http
PATCH /api/v1/admin/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "role": "admin",
  "is_active": true
}
```

#### Deactivate User

```http
POST /api/v1/admin/users/{user_id}/deactivate
Authorization: Bearer <admin_token>
```

#### Activate User

```http
POST /api/v1/admin/users/{user_id}/activate
Authorization: Bearer <admin_token>
```

#### List Background Jobs

```http
GET /api/v1/admin/jobs
Authorization: Bearer <admin_token>
```

#### Retry Failed Job

```http
POST /api/v1/admin/jobs/{job_id}/retry
Authorization: Bearer <admin_token>
```

#### Dashboard Statistics

```http
GET /api/v1/admin/dashboard/stats
Authorization: Bearer <admin_token>
```

**Response (200)**
```json
{
  "users": {
    "total": 1250,
    "active": 1100,
    "new_last_7_days": 45,
    "new_last_30_days": 180
  },
  "subscriptions": {
    "active": 450,
    "by_plan": {
      "free": 800,
      "pro": 350,
      "enterprise": 100
    }
  },
  "webhooks": {
    "total": 5000,
    "failed": 12,
    "pending": 3
  },
  "jobs": {
    "queued": 25,
    "completed_last_24h": 1500,
    "failed_last_24h": 5
  }
}
```

#### List Feature Flags

```http
GET /api/v1/admin/feature-flags
Authorization: Bearer <admin_token>
```

**Response (200)**
```json
{
  "items": [
    {
      "id": "flag_123",
      "key": "new_dashboard",
      "name": "New Dashboard UI",
      "description": "Enable the redesigned dashboard",
      "flag_type": "percentage",
      "is_enabled": true,
      "percentage": 25,
      "user_ids": [],
      "plans": [],
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### Create Feature Flag

```http
POST /api/v1/admin/feature-flags
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "key": "beta_feature",
  "name": "Beta Feature",
  "description": "New experimental feature",
  "flag_type": "percentage",
  "percentage": 10,
  "is_enabled": true
}
```

**Flag Types**

| Type | Description |
|------|-------------|
| `boolean` | Simple on/off toggle |
| `percentage` | Roll out to % of users |
| `user_list` | Enable for specific user IDs |
| `plan_based` | Enable for specific subscription plans |

#### Update Feature Flag

```http
PATCH /api/v1/admin/feature-flags/{flag_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "percentage": 50,
  "is_enabled": true
}
```

#### Delete Feature Flag

```http
DELETE /api/v1/admin/feature-flags/{flag_id}
Authorization: Bearer <admin_token>
```

#### Check Feature Flag

```http
GET /api/v1/admin/feature-flags/{flag_key}/check?user_id=user_123
Authorization: Bearer <admin_token>
```

**Response (200)**
```json
{
  "flag_key": "new_dashboard",
  "is_enabled": true,
  "reason": "percentage_rollout"
}
```

#### Impersonate User

```http
POST /api/v1/admin/impersonate/start
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "user_id": "user_123abc"
}
```

**Response (200)**
```json
{
  "message": "Impersonation started",
  "impersonated_user": {
    "id": "user_123abc",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "token": "<impersonation_jwt_token>",
  "expires_at": "2026-01-11T13:00:00Z"
}
```

> **Note:** Impersonation is logged in the audit log. Admins cannot impersonate other admins or superadmins.

#### Stop Impersonation

```http
POST /api/v1/admin/impersonate/stop
Authorization: Bearer <impersonation_token>
```

#### Get Audit Logs

```http
GET /api/v1/admin/dashboard/audit-logs?limit=50
Authorization: Bearer <admin_token>
```

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `actor_id` | string | Filter by actor user ID |
| `action` | string | Filter by action type |
| `resource_type` | string | Filter by resource type |
| `limit` | integer | Max results (default: 50) |

**Response (200)**
```json
{
  "items": [
    {
      "id": "log_123",
      "actor_id": "admin_456",
      "action": "impersonate.start",
      "resource_type": "user",
      "resource_id": "user_789",
      "details": { "reason": "Support ticket #123" },
      "ip_address": "192.168.1.1",
      "created_at": "2026-01-11T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

### Webhook Endpoints

> **Note:** Webhook endpoints don't require Bearer authentication. They verify requests using provider-specific signatures.

#### Stripe Webhook

```http
POST /api/v1/public/webhooks/stripe
Stripe-Signature: t=xxx,v1=xxx
```

**Handled Events**
- `checkout.session.completed` - New subscription
- `customer.subscription.updated` - Plan change
- `customer.subscription.deleted` - Cancellation
- `invoice.paid` - Successful payment
- `invoice.payment_failed` - Failed payment

#### Clerk Webhook

```http
POST /api/v1/public/webhooks/clerk
svix-id: xxx
svix-timestamp: xxx
svix-signature: xxx
```

**Handled Events**
- `user.created` - New user signup
- `user.updated` - Profile update
- `user.deleted` - User deletion

#### Supabase Webhook

```http
POST /api/v1/public/webhooks/supabase
Authorization: Bearer <webhook_secret>
```

**Handled Events**
- `INSERT` on `auth.users` - New user
- `UPDATE` on `auth.users` - User update
- `DELETE` on `auth.users` - User deletion

#### Apple App Store Webhook

```http
POST /api/v1/public/webhooks/apple
Content-Type: application/json

{
  "signedPayload": "<JWS_signed_notification>"
}
```

**Handled Events**
- `SUBSCRIBED` - New subscription
- `DID_RENEW` - Renewal
- `EXPIRED` - Expiration
- `REFUND` - Refund issued

#### Google Play Webhook

```http
POST /api/v1/public/webhooks/google
Content-Type: application/json

{
  "message": {
    "data": "<base64_encoded_notification>",
    "messageId": "xxx"
  }
}
```

**Handled Events**
- `SUBSCRIPTION_PURCHASED` - New subscription
- `SUBSCRIPTION_RENEWED` - Renewal
- `SUBSCRIPTION_CANCELED` - Cancellation
- `SUBSCRIPTION_EXPIRED` - Expiration

---

## Response Headers

### Standard Headers

Every response includes:

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier for debugging |
| `X-RateLimit-Limit` | Rate limit ceiling |
| `X-RateLimit-Remaining` | Remaining requests |
| `X-RateLimit-Reset` | Reset timestamp |

### Security Headers (Production)

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | `default-src 'self'` |

---

## Distributed Tracing (OpenTelemetry)

When OpenTelemetry is enabled (`OTEL_ENABLED=true`), all requests are automatically traced.

### Trace Context Propagation

The API supports W3C Trace Context propagation. Include these headers to continue a trace from your frontend:

| Header | Description | Example |
|--------|-------------|---------|
| `traceparent` | W3C Trace Context | `00-abc123...-def456...-01` |
| `tracestate` | Vendor-specific trace info | `vendor=value` |

### Trace Correlation in Logs

All log entries include trace context when available:

```json
{
  "timestamp": "2026-01-11T12:00:00Z",
  "level": "INFO",
  "message": "Request completed",
  "trace_id": "abc123def456789012345678901234",
  "span_id": "1234567890abcdef",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Supported Exporters

| Exporter | Configuration | Use Case |
|----------|--------------|----------|
| OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | Jaeger, Grafana Tempo, etc. |
| Zipkin | `OTEL_EXPORTER_ZIPKIN_ENDPOINT` | Zipkin-compatible backends |
| Console | `OTEL_EXPORTER=console` | Local development |

### Auto-Instrumented Components

- HTTP requests (FastAPI endpoints)
- Database queries (SQLAlchemy)
- Redis operations
- External HTTP calls (httpx)

---

## OpenAPI / Swagger

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
