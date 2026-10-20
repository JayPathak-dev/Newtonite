"""Database seed script for demo and testing.

Creates teams, users with distinct system and team roles,
realistic work items across statuses, comments, and activity histories.
Repeatable and idempotent.
"""
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models.user import User, SystemRole
from app.models.team import Team
from app.models.team_membership import TeamMembership, TeamRole
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus
from app.models.comment import Comment
from app.models.activity import ActivityLog, EventType
from app.models.approval import ApprovalRecord, ApprovalDecision
from app.core.security import hash_password

DEMO_PASSWORD = "Password123!"


def seed_database():
    db = SessionLocal()
    try:
        print("🌱 Seeding database...")
        password_hash = hash_password(DEMO_PASSWORD)
        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # 1. TEAMS
        # -------------------------------------------------------------
        teams_data = [
            {
                "name": "Payments",
                "description": "Payment gateways, transaction processing, reconciliation, and settlement disputes.",
            },
            {
                "name": "Platform",
                "description": "Infrastructure, cloud services, reliability engineering, and core developer tools.",
            },
            {
                "name": "Customer Operations",
                "description": "Customer escalation, onboarding, merchant support, and dispute resolution.",
            },
        ]

        teams = {}
        for td in teams_data:
            team = db.query(Team).filter(Team.name == td["name"]).first()
            if not team:
                team = Team(name=td["name"], description=td["description"], is_active=True)
                db.add(team)
                db.flush()
                print(f"  ✓ Created team: {team.name}")
            teams[td["name"]] = team

        # -------------------------------------------------------------
        # 2. USERS
        # -------------------------------------------------------------
        users_data = [
            {
                "email": "admin@newtonite.internal",
                "name": "Alex Admin",
                "role": SystemRole.ADMIN,
                "teams": [
                    ("Payments", TeamRole.LEAD),
                    ("Platform", TeamRole.LEAD),
                    ("Customer Operations", TeamRole.LEAD),
                ],
            },
            {
                "email": "sarah.payments@newtonite.internal",
                "name": "Sarah Chen",
                "role": SystemRole.USER,
                "teams": [("Payments", TeamRole.APPROVER)],
            },
            {
                "email": "alex.payments@newtonite.internal",
                "name": "Alex Rivera",
                "role": SystemRole.USER,
                "teams": [("Payments", TeamRole.MEMBER)],
            },
            {
                "email": "marcus.platform@newtonite.internal",
                "name": "Marcus Vance",
                "role": SystemRole.USER,
                "teams": [("Platform", TeamRole.LEAD)],
            },
            {
                "email": "elena.platform@newtonite.internal",
                "name": "Elena Rostova",
                "role": SystemRole.USER,
                "teams": [("Platform", TeamRole.MEMBER)],
            },
            {
                "email": "david.ops@newtonite.internal",
                "name": "David Kim",
                "role": SystemRole.USER,
                "teams": [("Customer Operations", TeamRole.MEMBER)],
            },
            {
                "email": "viewer@newtonite.internal",
                "name": "Valerie Viewer",
                "role": SystemRole.VIEWER,
                "teams": [("Payments", TeamRole.MEMBER), ("Platform", TeamRole.MEMBER)],
            },
            {
                "email": "outsider@newtonite.internal",
                "name": "Oscar Outsider",
                "role": SystemRole.USER,
                "teams": [("Customer Operations", TeamRole.MEMBER)],
            },
        ]

        users = {}
        for ud in users_data:
            user = db.query(User).filter(User.email == ud["email"]).first()
            if not user:
                user = User(
                    email=ud["email"],
                    name=ud["name"],
                    password_hash=password_hash,
                    role=ud["role"],
                    is_active=True,
                )
                db.add(user)
                db.flush()
                print(f"  ✓ Created user: {user.name} ({user.email}) [{user.role.value}]")
            users[ud["email"]] = user

            # Memberships
            for team_name, team_role in ud["teams"]:
                team = teams[team_name]
                membership = (
                    db.query(TeamMembership)
                    .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == team.id)
                    .first()
                )
                if not membership:
                    membership = TeamMembership(
                        user_id=user.id,
                        team_id=team.id,
                        team_role=team_role,
                    )
                    db.add(membership)
                    db.flush()

        db.commit()

        # -------------------------------------------------------------
        # 3. WORK ITEMS
        # -------------------------------------------------------------
        work_items_seed = [
            {
                "key": "NEW-1",
                "title": "Payment gateway timeout spikes on EU checkout cluster",
                "description": "Intermittent 504 Gateway Timeout errors reported on the Frankfurt edge proxy when routing authorization payloads to WireCard/Adyen fallback.",
                "work_type": WorkType.PAYMENT_INVESTIGATION,
                "priority": WorkItemPriority.CRITICAL,
                "status": WorkItemStatus.OPEN,
                "team": "Payments",
                "assignee": None,
                "created_by": "sarah.payments@newtonite.internal",
                "due_at": now + timedelta(days=1),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [
                    (
                        "sarah.payments@newtonite.internal",
                        "Elevated from Sentry issue #41092. Error rate currently at 2.4% for EU transactions.",
                        now - timedelta(hours=3),
                    )
                ],
                "activities": [
                    (
                        "sarah.payments@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-1: Payment gateway timeout spikes on EU checkout cluster",
                        now - timedelta(hours=3),
                    ),
                ],
            },
            {
                "key": "NEW-2",
                "title": "Stripe webhook retry queue backing up under high load",
                "description": "During peak billing hours, incoming stripe charge.succeeded webhooks fail signature validation cache lookups and enter backoff loop.",
                "work_type": WorkType.ENGINEERING_ISSUE,
                "priority": WorkItemPriority.HIGH,
                "status": WorkItemStatus.IN_PROGRESS,
                "team": "Payments",
                "assignee": "alex.payments@newtonite.internal",
                "created_by": "sarah.payments@newtonite.internal",
                "due_at": now + timedelta(days=2),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [
                    (
                        "alex.payments@newtonite.internal",
                        "I've reproduced this in staging with 500 req/sec load generator. Redis lock TTL was too short.",
                        now - timedelta(hours=5),
                    )
                ],
                "activities": [
                    (
                        "sarah.payments@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-2: Stripe webhook retry queue backing up",
                        now - timedelta(days=1),
                    ),
                    (
                        "alex.payments@newtonite.internal",
                        EventType.WORK_ITEM_CLAIMED,
                        "Alex Rivera claimed this work item",
                        now - timedelta(hours=18),
                    ),
                    (
                        "alex.payments@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from OPEN to IN_PROGRESS",
                        now - timedelta(hours=18),
                    ),
                ],
            },
            {
                "key": "NEW-3",
                "title": "Merchant refund override exceeding threshold ($25,000 USD)",
                "description": "Merchant #94821 requested bulk charge reversal due to duplicate settlement batch on 2026-10-15. Requires financial lead authorization before executing refund.",
                "work_type": WorkType.APPROVAL_REQUEST,
                "priority": WorkItemPriority.CRITICAL,
                "status": WorkItemStatus.IN_REVIEW,
                "team": "Payments",
                "assignee": "sarah.payments@newtonite.internal",
                "created_by": "alex.payments@newtonite.internal",
                "due_at": now + timedelta(hours=8),
                "requires_approval": True,
                "approval_status": ApprovalStatus.PENDING,
                "comments": [
                    (
                        "alex.payments@newtonite.internal",
                        "Ledger audit confirmed duplicate credits totaling $25,480.00. Ready for Sarah's review and sign-off.",
                        now - timedelta(hours=2),
                    )
                ],
                "activities": [
                    (
                        "alex.payments@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-3: Merchant refund override exceeding threshold",
                        now - timedelta(hours=4),
                    ),
                    (
                        "alex.payments@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from OPEN to IN_PROGRESS",
                        now - timedelta(hours=3),
                    ),
                    (
                        "alex.payments@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from IN_PROGRESS to IN_REVIEW",
                        now - timedelta(hours=2),
                    ),
                ],
            },
            {
                "key": "NEW-4",
                "title": "PostgreSQL connection pool saturation during morning spike",
                "description": "PgBouncer pool reached 98% utilization at 09:00 UTC. Celery worker concurrency burst exhausted reserved client connections.",
                "work_type": WorkType.INCIDENT,
                "priority": WorkItemPriority.HIGH,
                "status": WorkItemStatus.IN_PROGRESS,
                "team": "Platform",
                "assignee": "marcus.platform@newtonite.internal",
                "created_by": "admin@newtonite.internal",
                "due_at": now + timedelta(days=1),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [
                    (
                        "marcus.platform@newtonite.internal",
                        "Adjusted pool size from 100 to 250 in staging config. Analyzing memory overhead before rolling to prod.",
                        now - timedelta(hours=1),
                    )
                ],
                "activities": [
                    (
                        "admin@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-4: PostgreSQL connection pool saturation",
                        now - timedelta(hours=6),
                    ),
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.WORK_ITEM_CLAIMED,
                        "Marcus Vance claimed this work item",
                        now - timedelta(hours=5),
                    ),
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from OPEN to IN_PROGRESS",
                        now - timedelta(hours=5),
                    ),
                ],
            },
            {
                "key": "NEW-5",
                "title": "Quarterly SOC2 & PCI-DSS access control audit evidence collection",
                "description": "Gather employee access revocation logs, KMS key rotation proofs, and firewall change request logs for Q3 compliance filing.",
                "work_type": WorkType.COMPLIANCE_REQUEST,
                "priority": WorkItemPriority.MEDIUM,
                "status": WorkItemStatus.BLOCKED,
                "team": "Platform",
                "assignee": "elena.platform@newtonite.internal",
                "created_by": "marcus.platform@newtonite.internal",
                "due_at": now - timedelta(days=2),  # OVERDUE
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [
                    (
                        "elena.platform@newtonite.internal",
                        "Blocked on external auditor providing the updated spreadsheet template.",
                        now - timedelta(days=1),
                    )
                ],
                "activities": [
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-5: Quarterly SOC2 & PCI-DSS audit",
                        now - timedelta(days=5),
                    ),
                    (
                        "elena.platform@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from IN_PROGRESS to BLOCKED",
                        now - timedelta(days=1),
                    ),
                ],
            },
            {
                "key": "NEW-6",
                "title": "Redis read-replica cache evictions spike on catalog queries",
                "description": "High memory fragmentation in node-3 caused transient TTL misses on product categories. Resolved by increasing instance RAM tier.",
                "work_type": WorkType.TASK,
                "priority": WorkItemPriority.MEDIUM,
                "status": WorkItemStatus.RESOLVED,
                "team": "Platform",
                "assignee": "elena.platform@newtonite.internal",
                "created_by": "marcus.platform@newtonite.internal",
                "due_at": now - timedelta(days=1),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [
                    (
                        "elena.platform@newtonite.internal",
                        "Resized cluster to cache.m6g.large. Eviction rate returned to zero.",
                        now - timedelta(hours=8),
                    )
                ],
                "activities": [
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-6: Redis cache evictions spike",
                        now - timedelta(days=3),
                    ),
                    (
                        "elena.platform@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status from IN_PROGRESS to RESOLVED",
                        now - timedelta(hours=8),
                    ),
                ],
            },
            {
                "key": "NEW-7",
                "title": "Unassigned claim demo: Settlement batch discrepancy in CAD corridor",
                "description": "Total settling sum for CAD transactions on TD Bank rail shows a $342.12 rounding discrepancy between batch header and aggregate transactions.",
                "work_type": WorkType.PAYMENT_INVESTIGATION,
                "priority": WorkItemPriority.HIGH,
                "status": WorkItemStatus.OPEN,
                "team": "Payments",
                "assignee": None,  # PERFECT FOR CONCURRENT CLAIM DEMO!
                "created_by": "sarah.payments@newtonite.internal",
                "due_at": now + timedelta(days=3),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [],
                "activities": [
                    (
                        "sarah.payments@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-7: Settlement batch discrepancy in CAD corridor",
                        now - timedelta(hours=1),
                    )
                ],
            },
            {
                "key": "NEW-8",
                "title": "Enterprise merchant onboarding KYC document verification stall",
                "description": "Acrobat Logistics Corp document OCR failed on business incorporation certificate. Needs manual review and KYC approval.",
                "work_type": WorkType.CUSTOMER_ISSUE,
                "priority": WorkItemPriority.HIGH,
                "status": WorkItemStatus.IN_PROGRESS,
                "team": "Customer Operations",
                "assignee": "david.ops@newtonite.internal",
                "created_by": "david.ops@newtonite.internal",
                "due_at": now + timedelta(hours=12),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [],
                "activities": [
                    (
                        "david.ops@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-8: Enterprise merchant onboarding stall",
                        now - timedelta(hours=4),
                    )
                ],
            },
            {
                "key": "NEW-9",
                "title": "Decommission legacy v0 webhook dispatcher service",
                "description": "Old python 2.7 dispatch worker cluster successfully replaced by modern Go worker fleet. Terminated EC2 instances and archived CloudWatch logs.",
                "work_type": WorkType.TASK,
                "priority": WorkItemPriority.LOW,
                "status": WorkItemStatus.CLOSED,
                "team": "Platform",
                "assignee": "marcus.platform@newtonite.internal",
                "created_by": "marcus.platform@newtonite.internal",
                "due_at": now - timedelta(days=7),
                "requires_approval": False,
                "approval_status": ApprovalStatus.NOT_REQUIRED,
                "comments": [],
                "activities": [
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.WORK_ITEM_CREATED,
                        "Created work item NEW-9: Decommission legacy v0 webhook",
                        now - timedelta(days=10),
                    ),
                    (
                        "marcus.platform@newtonite.internal",
                        EventType.STATUS_CHANGED,
                        "Changed status to CLOSED",
                        now - timedelta(days=6),
                    ),
                ],
            },
        ]

        for item_data in work_items_seed:
            item = db.query(WorkItem).filter(WorkItem.key == item_data["key"]).first()
            team = teams[item_data["team"]]
            assignee = users[item_data["assignee"]] if item_data["assignee"] else None
            creator = users[item_data["created_by"]]

            if not item:
                item = WorkItem(
                    key=item_data["key"],
                    title=item_data["title"],
                    description=item_data["description"],
                    work_type=item_data["work_type"],
                    priority=item_data["priority"],
                    status=item_data["status"],
                    team_id=team.id,
                    assignee_id=assignee.id if assignee else None,
                    created_by_id=creator.id,
                    due_at=item_data["due_at"],
                    requires_approval=item_data["requires_approval"],
                    approval_status=item_data["approval_status"],
                    version=1,
                    created_at=now - timedelta(days=2),
                    updated_at=now - timedelta(hours=1),
                )
                if item.status == WorkItemStatus.RESOLVED:
                    item.resolved_at = now - timedelta(hours=8)
                elif item.status == WorkItemStatus.CLOSED:
                    item.closed_at = now - timedelta(days=6)

                db.add(item)
                db.flush()
                print(f"  ✓ Created work item: {item.key} - {item.title[:45]}...")

                # Comments
                for author_email, body, comment_time in item_data["comments"]:
                    c_user = users[author_email]
                    comment = Comment(
                        work_item_id=item.id,
                        author_id=c_user.id,
                        body=body,
                        created_at=comment_time,
                    )
                    db.add(comment)

                # Activities
                for actor_email, evt_type, summary, evt_time in item_data["activities"]:
                    a_user = users[actor_email]
                    act = ActivityLog(
                        work_item_id=item.id,
                        actor_id=a_user.id,
                        event_type=evt_type,
                        summary=summary,
                        created_at=evt_time,
                    )
                    db.add(act)

        # Update sequence so new items generated via sequence start at NEW-10
        from sqlalchemy import text
        db.execute(text("SELECT setval('work_item_key_seq', 9, true)"))

        db.commit()
        print("\n✅ Database seeding complete!")
        print("\n🔑 Demo credentials (all passwords: Password123!):")
        print("  - Admin:      admin@newtonite.internal")
        print("  - Approver:   sarah.payments@newtonite.internal (Payments Lead/Approver)")
        print("  - Member:     alex.payments@newtonite.internal (Payments Member)")
        print("  - Platform:   marcus.platform@newtonite.internal (Platform Lead)")
        print("  - Viewer:     viewer@newtonite.internal (Read-only)")
        print("  - Outsider:   outsider@newtonite.internal (Customer Operations only)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
