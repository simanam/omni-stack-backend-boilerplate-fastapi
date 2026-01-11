"""
API v1 router aggregation.
Combines all v1 route modules into a single router.
"""

from fastapi import APIRouter

from app.api.v1.admin import dashboard as admin_dashboard
from app.api.v1.admin import feature_flags as admin_feature_flags
from app.api.v1.admin import impersonate as admin_impersonate
from app.api.v1.admin import jobs as admin_jobs
from app.api.v1.admin import users as admin_users
from app.api.v1.app import ai, billing, files, projects, users, ws
from app.api.v1.public import health, metrics, webhooks

# Public routes (no auth required)
public_router = APIRouter(prefix="/public", tags=["Public"])
public_router.include_router(health.router)
public_router.include_router(webhooks.router, prefix="/webhooks")
public_router.include_router(metrics.router)

# App routes (auth required)
app_router = APIRouter(prefix="/app", tags=["App"])
app_router.include_router(users.router, prefix="/users")
app_router.include_router(projects.router, prefix="/projects")
app_router.include_router(files.router, prefix="/files")
app_router.include_router(ai.router, prefix="/ai")
app_router.include_router(billing.router, prefix="/billing")
app_router.include_router(ws.router)  # WebSocket at /api/v1/app/ws

# Admin routes (auth + admin role required)
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(admin_users.router, prefix="/users")
admin_router.include_router(admin_jobs.router, prefix="/jobs")
admin_router.include_router(admin_dashboard.router, prefix="/dashboard")
admin_router.include_router(admin_feature_flags.router, prefix="/feature-flags")
admin_router.include_router(admin_impersonate.router, prefix="/impersonate")

# Aggregate all v1 routes
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public_router)
api_router.include_router(app_router)
api_router.include_router(admin_router)
