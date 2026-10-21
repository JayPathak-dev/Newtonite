# Engineering Decisions & Architecture Specification: Newtonite Ops

This document provides a comprehensive technical review and rationale for the architectural patterns, database concurrency mechanisms, security controls, and trade-offs implemented in **Newtonite Ops**.

---

## 1. Modular Monolith and PostgreSQL as the Source of Truth

### The Problem
Newtonite Ops coordinates mission-critical operational work (payment investigations, incident triage, approval authorizations, customer escalations). Operations workflows require strict transactional invariants across state changes, activity logs, approval status, and idempotency guarantees.

### The Approach
A structured, modular monolith built with FastAPI, SQLAlchemy 2.0, and PostgreSQL 16. Services are organized with explicit separation of concerns:
- **API routers** handle HTTP serialization, query params, cookies, and status codes.
- **Service layer** (`work_item_service`, `activity_service`, `idempotency_service`, `dashboard_service`) encapsulates domain business rules and database transaction boundaries.
- **Permissions module** (`permissions.py`) provides centralized role-based access control (RBAC).
- **PostgreSQL 16** serves as the single transactional source of truth, enforcing foreign keys, sequences, row-level locks, and unique constraints.

### Why It Was Selected
- **ACID Invariants**: Operations requiring multi-table updates (e.g., status transition + activity log + version increment + idempotency record) commit or roll back in a single atomic database transaction.
- **Operational Simplicity**: Clean local setup with `docker-compose.yml` and unified testing without network partition risks.
- **Mechanical Service Extraction**: Clean internal service boundaries permit future extraction of specific modules (such as notifications or audit logging) without rewriting domain contracts.

### Alternatives Considered
- **Microservices Architecture**: Rejected due to distributed transaction complexities (2-phase commits/saga patterns) and split-brain risks under network partitions.
- **Document Store (MongoDB)**: Rejected because multi-document ACID transactions and foreign key integrity across teams, users, and audit logs are second-class compared to PostgreSQL.

### Trade-offs & Remaining Risks
- Scaling writes requires vertical scaling or table partitioning rather than sharding.
- All modules share database connection pools; unbounded queries could impact API response times without query limits.

---

## 2. Authentication, HttpOnly Cookies, and CSRF Protection

### The Problem
Browser applications storing access tokens in `localStorage` or `sessionStorage` are vulnerable to token theft via Cross-Site Scripting (XSS). Conversely, pure cookie-based authentication requires protection against Cross-Site Request Forgery (CSRF). Inconsistent authentication architectures (where both localStorage and cookies compete) cause session desynchronization.

### The Approach
- **Pure HttpOnly Cookie Authentication**:
  Upon successful login, the server sets an `access_token` cookie with `HttpOnly=True`, `SameSite="lax"`, `path="/"`, and `secure=True` in production environments. Tokens are never exposed to client-side JavaScript.
- **Double-Submit CSRF Protection**:
  On login or session fetch, the server sets a readable `csrf_token` cookie (`HttpOnly=False`, `SameSite="lax"`). For state-changing operations (`POST`, `PATCH`, `PUT`, `DELETE`), the client API layer extracts this token and transmits it via the `X-CSRF-Token` HTTP header.
- **FastAPI CSRF & Origin Middleware**:
  An HTTP middleware checks state-changing requests when an auth cookie is present. It verifies:
  1. The `Origin` header matches configured CORS origins.
  2. The `X-CSRF-Token` header matches the `csrf_token` cookie using constant-time comparison (`hmac.compare_digest`).
  Requests failing validation receive `HTTP 403 Forbidden` (`CSRF_ERROR`).
- **Login Abuse Protection**:
  An in-memory sliding-window rate limiter tracks login attempts per client IP address. Exceeding 15 attempts in a 60-second window yields `HTTP 429 Too Many Requests` (`RATE_LIMIT_EXCEEDED`).
- **Resource Disclosure Policy**:
  Unauthorized cross-team resource lookups return `HTTP 404 Not Found` rather than `HTTP 403 Forbidden`, preventing resource enumeration attacks.

### Why It Was Selected
This adheres to OWASP guidelines for secure session management in single-page applications without requiring heavyweight session backends like Redis.

