# Newtonite Ops — Operational Work Management Platform

**Newtonite Ops** is a full-stack, enterprise-grade internal operational work management platform developed for the Newtonite Software Engineering Assessment.

It centralizes mission-critical operational work (payment investigations, incident triage, approval authorizations, customer escalations, and compliance reviews) into a unified platform with strict database persistence, server-side authorization, immutable activity logging, and verifiable concurrency correctness under high load.

---

## 🚀 Key Engineering & Security Highlights

1. **Atomic Approval Decisions & Race Condition Safety**:
   Approval decisions execute via conditional atomic database updates (`WHERE requires_approval IS TRUE AND approval_status = 'pending'`). Competing decisions from multiple approvers guarantee exactly 1 winner; losing concurrent requests receive an immediate `HTTP 409 Conflict` (`ALREADY_DECIDED`). Exactly one decision and activity event are persisted.
2. **Atomic Claiming with Concurrency Protection**:
   Claiming unassigned items uses conditional database updates (`WHERE assignee_id IS NULL`). Tested under 10 concurrent threads in PostgreSQL, proving that exactly 1 worker succeeds and 9 receive `HTTP 409 Conflict` (`ALREADY_CLAIMED`).
3. **Optimistic Concurrency Control (OCC)**:
   Every mutation requires the client to supply an expected integer `version`. Stale updates are rejected with `HTTP 409 Conflict` (`STALE_VERSION`), triggering a frontend `ConflictBanner` with a 1-click reload reconciliation workflow without losing unsaved changes.
4. **Database-Backed Idempotent Creation with Savepoints**:
   Creation requests support client idempotency keys validated against a PostgreSQL unique constraint (`uq_idempotency`) and SHA-256 canonical payload fingerprints. Nested transactions (`db.begin_nested()`) catch concurrent uniqueness conflicts without corrupting the outer database session.
5. **Hardened Authentication & CSRF Protection**:
   - **HttpOnly Cookies**: Session access tokens are stored strictly in `HttpOnly`, `SameSite="lax"`, path-scoped cookies (`access_token`). Tokens are never stored in `localStorage`.
   - **Double-Submit CSRF Protection**: State-changing requests (`POST`, `PATCH`, `PUT`, `DELETE`) require a matching `X-CSRF-Token` header paired with the server's `csrf_token` cookie, verified by constant-time comparison in custom FastAPI middleware.
   - **Origin & Referer Validation**: Middleware verifies cross-origin headers against configured CORS origins.
   - **Brute-Force Rate Limiting**: In-memory sliding-window limiter blocks rapid repeated failed login attempts (`HTTP 429 Too Many Requests`).
6. **Assignee and Team Membership Validation**:
   Creating, updating, reassigning, claiming, or moving a work item strictly enforces that the assignee exists, is active, and is an active member of the item's team.
7. **Resource-Level Authorization & Non-Enumeration**:
   Multi-tenant team scoping returns `HTTP 404 Not Found` for unauthorized cross-team resource lookups to prevent resource enumeration. Read-only `VIEWER` accounts are barred from mutations.
8. **Real Database Metrics**:
   The dashboard calculates real, scoped aggregates directly in PostgreSQL with zero mock or hardcoded statistics.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Psycopg 3 |
| **Database** | PostgreSQL 16 (Isolated containers on ports `5435` dev, `5436` test) |
| **Security** | Argon2id password hashing, PyJWT, HttpOnly SameSite cookies, CSRF middleware |
| **Frontend** | React 19, TypeScript (strict), Vite, Tailwind CSS, TanStack Query v5, React Router v7 |
| **Backend Testing** | Pytest, Pytest-Asyncio, HTTPX, ThreadPoolExecutor concurrency harness (34 tests) |
| **Frontend Testing** | Vitest, @testing-library/react, @testing-library/jest-dom, JSDOM (8 tests) |

---

## 📂 Project Structure

