# Phase 5: Background Jobs ✅ COMPLETE

**Duration:** Async task processing phase
**Goal:** Set up ARQ for background job processing
**Status:** ✅ Complete & Verified (2026-01-10)

**Prerequisites:** Phase 1-4 completed (especially Redis)

---

## 5.1 ARQ Worker Configuration ✅

### Files to create:
- [x] `app/jobs/worker.py` — Worker settings

### Checklist:
- [x] `get_redis_settings()` — Parse REDIS_URL for ARQ
- [x] `startup()` — Worker startup hook
- [x] `shutdown()` — Worker shutdown hook
- [x] `WorkerSettings` class:
  - [x] Redis settings
  - [x] Function imports
  - [x] Cron jobs configuration
  - [x] Job timeout settings
  - [x] Result retention

### Validation:
- [x] Worker starts with `arq app.jobs.worker.WorkerSettings`
- [x] Connects to Redis

---

## 5.2 Job Enqueue Helper ✅

### Files to create:
- [x] `app/jobs/__init__.py` — Job utilities

### Checklist:
- [x] `get_job_pool()` — Get/create ARQ connection pool
- [x] `enqueue()` — Universal job enqueue function:
  - [x] Accept function name and args
  - [x] Support job ID for deduplication
  - [x] Support defer_by for delayed execution
  - [x] Fallback to sync execution if Redis unavailable
- [x] `enqueue_in()` — Convenience function for delayed jobs

### Validation:
- [x] Jobs enqueue successfully
- [x] Fallback executes synchronously

---

## 5.3 Email Jobs ✅

### Files to create:
- [x] `app/jobs/email_jobs.py` — Email-related tasks

### Checklist:
- [x] `send_welcome_email(ctx, user_email, user_name)`
- [x] `send_password_reset_email(ctx, user_email, reset_link)`
- [x] `send_notification_email(ctx, user_email, subject, body)`
- [x] Error handling with logging
- [x] Placeholder for email service integration (Phase 6)

### Validation:
- [x] Jobs execute correctly
- [x] Errors logged properly

---

## 5.4 Report Jobs ✅

### Files to create:
- [x] `app/jobs/report_jobs.py` — Report generation tasks

### Checklist:
- [x] `generate_daily_report(ctx)` — Scheduled daily task
- [x] `export_user_data(ctx, user_id)` — On-demand data export (GDPR)
- [x] `cleanup_old_data(ctx)` — Maintenance task
- [x] Database session handling in jobs via `get_session_context()`

### Validation:
- [x] Jobs can access database
- [x] Scheduled jobs configured in WorkerSettings

---

## 5.5 Job Monitoring Endpoints ✅

### Files to create:
- [x] `app/api/v1/admin/jobs.py` — Job monitoring

### Checklist:
- [x] `GET /api/v1/admin/jobs` — List recent jobs
- [x] `GET /api/v1/admin/jobs/{job_id}` — Get job status
- [x] `POST /api/v1/admin/jobs/{job_id}/retry` — Retry failed job
- [x] `DELETE /api/v1/admin/jobs/{job_id}` — Cancel pending job

### Validation:
- [x] Endpoints protected with admin role
- [x] Can view job history
- [x] Can retry failed jobs

---

## 5.6 Scheduled Tasks (Cron) ✅

### Files to update:
- [x] `app/jobs/worker.py` — Add cron_jobs

### Checklist:
- [x] Configure cron schedule format
- [x] Daily report at 9am UTC
- [x] Weekly cleanup task (Sunday midnight)

### Validation:
- [x] Cron jobs configured in WorkerSettings.cron_jobs

---

## 5.7 Job Decorators ✅

### Files to create:
- [x] `app/jobs/decorators.py` — Job helper decorators

### Checklist:
- [x] `@background_task` — Combined decorator with retry + timeout
- [x] `@retry(config)` — Automatic retry with exponential backoff
- [x] `@timeout(seconds)` — Job timeout
- [x] `RetryConfig` dataclass for configuration

### Validation:
- [x] Decorators work correctly
- [x] Retries happen on failure
- [x] Timeouts raise asyncio.TimeoutError

---

## 5.8 Integration with API ✅

### Files to update:
- [x] `app/api/v1/router.py` — Include admin jobs router

### Example Usage:
```python
from app.jobs import enqueue

@router.post("/welcome")
async def send_welcome(user: CurrentUser):
    await enqueue(
        "app.jobs.email_jobs.send_welcome_email",
        user.email,
        user.full_name
    )
    return {"status": "email queued"}
```

### Validation:
- [x] API endpoints can enqueue jobs
- [x] Jobs execute asynchronously (or sync fallback)

---

## 5.9 Makefile Commands ✅

### Files to update:
- [x] `Makefile` — Add worker commands

### Checklist:
- [x] `make worker` — Start ARQ worker
- [x] `make worker-dev` — Start worker with watchfiles reload

### Validation:
- [x] Commands work correctly

---

## 5.10 Docker Integration ✅

### Files to update:
- [x] `docker/docker-compose.yml` — Add worker service

### Checklist:
- [x] Worker service definition
- [x] Shared environment with API
- [x] Depends on Redis and DB
- [x] Uses `--profile worker` for optional startup

### Validation:
- [x] Worker starts with `docker compose --profile worker up`
- [x] Processes jobs from queue

---

## Phase 5 Completion Criteria ✅

- [x] ARQ worker starts and connects to Redis
- [x] Jobs can be enqueued from API endpoints
- [x] Jobs execute in background (or sync fallback)
- [x] Failed jobs can be retried via admin endpoint
- [x] Scheduled jobs configured (daily report, weekly cleanup)
- [x] Job status visible in admin endpoints
- [x] Worker runs in Docker alongside API
- [x] 20 unit tests passing
- [x] All linting checks pass

---

## Files Created/Updated in Phase 5

| File | Purpose |
|------|---------|
| `app/jobs/worker.py` | ARQ worker configuration |
| `app/jobs/__init__.py` | Enqueue helper functions |
| `app/jobs/email_jobs.py` | Email background tasks |
| `app/jobs/report_jobs.py` | Report generation tasks |
| `app/jobs/decorators.py` | Job helper decorators |
| `app/api/v1/admin/jobs.py` | Job monitoring endpoints |
| `app/api/v1/router.py` | Updated to include jobs router |
| `Makefile` | Added worker commands |
| `docker/docker-compose.yml` | Added worker service |
| `tests/unit/test_jobs.py` | 20 unit tests |

---

## Test Results

```
tests/unit/test_jobs.py - 20 tests passing
- TestWorkerConfig: 6 tests
- TestEnqueue: 2 tests
- TestEmailJobs: 3 tests
- TestReportJobs: 3 tests
- TestDecorators: 6 tests
```

---

*Completed: 2026-01-10*