### Alternatives Considered
- **Synchronizer Token Pattern with Server-Side Session Store**: Requires shared cache infrastructure (Redis) to store server-side CSRF tokens, adding operational overhead for placement assessment.
- **Bearer Tokens in LocalStorage**: Vulnerable to XSS token exfiltration; explicitly prohibited.

### Trade-offs & Remaining Risks
- The in-memory login rate limiter is node-local; in a multi-instance production deployment behind a load balancer, an external Redis rate limiter would be required.

---

## 3. Atomic Assignment and Approval Decisions (Race-Condition Safety)

### The Problem
When work items are unassigned, or when high-value items require approval signoff, two concurrent requests may read the item in `PENDING` state and attempt conflicting updates. A naive `SELECT` followed by an `UPDATE` allows both requests to pass validation, silently overwriting each other and emitting duplicate activity events.

### The Approach
1. **Atomic Conditional Updates**:
   For approval decisions:
   ```sql
   UPDATE work_items
   SET approval_status = :new_status,
       version = work_items.version + 1,
       updated_at = :now
   WHERE id = :work_item_id
     AND requires_approval IS TRUE
     AND approval_status = 'pending'
   RETURNING version;
   ```
   For work item claiming:
   ```sql
   UPDATE work_items
   SET assignee_id = :actor_id,
       version = work_items.version + 1,
       updated_at = :now
   WHERE id = :work_item_id
     AND assignee_id IS NULL
   RETURNING version, assignee_id;
   ```
2. **Row Count Verification**:
   If another transaction commits first, zero rows match the condition (`updated is None`).
3. **Transaction Rollback & Conflict Resolution**:
   When zero rows are updated, the service immediately rolls back the session, re-queries the current state to check permissions, and returns `HTTP 409 Conflict` (`ALREADY_DECIDED` or `ALREADY_CLAIMED`).
4. **Single Transaction Boundary**:
   The work item state update, `ApprovalRecord` insertion, and `ActivityLog` creation are all committed in the exact same transaction. If any part fails, all changes roll back atomically.

### Why It Was Selected
Database-level conditional updates eliminate race conditions without requiring table-level locks or distributed mutexes.

### Alternatives Considered
- **Pessimistic Locking (`SELECT FOR UPDATE`)**: Effective, but holds locks across network roundtrips and increases the risk of deadlocks under high concurrency.
- **Application-Level Mutex (e.g. `threading.Lock`)**: Ineffective across multi-process or multi-worker deployments.

### Trade-offs & Remaining Risks
- The losing client must handle the 409 Conflict gracefully in the UI.

---

## 4. Optimistic Concurrency Control (OCC)

### The Problem
In multi-user collaborative operations, stale overwrites ("lost updates") cause data corruption. If User A opens version 1 of a ticket, and User B edits it to version 2, User A's subsequent submission would silently overwrite User B's changes unless versioning is checked.

### The Approach
- Every `work_items` record contains an integer `version` column starting at 1.
- All mutating requests (`PATCH /work-items/{id}`, `POST /transition`, `POST /assign`) require the client to supply the expected `version`.
- Updates execute conditionally:
  ```sql
  UPDATE work_items
  SET title = :title,
      version = work_items.version + 1,
      updated_at = :now
  WHERE id = :work_item_id AND version = :expected_version
  RETURNING version;
  ```
- If 0 rows match, the transaction rolls back and returns `HTTP 409 Conflict` (`STALE_VERSION`) including the current version in details.
- The frontend preserves user edits and displays a `ConflictBanner` offering a reload action.

### Why It Was Selected
OCC is the industry standard for collaborative web applications with low contention, avoiding unnecessary locking while guaranteeing zero lost updates.

### Alternatives Considered
- **Last-Write-Wins (LWW)**: Unacceptable for operational work; leads to silent data loss.
- **WebSocket Real-Time Locks**: Adds operational fragility, stateful connection handling, and reconnect synchronization complexity.

---

## 5. Server-Enforced Idempotent Creation with Nested Savepoints

