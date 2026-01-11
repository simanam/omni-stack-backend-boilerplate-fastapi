# Phase 3: CRUD Patterns & Data Layer

**Duration:** Data patterns phase
**Goal:** Implement reusable CRUD patterns and example resource
**Status:** ✅ Complete

**Prerequisites:** Phase 1, Phase 2 completed

---

## 3.1 Generic CRUD Base Class

### Files to create:
- [x] `app/business/crud_base.py` — Generic CRUD operations

### Checklist:
- [x] Generic type parameters (ModelType, CreateSchemaType, UpdateSchemaType)
- [x] `get(session, id)` — Get single record by ID
- [x] `get_by_field(session, field, value)` — Get by arbitrary field
- [x] `get_multi(session, skip, limit)` — Paginated list
- [x] `get_multi_by_owner(session, owner_id, skip, limit)` — Owner-scoped list
- [x] `count(session)` — Total count
- [x] `count_by_owner(session, owner_id)` — Owner-scoped count
- [x] `create(session, obj_in)` — Create new record
- [x] `create_with_owner(session, obj_in, owner_id)` — Create with owner
- [x] `update(session, db_obj, obj_in)` — Update existing record
- [x] `delete(session, id)` — Hard delete
- [x] `soft_delete(session, id)` — Soft delete (if mixin used)
- [x] `restore(session, id)` — Restore soft-deleted record

### Validation:
- [x] All CRUD operations work correctly
- [x] Proper session handling (flush, refresh)
- [x] Type hints work with generic types

---

## 3.2 Common Schemas

### Files to create/update:
- [x] `app/schemas/common.py` — Shared schemas (already existed from Phase 1)

### Checklist:
- [x] `PaginationParams` — Skip, limit parameters
- [x] `PaginatedResponse[T]` — Generic paginated response
- [x] `MessageResponse` — Simple message response
- [x] `ErrorResponse` — Error response format

### Validation:
- [x] Schemas serialize correctly
- [x] Pagination works with any model

---

## 3.3 Example Resource: Project Model

### Files to create:
- [x] `app/models/project.py` — Example resource model
- [x] `app/schemas/project.py` — Project schemas

### Checklist:
- [x] Project model with fields:
  - [x] `id` (UUID from BaseModel)
  - [x] `name` (required, max 255 chars)
  - [x] `description` (optional, max 2000 chars)
  - [x] `owner_id` (foreign key to User)
  - [x] `deleted_at` (from SoftDeleteMixin)
  - [x] `created_at`, `updated_at` (from BaseModel)
- [x] ProjectCreate schema
- [x] ProjectUpdate schema
- [x] ProjectRead schema
- [x] ProjectReadWithDeleted schema

### Validation:
- [x] Migration generates correctly
- [x] Foreign key relationship works

---

## 3.4 Project CRUD Service

### Files to create:
- [x] `app/business/project_service.py` — Project business logic

### Checklist:
- [x] Extend CRUDBase for Project
- [x] `get_active_by_owner(session, owner_id)` — Filter by owner, exclude deleted
- [x] `count_active_by_owner(session, owner_id)` — Count active for owner
- [x] `get_by_name_and_owner(session, name, owner_id)` — Find by name
- [x] `search_by_name(session, owner_id, query)` — Case-insensitive search
- [x] Singleton instance (`project_service`)

### Validation:
- [x] CRUD inheritance works
- [x] User-scoped queries work
- [x] Soft delete exclusion works

---

## 3.5 Project API Endpoints

### Files to create:
- [x] `app/api/v1/app/projects.py` — Project CRUD endpoints

### Checklist:
- [x] `GET /api/v1/app/projects` — List user's projects
  - [x] Pagination support (skip, limit)
  - [x] Search by name parameter
  - [x] Only return user's own active projects
- [x] `POST /api/v1/app/projects` — Create project
  - [x] Auto-assign current user as owner
  - [x] Return 201 Created
- [x] `GET /api/v1/app/projects/{id}` — Get single project
  - [x] Verify ownership
  - [x] Return 404 if not found or deleted
- [x] `PATCH /api/v1/app/projects/{id}` — Update project
  - [x] Verify ownership
  - [x] Partial updates
- [x] `DELETE /api/v1/app/projects/{id}` — Delete project
  - [x] Verify ownership
  - [x] Soft delete (sets deleted_at)
  - [x] Return 204 No Content

### Validation:
- [x] All CRUD operations work via API
- [x] Ownership checks prevent cross-user access
- [x] Proper HTTP status codes

---

## 3.6 Pagination Utilities

### Files to create:
- [x] `app/utils/pagination.py` — Pagination helpers

### Checklist:
- [x] `PaginationParams` — Skip/limit based pagination
- [x] `PageParams` — Page/page_size based pagination
- [x] `PaginatedResult[T]` — Result with metadata (has_more, page, total_pages)
- [x] `get_pagination_params()` — FastAPI dependency
- [x] `get_page_params()` — FastAPI dependency
- [x] `paginate_query(session, query, skip, limit)` — Execute with count
- [x] `paginate(session, query, params)` — Full pagination helper

### Validation:
- [x] Pagination works correctly
- [x] Total count is accurate
- [x] Uses Python 3.12 type parameters

---

## 3.7 Query Filters

### Files to create:
- [ ] `app/utils/filters.py` — Query filter helpers (deferred to Phase 4)

### Notes:
- Basic search implemented in project_service.py
- Full filter builder deferred for future enhancement

---

## 3.8 Router Integration

### Files to update:
- [x] `app/api/v1/router.py` — Include project routes

### Checklist:
- [x] Import projects module
- [x] Add to app_router with `/projects` prefix

### Validation:
- [x] Routes accessible at `/api/v1/app/projects`

---

## Phase 3 Completion Criteria

- [x] Generic CRUD base works with any model
- [x] Project model migrations applied
- [x] All project endpoints functional
- [x] Pagination returns correct results
- [x] Ownership checks prevent unauthorized access
- [x] OpenAPI docs show request/response schemas
- [x] All tests pass
- [x] Lint passes

---

## Files Created/Updated in Phase 3

| File | Purpose | Status |
|------|---------|--------|
| `app/business/crud_base.py` | Generic CRUD operations | ✅ Created |
| `app/models/project.py` | Project model with soft delete | ✅ Created |
| `app/schemas/project.py` | Project request/response schemas | ✅ Created |
| `app/business/project_service.py` | Project business logic | ✅ Created |
| `app/api/v1/app/projects.py` | Project CRUD endpoints | ✅ Created |
| `app/utils/pagination.py` | Pagination utilities | ✅ Created |
| `app/api/v1/router.py` | Router aggregation | ✅ Updated |
| `app/models/base.py` | Fixed sa_column_kwargs | ✅ Updated |
| `migrations/versions/*_add_project_model.py` | Project table migration | ✅ Created |

---

## Completion Date

**Completed:** 2026-01-10