```
newtonite-ops/
├── docker-compose.yml          # PostgreSQL services (app: 5435, test: 5436)
├── ENGINEERING_DECISIONS.md    # Architecture rationale and correctness deep-dives
├── KNOWN_LIMITATIONS.md        # Explicitly scoped trade-offs and future roadmap
├── README.md                   # Setup guide and interview walkthrough
├── .env.example                # Safe development placeholder configuration
├── backend/
│   ├── alembic/                # Database migrations (initial schema & sequences)
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (auth, work_items, teams, dashboard)
│   │   ├── core/               # Security, dependencies, rate limiting, permissions, exceptions
│   │   ├── models/             # SQLAlchemy declarative models (WorkItem, ActivityLog, etc.)
│   │   ├── schemas/            # Pydantic request & response schemas
│   │   ├── services/           # Transactional business logic, OCC & concurrency enforcement
│   │   ├── config.py           # Typed settings with production secret validation
│   │   ├── database.py         # SQLAlchemy engine & session factories
│   │   ├── main.py             # FastAPI app with CSRF middleware & custom error handlers
│   │   └── seed.py             # Repeatable & idempotent demo database seeder
│   └── tests/                  # Pytest test suite (34 unit, integration & concurrency tests)
└── frontend/
    ├── src/
    │   ├── components/         # StatusBadge, PriorityBadge, ConflictBanner, Sidebar, Header
    │   ├── context/            # AuthContext with pure HttpOnly cookie authentication
    │   ├── lib/                # Typed API client with automatic X-CSRF-Token attachment
    │   ├── pages/              # Login, Dashboard, WorkItems, Detail, MyWork, Inbox, Approvals, Teams
    │   ├── test/               # Vitest test suites (auth, conflict banner, badges)
    │   └── types/              # Domain TypeScript interfaces
    └── tailwind.config.js      # Enterprise Linear/Jira design system tokens
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- **Docker & Docker Compose** (for PostgreSQL 16)
- **Python 3.12+**
- **Node.js 20+** and **npm**

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default ports used:
- Main Database: `localhost:5435`
- Test Database: `localhost:5436`
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173` (or `5174`)

### 3. Start Database Containers
```bash
docker compose up -d
```
Verify containers are healthy:
```bash
docker compose ps
```

### 4. Backend Setup & Seeding
```bash
cd backend

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Seed demo dataset
python -m app.seed

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at `http://localhost:8000`.
Interactive OpenAPI Swagger docs: `http://localhost:8000/api/docs`.

### 5. Frontend Setup
In a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Open `http://localhost:5173` (or `http://localhost:5174`) in your browser.

---

## 🧪 Automated Testing

### Backend Test Suite (Pytest)
The backend test suite runs against the real PostgreSQL test database (`newtonite_ops_test` on port `5436`), validating real constraints, sequences, transactions, and multi-threaded race conditions:

```bash
cd backend
source .venv/bin/activate
pytest -v
```

**Results: 34 tests passing in ~3.8 seconds**:
- `test_csrf.py`: CSRF rejection on missing token, rejection on token mismatch, untrusted origin rejection, success on valid token (4 tests)
- `test_rate_limiting.py`: Rate limiting enforcement on rapid failed logins (1 test)
- `test_concurrency_approval.py`: Multi-threaded competing approval decisions, exactly 1 winner, exactly 1 activity log, overwrite rejection, unauthorized rejection (3 tests)
- `test_concurrency_claiming.py`: 10-thread parallel claim race condition, single winner, subsequent claim rejection (3 tests)
- `test_assignee_validation.py`: Rejection of non-existent users, non-team members, inactive users, cross-team reassignments (4 tests)
- `test_auth.py`: Login, credentials verification, inactive account rejection, authenticated `/me` (5 tests)
- `test_authorization.py`: Multi-tenant 404 isolation, team scoping, viewer mutation prohibition, admin global access (5 tests)
- `test_idempotency.py`: Replay with identical payload, conflict on differing payload, distinct key generation (3 tests)
- `test_optimistic_concurrency.py`: Atomic version increment, stale version 409 rejection, status transition OCC (3 tests)
- `test_workflow_transitions.py`: State machine transitions, invalid jump rejections, approval gate enforcement (3 tests)

### Frontend Test Suite (Vitest)
Unit and integration tests using Vitest and React Testing Library:

```bash
cd frontend
npm test
```

