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
   - [Users](#user-endpoints)
   - [Projects](#project-endpoints)
   - [Files](#file-endpoints)
   - [AI](#ai-endpoints)
   - [Billing](#billing-endpoints)
   - [Admin](#admin-endpoints)
   - [Webhooks](#webhook-endpoints)

---

## Overview

### Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://your-domain.com/api/v1
```

### Route Structure

```
/api/v1/
├── public/          # No authentication required
│   ├── health       # Health checks
│   ├── webhooks/    # External service webhooks
│   └── metrics      # Prometheus metrics
│
├── app/             # Authentication required
│   ├── users/       # User profile management
│   ├── projects/    # Project CRUD
│   ├── files/       # File upload/download
│   ├── ai/          # AI completions
│   └── billing/     # Subscription management
│
└── admin/           # Authentication + Admin role required
    ├── users/       # User management
    └── jobs/        # Background job monitoring
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

## OpenAPI / Swagger

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
