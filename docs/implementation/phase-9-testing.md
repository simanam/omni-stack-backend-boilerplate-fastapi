# Phase 9: Testing

**Duration:** Quality assurance phase
**Goal:** Comprehensive test coverage with unit, integration, and e2e tests

**Prerequisites:** Phase 1-8 completed

---

## 9.1 Test Configuration

### Files to create:
- [ ] `tests/__init__.py`
- [ ] `tests/conftest.py` — Pytest fixtures

### Checklist:
- [ ] Test database setup (SQLite for speed)
- [ ] Event loop fixture
- [ ] Async engine fixture
- [ ] Session fixture with rollback
- [ ] HTTP client fixture
- [ ] Auth mocking fixtures
- [ ] Factory imports

### Validation:
- [ ] `pytest` runs without errors

---

## 9.2 Test Factories

### Files to create:
- [ ] `tests/factories/__init__.py`
- [ ] `tests/factories/user_factory.py`
- [ ] `tests/factories/project_factory.py`

### Checklist:
- [ ] `UserFactory` — Create test users
- [ ] `ProjectFactory` — Create test projects
- [ ] Factory inheritance for variations
- [ ] Async-compatible factories
- [ ] Random but reproducible data (Faker)

### Validation:
- [ ] Factories create valid objects

---

## 9.3 Unit Tests — Core

### Files to create:
- [ ] `tests/unit/__init__.py`
- [ ] `tests/unit/test_config.py`
- [ ] `tests/unit/test_security.py`
- [ ] `tests/unit/test_exceptions.py`

### Test Cases:
- [ ] Config loads from env vars
- [ ] Config validates required fields
- [ ] Config computed properties work
- [ ] JWT verification works
- [ ] Invalid token rejected
- [ ] Expired token rejected
- [ ] Custom exceptions have correct codes

### Validation:
- [ ] All unit tests pass

---

## 9.4 Unit Tests — CRUD

### Files to create:
- [ ] `tests/unit/test_crud_base.py`

### Test Cases:
- [ ] Create record
- [ ] Get by ID
- [ ] Get by field
- [ ] Get multiple with pagination
- [ ] Update record
- [ ] Delete record
- [ ] Soft delete record
- [ ] Count records

### Validation:
- [ ] All CRUD operations tested

---

## 9.5 Unit Tests — Services

### Files to create:
- [ ] `tests/unit/test_email_service.py`
- [ ] `tests/unit/test_storage_service.py`
- [ ] `tests/unit/test_ai_service.py`

### Test Cases:
- [ ] Email service interface
- [ ] Mock email sending
- [ ] Storage service interface
- [ ] Mock file upload/download
- [ ] AI service interface
- [ ] Mock completions

### Validation:
- [ ] Services tested with mocks

---

## 9.6 Integration Tests — API

### Files to create:
- [ ] `tests/integration/__init__.py`
- [ ] `tests/integration/test_health.py`
- [ ] `tests/integration/test_auth.py`
- [ ] `tests/integration/test_users.py`
- [ ] `tests/integration/test_projects.py`

### Test Cases:
- [ ] Health check returns 200
- [ ] Readiness check shows components
- [ ] Protected routes require auth
- [ ] Invalid token returns 401
- [ ] User profile endpoint works
- [ ] Project CRUD works
- [ ] Ownership checks enforced
- [ ] Pagination works

### Validation:
- [ ] API endpoints tested

---

## 9.7 Integration Tests — Database

### Files to create:
- [ ] `tests/integration/test_database.py`

### Test Cases:
- [ ] Database connection works
- [ ] Transactions commit
- [ ] Transactions rollback on error
- [ ] Migrations apply cleanly
- [ ] Foreign keys enforced

### Validation:
- [ ] Database operations tested

---

## 9.8 Integration Tests — External Services

### Files to create:
- [ ] `tests/integration/test_webhooks.py`
- [ ] `tests/integration/test_stripe.py`

### Test Cases:
- [ ] Webhook signature verification
- [ ] Webhook event processing
- [ ] Stripe checkout session creation
- [ ] Stripe webhook handling
- [ ] Idempotency checks

### Validation:
- [ ] External service integration tested

---

## 9.9 E2E Tests

### Files to create:
- [ ] `tests/e2e/__init__.py`
- [ ] `tests/e2e/test_user_flow.py`
- [ ] `tests/e2e/test_subscription_flow.py`

### Test Cases:
- [ ] Complete user signup flow
- [ ] User creates project
- [ ] User updates project
- [ ] User deletes project
- [ ] Subscription checkout flow
- [ ] Subscription cancellation flow

### Validation:
- [ ] Full user journeys tested

---

## 9.10 Test Utilities

### Files to create:
- [ ] `tests/utils.py`

### Checklist:
- [ ] `create_auth_headers(user_id)` — Generate test auth
- [ ] `mock_jwt_verification()` — Mock auth dependency
- [ ] `create_test_user(session)` — Quick user creation
- [ ] `async_mock()` — Async mock helper

### Validation:
- [ ] Utilities work correctly

---

## 9.11 Coverage Configuration

### Files to update:
- [ ] `pyproject.toml` — Coverage settings

### Checklist:
- [ ] Coverage threshold (80%)
- [ ] Exclude patterns (tests, migrations)
- [ ] Branch coverage
- [ ] Report formats (terminal, HTML, XML)

### Validation:
- [ ] Coverage reports generated

---

## 9.12 CI Test Pipeline

### Files to create:
- [ ] `.github/workflows/test.yml`

### Checklist:
- [ ] Run on push and PR
- [ ] Set up Python
- [ ] Install dependencies
- [ ] Run linting
- [ ] Run tests with coverage
- [ ] Upload coverage report
- [ ] Fail on coverage drop

### Validation:
- [ ] CI pipeline runs on GitHub

---

## 9.13 Test Documentation

### Files to create:
- [ ] `tests/README.md`

### Checklist:
- [ ] How to run tests
- [ ] Test structure explanation
- [ ] Adding new tests guide
- [ ] Mocking guide
- [ ] Coverage requirements

---

## Phase 9 Completion Criteria

- [ ] `pytest` runs all tests
- [ ] Unit test coverage > 80%
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] CI pipeline works
- [ ] Coverage reports generated

---

## Files Created in Phase 9

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Test fixtures |
| `tests/factories/*.py` | Data factories |
| `tests/unit/*.py` | Unit tests |
| `tests/integration/*.py` | Integration tests |
| `tests/e2e/*.py` | E2E tests |
| `tests/utils.py` | Test utilities |
| `.github/workflows/test.yml` | CI pipeline |
| `tests/README.md` | Test docs |
