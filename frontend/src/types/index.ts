export type SystemRole = 'ADMIN' | 'USER' | 'VIEWER';

export type TeamRole = 'MEMBER' | 'LEAD' | 'APPROVER';

export interface UserBrief {
  id: string;
  name: string;
  email: string;
  role: SystemRole;
}

export interface TeamMemberInfo {
  team_id: string;
  team_name: string;
  team_role: TeamRole;
}

export interface CurrentUser {
  id: string;
  name: string;
  email: string;
  role: SystemRole;
  is_active: boolean;
  team_memberships: TeamMemberInfo[];
  teams: TeamMemberInfo[];
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  member_count?: number;
}

export interface TeamDetail extends Team {
  members: {
    user_id: string;
    team_id: string;
    team_role: TeamRole;
    user: UserBrief;
    created_at: string;
  }[];
}

export type WorkItemStatus =
  | 'OPEN'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'IN_REVIEW'
  | 'RESOLVED'
  | 'CLOSED';

export type WorkItemPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type WorkType =
  | 'incident'
  | 'task'
  | 'customer_issue'
  | 'engineering_issue'
  | 'payment_investigation'
  | 'compliance_request'
  | 'approval_request';

export type ApprovalStatus = 'not_required' | 'pending' | 'approved' | 'rejected';

export interface WorkItem {
  id: string;
  key: string;
  title: string;
  description?: string | null;
  status: WorkItemStatus;
  priority: WorkItemPriority;
  work_type: WorkType;
  team_id: string;
  team?: { id: string; name: string };
  team_name?: string | null;
  assignee_id?: string | null;
  assignee?: UserBrief | null;
  assignee_name?: string | null;
  created_by_id: string;
  created_by?: UserBrief;
  due_at?: string | null;
  requires_approval: boolean;
  approval_status: ApprovalStatus;
  version: number;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  closed_at?: string | null;
}

export interface WorkItemListResponse {
  items: WorkItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Comment {
  id: string;
  work_item_id: string;
  author_id: string;
  author: UserBrief;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityLog {
  id: string;
  work_item_id: string;
  actor_id?: string | null;
  actor?: UserBrief | null;
  event_type: string;
  field_name?: string | null;
  previous_value?: string | null;
  new_value?: string | null;
  summary: string;
  metadata?: Record<string, any> | null;
  created_at: string;
}

export interface PaginatedActivityResponse {
  items: ActivityLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApprovalRecord {
  id: string;
  work_item_id: string;
  decision: 'approved' | 'rejected';
  explanation?: string | null;
  requested_at: string;
  decided_at?: string | null;
}

export interface DashboardSummary {
  open_items: number;
  critical_items: number;
  unassigned_items: number;
  overdue_items: number;
  pending_approvals: number;
}

export interface StatusBreakdown {
  status: WorkItemStatus;
  count: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}
