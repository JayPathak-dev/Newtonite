# Newtonite Ops — Operational Work Management Platform

**Newtonite Ops** is a full-stack, enterprise-grade internal operational work management platform developed for the Newtonite Software Engineering Assessment.

It centralizes mission-critical operational work (payment investigations, incident triage, approval authorizations, customer escalations, and compliance reviews) into a unified platform with strict database persistence, server-side authorization, immutable activity logging, and verifiable concurrency correctness.

---

## 🚀 Key Engineering Highlights

1. **Atomic Claiming with Concurrency Protection**: High-concurrency claiming uses conditional row-level database updates (`WHERE assignee_id IS NULL`). Concurrent claims allow exactly 1 winner and return `HTTP 409 Conflict` to losing requests, guaranteed by automated multi-threaded stress tests.
2. **Optimistic Concurrency Control (OCC)**: Every state mutation requires an expected integer `version`. Stale updates from concurrent browser tabs are rejected with `HTTP 409 STALE_VERSION`, accompanied by a frontend conflict resolution banner with a 1-click reload workflow.
3. **Idempotent Creation**: Double-clicks and network retry attempts reuse client-generated idempotency keys verified against a database constraint (`uq_idempotency`) and SHA-256 request payload fingerprints.
4. **Server-Side Authorization & Isolation**: Multi-tenant team scoping returns `HTTP 404 Not Found` for unauthorized cross-team resource lookups to prevent resource enumeration. Read-only `VIEWER` accounts are strictly barred from mutations.
5. **Real Database Metrics**: The dashboard calculates scoped aggregates directly in PostgreSQL with no hardcoded or mock statistics.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Psycopg 3 |
| **Database** | PostgreSQL 16 (Dockerized on non-standard ports to prevent host conflicts) |
| **Security** | Argon2id password hashing, PyJWT, HttpOnly SameSite cookies |
| **Frontend** | React 19, TypeScript (strict), Vite, Tailwind CSS, TanStack Query v5, React Router v7 |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX, ThreadPoolExecutor concurrency harness |

---

## 📂 Project Structure

```
newtonite-ops/
├── docker-compose.yml          # PostgreSQL services (app: 5435, test: 5436)
├── ENGINEERING_DECISIONS.md    # Architecture rationale and correctness deep-dives
├── KNOWN_LIMITATIONS.md        # Explicitly scoped trade-offs and future roadmap
├── README.md                   # Setup guide and interview walkthrough
├── backend/
│   ├── alembic/                # Database migrations (initial schema & sequences)
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (auth, work_items, teams, dashboard)
│   │   ├── core/               # Security, dependencies, permissions, exceptions
│   │   ├── models/             # SQLAlchemy declarative models (WorkItem, ActivityLog, etc.)
│   │   ├── schemas/            # Pydantic request & response schemas
│   │   ├── services/           # Transactional business logic & OCC enforcement
│   │   ├── config.py           # Typed settings with pydantic-settings
│   │   ├── database.py         # SQLAlchemy engine & session factories
│   │   ├── main.py             # FastAPI app with CORS & custom exception handlers
│   │   └── seed.py             # Repeatable & idempotent demo database seeder
│   └── tests/                  # Pytest test suite (22 unit, integration & concurrency tests)
└── frontend/
    ├── src/
    │   ├── components/         # StatusBadge, PriorityBadge, ConflictBanner, Sidebar, Header
    │   ├── context/            # AuthContext with 1-click demo role switching
    │   ├── lib/                # Typed API client with token & cookie credentials
    │   ├── pages/              # Login, Dashboard, WorkItems, Detail, MyWork, Inbox, Approvals, Teams
    │   ├── types/              # Domain TypeScript interfaces
    │   └── App.tsx             # Protected routes & QueryClient setup
    └── tailwind.config.js      # Enterprise Linear/Jira design system tokens
```

---

## ⚡ Quick Start Guide

### 1. Start the Database Containers
Newtonite Ops uses isolated Docker PostgreSQL containers on ports `5435` (dev) and `5436` (test) to prevent conflicts with local Postgres instances:

```bash
docker compose up -d
```

### 2. Backend Setup & Seeding

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate

# Apply database migrations
alembic upgrade head

# Seed initial demo data (teams, users, work items, activities)
python -m app.seed

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend API will be live at `http://localhost:8000` (OpenAPI Swagger docs at `http://localhost:8000/api/docs`).

### 3. Frontend Setup

In a new terminal window:

```bash
cd frontend

# Install dependencies (if not already installed)
npm install

# Start Vite dev server
npm run dev
```
Open `http://localhost:5174` (or `http://localhost:5173`) in your browser.

---

## 🔑 Demo Credentials (Password: `Password123!`)

Newtonite Ops includes pre-configured personas to demonstrate authorization boundaries:

