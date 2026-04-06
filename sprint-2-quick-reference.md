# Sprint 2 Quick Reference Card
## Purple Team GPT - Production Readiness

**Sprint Dates:** April 15-28, 2026

---

## Critical Path (Must Complete)

```
DB-001 (12h) → DB-002 (16h) → TEST-005 (12h) = 40h minimum
```

## Priority Assignments

| Priority | Tasks | Must Complete |
|----------|-------|---------------|
| **P0** | DB-001, DB-002, SEC-007, SEC-008 | Yes |
| **P1** | DB-003, FE-001, FE-002, TEST-003, TEST-004, TEST-005 | Yes |
| **P2** | AI-001, AI-002, DOC-003, DOC-004 | If time permits |

## Integration Checkpoints

| Checkpoint | Date | Owner | Key Deliverables |
|------------|------|-------|------------------|
| CP1 | Day 3 (Apr 17) | dev-1 | DB schema, HTTPS config, Error boundaries |
| CP2 | Day 5 (Apr 21) | dev-2 | Session persistence, Secrets management |
| CP3 | Day 7 (Apr 23) | dev-4 | Redis integration, 80% test coverage |
| CP4 | Day 9 (Apr 25) | dev-5 | E2E tests passing, All P0 complete |

## Files to Create (Priority Order)

1. `src/purple_team_gpt/models/database.py` - DB connection
2. `alembic/` - Migration setup
3. `src/purple_team_gpt/services/session_repository.py` - Persistence layer
4. `src/purple_team_gpt/services/cache.py` - Redis cache
5. `src/frontend/src/components/ErrorBoundary.tsx` - Error handling
6. `e2e/` - Playwright tests

## Database Migration Commands

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Test Commands

```bash
# Backend unit tests with coverage
pytest tests/unit -v --cov=src/purple_team_gpt --cov-report=html

# Integration tests
pytest tests/integration -v

# Frontend tests
cd src/frontend && npm test -- --coverage

# E2E tests
npx playwright test
```

## Risk Escalation

| Risk | Trigger | Action |
|------|---------|--------|
| DB migration issues | Test failures | Escalate to dev-1, prepare rollback |
| Coverage < 80% | Day 7 checkpoint | Focus on critical paths only |
| E2E flakiness | >2 CI failures | Reduce test scope, add retries |

## Success Criteria

- [ ] All P0 tasks complete
- [ ] Test coverage >= 80%
- [ ] Sessions persist across restarts
- [ ] HTTPS working in production
- [ ] E2E tests passing
- [ ] No new security vulnerabilities

---

**Questions?** See full coordination document: `sprint-2-coordination.md`