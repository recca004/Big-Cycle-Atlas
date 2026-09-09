# Decisions

## DEC-005: Alembic for Database Migrations
**Date:** 2026-09-07
**Status:** Adopted

**Decision:** Use Alembic for managing database schema migrations.

**Why:** As the project grows beyond a single-table prototype, manual schema management becomes error-prone and hard to coordinate. Alembic provides a robust, industry-standard way to track schema changes, support rollbacks, and ensure consistency across development environments.

**How to apply:** All schema changes must be implemented via Alembic migrations. Never modify the database schema directly. Use `uv run alembic upgrade head` to apply changes.