| User | Email | System Role | Team Role | Permitted Scope |
|---|---|---|---|---|
| **Alex Admin** | `admin@newtonite.internal` | `ADMIN` | Lead / Approver | Global access to all teams |
| **Sarah Chen** | `sarah.payments@newtonite.internal` | `USER` | Payments `APPROVER` | Payments team & approval decisions |
| **Alex Rivera** | `alex.payments@newtonite.internal` | `USER` | Payments `MEMBER` | Payments team work items |
| **Marcus Vance** | `marcus.platform@newtonite.internal` | `USER` | Platform `LEAD` | Platform team items & assignment |
| **Elena Rostova**| `elena.platform@newtonite.internal` | `USER` | Platform `MEMBER` | Platform team work items |
| **Valerie Viewer**| `viewer@newtonite.internal` | `VIEWER` | Member | **Read-only** across teams (mutations blocked) |
| **Oscar Outsider**| `outsider@newtonite.internal` | `USER` | Customer Ops `MEMBER`| Isolated to Customer Ops (**404 on Payments**) |

> **Pro-Tip**: Use the **"Demo Role Switcher"** widget at the top of the frontend sidebar to switch between any persona with 1 click during live interviews!

---

## 🧪 Automated Testing

### Backend Automated Tests
Run the comprehensive test suite (22 tests covering concurrency, OCC, idempotency, transitions, and security):

```bash
cd backend
source .venv/bin/activate
pytest -v
```

All 22 tests pass:
- `test_high_concurrency_claiming`: Spawns 10 concurrent threads attempting to claim the same unassigned item simultaneously. Proves exactly 1 succeeds (HTTP 200) and 9 fail (HTTP 409).
- `test_occ_stale_update_rejected_with_409`: Proves stale version updates are rejected and newer updates preserved.
- `test_idempotent_creation_returns_same_item_on_retry`: Proves network retries with identical keys return original item with zero duplicates.
- `test_idempotency_key_reuse_with_different_payload_returns_409`: Proves payload tampering returns HTTP 409 conflict.
- `test_approval_requirement_blocks_resolution`: Proves approval-required items cannot be resolved without sign-off.
- `test_viewer_cannot_create_work_item`: Proves viewers receive HTTP 403 Forbidden on writes.
- `test_cross_team_isolation_returns_404_not_found`: Proves cross-tenant access returns 404 to prevent enumeration.

### Frontend Typecheck & Build
Verify TypeScript strict compilation and Vite bundling:

```bash
cd frontend
npm run build
```

---

## 🎬 End-to-End Interview Demo Walkthrough

Follow this step-by-step sequence to demonstrate the critical acceptance criteria:

1. **Operational Dashboard**:
   - Navigate to `http://localhost:5174/login` and click **"Sarah Chen"**.
   - Inspect the Dashboard: observe real database metrics, Status Breakdown chart, "Needs Immediate Attention" table, and "Assigned to Me" tasks.
2. **Atomic Claiming**:
   - Navigate to **"All Work Items"** and find item **`NEW-7`** ("Settlement batch discrepancy in CAD corridor" — Unassigned).
   - Click to open its details page. Observe the "Claim This Item" button.
   - Click "Claim This Item".
   - Notice the item instantly updates to `Assignee: Sarah Chen`, database version increments from `v1` to `v2`, and the Activity Timeline records the claim event.
3. **Optimistic Concurrency Control (OCC) Conflict**:
   - Open work item `NEW-2` in **two separate browser windows** (Window A and Window B).
   - In Window A, change the priority from `HIGH` to `CRITICAL`. Notice version becomes `v3`.
   - In Window B (still showing `v2`), click Edit Title and attempt to save a change.
   - Window B is immediately rejected with `HTTP 409 Conflict`.
   - Notice the **Conflict Banner** appears, explaining that another user changed the item, with a 1-click button to reload the latest version without corrupting data.
4. **Idempotency Protection**:
   - Navigate to **"Create Work Item"** (`/work-items/new`).
   - Notice the client-generated idempotency key displayed at the bottom.
   - Fill out an item and click Create. If retried, the same resource key is preserved.
5. **Workflow & Approval Enforcement**:
   - Open work item `NEW-3` ("Merchant refund override exceeding threshold").
   - Notice the status is `IN_REVIEW` and requires approval (`PENDING`).
   - Switch to **Alex Rivera** using the sidebar role switcher.
   - Notice Alex has no Approve button (only approvers can decide).
   - Switch back to **Sarah Chen** (Payments Approver). Click **"Approve"**, enter an audit explanation ("Verified against TD Bank ledger batch"), and confirm.
   - The item status updates to `APPROVED` and can now be safely transitioned to `RESOLVED`.
6. **Authorization & Tenant Isolation**:
   - Switch to **Valerie Viewer** (Viewer role).
   - Notice the "+ New Item" CTA disappears, editing controls are hidden, and all API write attempts return `HTTP 403 Forbidden`.
   - Switch to **Oscar Outsider** (Customer Operations).
   - Notice Oscar cannot see any Payments items in the table. If Oscar attempts to navigate directly to `/work-items/<payments-uuid>`, the API returns `HTTP 404 Not Found`.

---

## 📖 Additional Architecture Documentation

- [ENGINEERING_DECISIONS.md](file:///Users/jaypathak/Desktop/newtonite-ops/ENGINEERING_DECISIONS.md) — Deep dive into transactional consistency, OCC conditional updates, and SQL sequence key generation.
- [KNOWN_LIMITATIONS.md](file:///Users/jaypathak/Desktop/newtonite-ops/KNOWN_LIMITATIONS.md) — Architectural boundaries, intentionally omitted features, and production roadmap.