**Results: 8 tests passing across 3 test suites**:
- `auth.test.tsx`: Authentication restoration on mount, login submission via cookie flow, logout state cleanup.
- `conflictBanner.test.tsx`: 409 Conflict banner rendering, unsaved edit preservation, reload button behavior.
- `badgesAndPermissions.test.tsx`: Status badges, priority badges, and human-readable work type labels.

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 👥 Demo Accounts & Permission Matrix

All demo accounts use the standard development password: `Password123!`

| User | Email | System Role | Team | Team Role | Permissions & Purpose |
|---|---|---|---|---|---|
| **Alex Admin** | `admin@newtonite.internal` | `ADMIN` | All Teams | Global Admin | Global system access; manage all teams and work items; cannot bypass OCC or audit trail. |
| **Sarah Chen** | `sarah.payments@newtonite.internal` | `USER` | Payments | `APPROVER` | Lead and approver in Payments; authorizes compliance refunds and investigations. |
| **Alex Rivera** | `alex.payments@newtonite.internal` | `USER` | Payments | `MEMBER` | Payments team contributor; can create, claim, update, comment, and resolve payments work. |
| **Marcus Vance** | `marcus.platform@newtonite.internal` | `USER` | Platform | `LEAD` | Team lead in Platform; manages infrastructure tasks, reassigns work within platform. |
| **Valerie Viewer** | `viewer@newtonite.internal` | `VIEWER` | Payments, Platform | `MEMBER` | Read-only audit access; can view dashboards and search queues, but barred from all mutations. |
| **Oscar Outsider** | `outsider@newtonite.internal` | `USER` | Customer Operations | `MEMBER` | Isolated to Customer Ops; attempting to access Payments or Platform returns `404 Not Found`. |

---

## 🎯 Evaluator Demo Walkthrough

Follow this 5-minute repeatable demonstration to review all key technical requirements:

1. **Sign In**:
   - Navigate to `http://localhost:5174/login`.
   - In development mode, click **Sarah Chen (Payments Approver)** to autofill credentials and click **Sign in**.
2. **Dashboard**:
   - Inspect real aggregate counts: Open Items, Critical Issues, Unassigned, Pending Approvals.
   - Click **Pending Approvals** card to automatically navigate to the filtered approvals queue.
3. **Assignee Membership Validation**:
   - Click **+ New Work Item**.
   - Select **Payments** team. Notice the Assignee dropdown strictly lists active members of the Payments team.
   - Attempting to pass an invalid UUID via API returns `400 VALIDATION_ERROR: User is not a member of team`.
4. **Idempotency in Action**:
   - Create a work item with title `"Duplicate charge investigation"`.
   - Inspect the response and note key `OPS-X`.
   - Resubmitting with the same `idempotency_key` returns the identical item without creating duplicate sequence numbers or activity logs.
5. **Optimistic Concurrency & Conflict Recovery**:
   - Open the created work item in two separate browser tabs (Tab A and Tab B).
   - In Tab A, change Priority from High to Critical and save (version increments from 1 to 2).
   - In Tab B, attempt to edit description and save with expected version 1.
   - Tab B receives `HTTP 409 STALE_VERSION`. The UI displays the amber `ConflictBanner` without discarding your unsaved edits.
   - Click **Reload Latest Version** to fetch version 2 and safely reapply changes.
6. **Atomic Approval Decision Concurrency**:
   - Navigate to an item requiring approval in `/approvals`.
   - Submitting a decision atomically updates `approval_status`, bumps version, and writes a single `APPROVAL_GRANTED` event.
   - Any second decision attempt returns `HTTP 409 ALREADY_DECIDED`.
7. **Cross-Team Isolation**:
   - Sign out and sign in as **Oscar Outsider** (`outsider@newtonite.internal`).
   - Attempt to access a Payments work item URL (e.g., `/work-items/<payments-id>`).
   - Notice the application returns `404 Not Found` (non-enumeration policy), completely isolating team data.
8. **Viewer Mutation Bar**:
   - Sign in as **Valerie Viewer** (`viewer@newtonite.internal`).
   - Notice action buttons (Claim, Edit, Change Status, Comment) are hidden. Direct API mutation attempts return `403 FORBIDDEN`.