### The Problem
Network timeouts or impatient double-clicks can cause clients to submit creation requests multiple times. Without idempotency, duplicate tickets and sequence keys are generated. Furthermore, in SQLAlchemy, if a concurrent request triggers an `IntegrityError` during flush/commit, a naive rollback can corrupt or invalidate the session.

### The Approach
1. **Client Key Scoping**:
   Clients supply an `Idempotency-Key` or `idempotency_key` payload attribute.
2. **Deterministic Payload Fingerprinting**:
   The server computes a canonical SHA-256 hash of the normalized request payload.
3. **Database Uniqueness Constraint**:
   Persisted in `idempotency_records` with `UniqueConstraint("idempotency_key", "actor_id", "operation")`.
4. **Nested Savepoints (`db.begin_nested()`)**:
   When recording the idempotency record, the service wraps the flush in a savepoint:
   ```python
   try:
       with db.begin_nested():
           record_idempotency_result(db, idempotency_key, actor.id, "create_work_item", request_data, item.id)
           db.flush()
   except IntegrityError:
       db.rollback()
       # Re-query winning idempotency record and return original created item
   ```
   If a duplicate request commits concurrently, the savepoint catches the constraint violation without invalidating the outer SQLAlchemy session.
5. **Replay Validation**:
   - Matching fingerprint: Returns original created resource (`HTTP 200/201`).
   - Different fingerprint: Rejects with `HTTP 409 Conflict` (`IDEMPOTENCY_CONFLICT`).

---

## 6. Transactionally Consistent Activity History (Audit Trail)

### The Problem
Audit trails are useless if they become desynchronized from the actual database state (e.g. an activity record exists for an operation that failed to persist, or an update succeeded but the audit log failed).

### The Approach
- **Append-Only Semantics**:
  Activity logs are strictly append-only records with server-generated timestamps (`TIMESTAMPTZ`) and foreign keys to `work_items` and `users`.
- **Atomic Transaction Enclosure**:
  Every business mutation commits its corresponding activity event within the same database transaction.
- **Server-Derived Context**:
  Actor IDs, previous values, and new values are extracted directly from authenticated server session state and verified database models, never trusted from client payloads.

---

## 7. Search, Pagination, Indexing, and Performance

### The Problem
In-memory filtering and unpaginated database queries degrade linearly as queues grow, leading to N+1 query bottlenecks and excessive database CPU utilization.

### The Approach
- **Deterministic Server-Side Pagination**:
  Pagination (`offset`, `limit`) and sorting validate against `VALID_SORT_FIELDS` with deterministic secondary sorting by `id ASC`.
- **Database Indexing**:
  B-Tree indexes applied to:
  - `work_items (team_id, status)` for team queue filtering.
  - `work_items (assignee_id, status)` for "My Work" queries.
  - `work_items (due_at)` for overdue calculations.
  - `work_items (created_at)` and `work_items (updated_at)` for timeline ordering.
  - Foreign keys: `team_memberships.user_id`, `team_memberships.team_id`, `comments.work_item_id`.
  - Unique constraint on `(idempotency_key, actor_id, operation)`.
- **Database Aggregates for Dashboard**:
  Dashboard summaries execute SQL aggregates (`COUNT`, `GROUP BY`) rather than fetching full ORM object graphs into application memory.
- **PostgreSQL Sequences for Human-Readable Keys**:
  Human-friendly keys (`OPS-1`, `OPS-2`) are issued via an atomic database sequence (`work_item_key_seq`), eliminating collision races.

---

## 8. Deliberate Scope Limitations

To maintain code clarity and project focus within the assessment constraints:
1. **No External Message Broker**: Background scheduling and async tasks use standard FastAPI lifecycle patterns rather than Celery or RabbitMQ.
2. **In-Memory Rate Limiting**: The sliding-window rate limiter is in-memory rather than Redis-backed.
3. **No Distributed File Storage**: File attachments and binary media are modeled as external links rather than integrating S3/GCS.
4. **Focused Team Roles**: Roles are modeled as System Roles (`ADMIN`, `USER`, `VIEWER`) and Team Roles (`MEMBER`, `LEAD`, `APPROVER`) rather than arbitrary dynamic permission graphs.
