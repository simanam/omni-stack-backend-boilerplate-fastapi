"""
API v2 router aggregation.

Combines all v2 route modules into a single router.
v2 introduces enhanced response formats with metadata wrappers,
improved validation, and additional computed fields.

Key differences from v1:
- All responses wrapped in {data: ..., meta: ...} format
- Metadata includes request_id, timestamp, version
- Enhanced health checks with latency metrics
- Stricter input validation
"""

from fastapi import APIRouter

from app.api.v2.app import users
from app.api.v2.public import health

# Public routes (no auth required)
public_router = APIRouter(prefix="/public", tags=["Public v2"])
public_router.include_router(health.router)

# App routes (auth required)
app_router = APIRouter(prefix="/app", tags=["App v2"])
app_router.include_router(users.router, prefix="/users")

# Admin routes - reuse v1 admin routes for now
# (in practice, you might create v2-specific admin endpoints)
# from app.api.v1.admin import users as admin_users, dashboard, ...
# admin_router = APIRouter(prefix="/admin", tags=["Admin v2"])
# admin_router.include_router(admin_users.router, prefix="/users")

# Aggregate all v2 routes
api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(public_router)
api_v2_router.include_router(app_router)
# api_v2_router.include_router(admin_router)  # Uncomment when v2 admin routes are ready
