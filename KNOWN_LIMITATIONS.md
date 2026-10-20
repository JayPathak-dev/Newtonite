# Known Limitations & Future Roadmap: Newtonite Ops

This document outlines architectural boundaries, intentionally scoped constraints for the assessment, and future engineering milestones for **Newtonite Ops**.

---

## 1. Intentionally Scoped Limitations (Assessment Scope)

### 1.1 Real-Time Server Push (WebSockets / SSE)
- **Current State**: State synchronization relies on TanStack Query with cached server state, automatic invalidation on mutations, and periodic refetches.
- **Why Scoped**: Real-time WebSockets introduce stateful gateway requirements (connection heartbeats, reconnect loops, distributed pub/sub). For an operations management platform, deterministic OCC version checks and clean conflict resolution provide greater safety than eventual-consistency push updates.
- **Future Roadmap**: Implement Server-Sent Events (SSE) using PostgreSQL `LISTEN/NOTIFY` channels to broadcast work item assignment and status transitions without requiring an external message broker.

### 1.2 Multi-Stage Approval Workflows
- **Current State**: The system implements a complete single-stage approval gate: items flagged with `requires_approval=True` cannot progress to `RESOLVED` or `CLOSED` until an authorized team `APPROVER`, `LEAD`, or `ADMIN` submits an approval decision.
- **Why Scoped**: Complex multi-level approval hierarchies (e.g., Level 1 Financial Lead -> Level 2 VP of Risk) were avoided to maintain strict transactional simplicity and prevent brittle state machines during the assessment.
- **Future Roadmap**: Implement configurable approval rules per work type and monetary threshold (e.g. refunds > $50,000 requiring dual-signoff).

### 1.3 Binary File Attachments
- **Current State**: Work items support detailed markdown descriptions, structured JSON metadata, and rich comments. Binary file uploads (e.g., PDF bank statements, screenshots) are not stored.
- **Why Scoped**: File uploads require cloud object storage (S3 / GCS) or local multi-part upload handling with virus scanning and presigned URL pipelines, which add external cloud infrastructure dependencies.
- **Future Roadmap**: Add presigned S3 upload URLs with SHA-256 integrity verification and attachment metadata tables.

### 1.4 Offset Pagination vs Cursor Pagination
- **Current State**: The work item inventory uses indexed limit/offset pagination with sort determinism (`ORDER BY <sort_col>, id ASC`).
- **Why Scoped**: Limit/offset is ideal for page-based SaaS UIs with arbitrary sorting across columns (created date, updated date, priority, due date) and total page count visibility.
- **Future Roadmap**: For high-volume archival tables exceeding 10M rows, implement keyset (cursor-based) pagination (`WHERE (updated_at, id) < (:cursor_time, :cursor_id)`).

### 1.5 External SSO / OAuth2 / SAML
- **Current State**: Authentication uses Argon2id password hashing and signed JWT tokens with HttpOnly SameSite cookies.
- **Why Scoped**: Integrating Okta, Google Workspace, or Azure AD requires external cloud IdP directory tenants.
- **Future Roadmap**: Add OIDC (OpenID Connect) authentication flow with JIT (Just-In-Time) user provisioning and SCIM group syncing.

---

## 2. Production Hardening Roadmap

1. **Rate Limiting**: Add Redis-backed token bucket rate limiting on `/api/v1/auth/login` to thwart brute-force password guessing.
2. **Read Replica Routing**: For high reporting queries on the operational dashboard, configure SQLAlchemy read/write split engines routing analytics queries to a PostgreSQL read replica.
3. **Structured Audit Export**: Export append-only `activity_logs` periodically to an immutable cold storage archive (AWS S3 Glacier or BigQuery) for regulatory PCI-DSS / SOC2 compliance.
