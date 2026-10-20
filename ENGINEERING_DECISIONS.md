# Engineering Decisions & Architecture Trade-offs: Newtonite Ops

This document articulates the architecture, data modeling, concurrency designs, and trade-offs implemented in **Newtonite Ops**, built for the Newtonite Software Engineering Assessment.

---

## 1. Architectural Philosophy: The Modular Monolith

Newtonite Ops coordinates mission-critical operational work (payment investigations, incident triage, approval authorizations, customer escalations).

### Decision
We rejected microservices, distributed queues (Kafka/Celery), and external caching layers (Redis) in favor of a **Modular Monolith backed by PostgreSQL as the authoritative single source of truth**.

### Rationale
- **Atomic Correctness**: Operational work requires strict transactional invariants. In a distributed microservices setup, recording an activity log, updating a work item, verifying optimistic concurrency, and persisting idempotency fingerprints requires complex 2-phase commits or saga orchestrators. In PostgreSQL, all four operations execute inside a single ACID database transaction.
- **Cognitive & Operational Simplicity**: The entire application can be spun up in 60 seconds with `docker compose up -d` and single-process backend/frontend servers, with zero distributed synchronization latency or split-brain risks.
- **Domain Boundaries**: Clean separation between routes, schemas, services, and models ensures that if a service (e.g., audit logging or notifications) ever requires isolation, extraction is mechanical rather than architectural.

---

## 2. Core Correctness Feature 1: Atomic Claiming & Race Condition Safety

### Problem
When an unassigned item appears in an operations queue, multiple agents simultaneously click "Claim Item" or "Assign to Me". A naive `SELECT -> UPDATE` sequence allows race conditions where two users both believe they won, overwriting each other and emitting duplicate activity events.

### Implemented Solution
We utilize a conditional atomic update directly at the database engine level:

```sql
UPDATE work_items
SET assignee_id = :actor_id,
    version = work_items.version + 1,
    updated_at = :now
WHERE id = :work_item_id
  AND assignee_id IS NULL
RETURNING version, assignee_id;
```

### Invariants Guaranteed
1. **Row Count Verification**: If another worker's transaction commits first, `assignee_id IS NULL` evaluates to `FALSE`. The database updates 0 rows and returns empty.
2. **Deterministic Conflict Handling**: The server rolls back the transaction, inspects the current owner, and returns `HTTP 409 Conflict` with error code `ALREADY_CLAIMED` and the winning user's name.
3. **No Phantom Activity**: The `WORK_ITEM_CLAIMED` activity log is inserted in the *exact same transaction* as the successful row update. If the claim fails, the activity log rolls back atomically.
4. **Verified by Concurrency Tests**: Tested under 10 concurrent threads in `tests/test_concurrency_claiming.py`, proving that exactly 1 worker succeeds and 9 receive HTTP 409.

---

## 3. Core Correctness Feature 2: Optimistic Concurrency Control (OCC)

### Problem
In operational work, stale overwrites ("lost updates") cause severe bugs: Employee A opens version 1 of a payment issue to add investigation notes. Simultaneously, Employee B escalates the priority to CRITICAL. When Employee A submits, their form submits based on version 1, potentially reverting Employee B's priority change.

### Implemented Solution
Every `work_item` row maintains an integer `version` column (starting at 1). Every state-changing API request (`PATCH`, `/transition`, `/assign`) requires the client to supply the `version` they read:

```sql
UPDATE work_items
SET title = :new_title,
    priority = :new_priority,
    version = work_items.version + 1,
    updated_at = :now
WHERE id = :work_item_id
  AND version = :expected_version
RETURNING version;
```

### Invariants Guaranteed
1. If the database row version was already bumped by another transaction, zero rows match the condition.
2. The server rolls back, fetches the fresh current version, and responds with `HTTP 409 Conflict`:
   ```json
   {
     "error": {
       "code": "STALE_VERSION",
       "message": "This work item has changed since you opened it. Please refresh and try again.",
       "details": { "current_version": 4 }
     }
   }
   ```
3. **Frontend Recovery Banner**: When the React UI encounters a 409, it does not discard the user's edits. It presents a `ConflictBanner` explaining that another team member updated the item, with a 1-click `Reload Latest Version` button.

---

## 4. Core Correctness Feature 3: Server-Enforced Idempotent Creation

### Problem
Network hiccups, proxy timeouts, or double-clicks on "Create Work Item" can cause clients to retry creation requests. Without idempotency, duplicate tickets (and duplicate sequence IDs like NEW-10 and NEW-11) flood the queue.

### Implemented Solution
Clients generate a client-side UUID (`idempotency_key`) for each logical creation flow. The server records this in a dedicated `idempotency_records` table:

```sql
CREATE TABLE idempotency_records (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    result_resource_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_idempotency UNIQUE (idempotency_key, actor_id, operation)
);
```

### Invariants Guaranteed
1. **Database Uniqueness**: Uniqueness is enforced by a database constraint (`uq_idempotency`), preventing in-memory cache race conditions.
2. **Cryptographic Fingerprint Match**: The request payload is canonicalized and hashed using SHA-256 (`request_fingerprint`). If a retry arrives with the exact same key and matching fingerprint, the original created resource is returned with `HTTP 200/201`.
3. **Key Replay Protection**: If a client attempts to reuse an existing idempotency key with a *different* payload, the server rejects it with `HTTP 409 Conflict` (`IDEMPOTENCY_CONFLICT`).

---

## 5. Security & Authorization Model

### Multi-Tenant & Team Isolation
- **System Roles**: `ADMIN`, `USER`, `VIEWER`.
- **Team Roles**: `MEMBER`, `LEAD`, `APPROVER`.
- **Non-Enumeration Policy**: If an authenticated user from Customer Operations tries to read or modify a Payments team work item by its UUID, the API returns `HTTP 404 Not Found` rather than `403 Forbidden`, preventing resource enumeration attacks.
- **Viewer Restrictions**: `VIEWER` accounts can read items and search operational dashboards, but all state mutations (`POST /work-items`, `PATCH`, `claim`, `assign`, `comments`, `approval`) are rejected with `HTTP 403 Forbidden`.

### Password Hashing & JWT Authentication
- **Argon2id**: Passwords hashed using standard Argon2id parameters (`time_cost=2`, `memory_cost=65536`, `parallelism=2`). Plaintext passwords are never persisted.
- **Dual Session Mechanism**: Supports both HttpOnly SameSite cookies for browser security against XSS, and `Authorization: Bearer <token>` for automated API testing and CLI access.

---

## 6. Key Sequences: Human-Readable Keys

Instead of exposing opaque UUIDs like `f47ac10b-58cc-4372-a567-0e02b2c3d479` in daily communications, items use human-friendly keys like `NEW-1`, `NEW-2`:
- Implemented using a dedicated PostgreSQL sequence (`work_item_key_seq`).
- Evaluated atomically via `SELECT nextval('work_item_key_seq')`.
- Safe under high concurrent creation load with zero key collisions.
