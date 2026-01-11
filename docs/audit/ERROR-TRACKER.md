# Error & Issue Tracker

**Project:** OmniStack Backend Boilerplate
**Purpose:** Track errors, bugs, and issues encountered during development

---

## Quick Stats

| Metric | Count |
|--------|-------|
| 🔴 Open Issues | 0 |
| 🟡 In Progress | 0 |
| 🟢 Resolved | 0 |
| 🔵 Won't Fix | 0 |
| **Total** | **0** |

---

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| 🔴 **Critical** | App crashes, data loss, security vulnerability | Immediate |
| 🟠 **High** | Feature broken, blocking development | Same day |
| 🟡 **Medium** | Feature degraded, workaround exists | Within 3 days |
| 🟢 **Low** | Minor issue, cosmetic, nice-to-have fix | When convenient |

---

## Open Issues

### Critical 🔴

<!-- No critical issues -->
*None*

---

### High 🟠

<!-- No high priority issues -->
*None*

---

### Medium 🟡

<!-- No medium priority issues -->
*None*

---

### Low 🟢

<!-- No low priority issues -->
*None*

---

## Issue Template

When adding a new issue, use this template:

```markdown
### [ISSUE-XXX] Issue Title

**Phase:** Phase X
**Severity:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low
**Status:** 🔴 Open | 🟡 In Progress | 🟢 Resolved | 🔵 Won't Fix
**Date Found:** YYYY-MM-DD
**Date Resolved:** YYYY-MM-DD (if resolved)

**Description:**
Brief description of the issue.

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen.

**Actual Behavior:**
What actually happens.

**Error Message/Stack Trace:**
```
Paste error here
```

**Environment:**
- Python version:
- OS:
- Relevant dependencies:

**Root Cause:**
(Fill when investigating)

**Resolution:**
(Fill when resolved)

**Files Affected:**
- `path/to/file.py`

**Related Issues:**
- ISSUE-XXX
```

---

## Resolved Issues

### Phase 1

<!-- Add resolved issues here as development progresses -->
*None yet*

---

### Phase 2

*None yet*

---

### Phase 3

*None yet*

---

### Phase 4

*None yet*

---

### Phase 5

*None yet*

---

### Phase 6

*None yet*

---

### Phase 7

*None yet*

---

### Phase 8

*None yet*

---

### Phase 9

*None yet*

---

### Phase 10

*None yet*

---

### Phase 11

*None yet*

---

### Phase 12

*None yet*

---

## Common Issues Reference

Quick reference for common issues and their solutions:

### Database Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | DB not running | `make up` to start Docker |
| Migration conflict | Multiple heads | `alembic merge heads` |
| asyncpg not found | Wrong driver | Check DATABASE_URL has `+asyncpg` |

### Auth Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 on valid token | JWKS cache stale | Restart server or clear cache |
| JWT decode error | Wrong algorithm | Check AUTH_PROVIDER setting |
| Missing 'sub' claim | Token format | Verify token structure |

### Redis Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Redis not running | `make up` or check REDIS_URL |
| Rate limit not working | Redis unavailable | Falls back to memory (expected) |

### Import Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| ModuleNotFoundError | Not installed | `pip install -e .` |
| Circular import | Wrong import order | Use TYPE_CHECKING or lazy import |

---

## Issue Statistics by Phase

| Phase | Total | Critical | High | Medium | Low | Resolved |
|-------|-------|----------|------|--------|-----|----------|
| Phase 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 11 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase 12 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **0** | **0** | **0** | **0** | **0** | **0** |

---

## Error Patterns to Watch

### Performance Issues
- [ ] Slow database queries (>100ms)
- [ ] Memory leaks in long-running processes
- [ ] N+1 query problems
- [ ] Unoptimized pagination

### Security Issues
- [ ] SQL injection vulnerabilities
- [ ] XSS in responses
- [ ] Missing auth on endpoints
- [ ] Secrets in logs

### Reliability Issues
- [ ] Unhandled exceptions
- [ ] Missing error handling for external services
- [ ] Race conditions in async code
- [ ] Deadlocks in database transactions

---

*Last Updated: 2026-01-10*
