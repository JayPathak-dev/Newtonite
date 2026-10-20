import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  UserCheck,
  Clock,
  Calendar,
  AlertTriangle,
  Send,
  CheckCircle2,
  XCircle,
  FileCheck,
  Shield,
  Layers,
  Edit2,
  Check,
  X,
  History,
  MessageSquare,
} from 'lucide-react';
import { api, ApiClientError } from '../lib/api';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { ConflictBanner } from '../components/ConflictBanner';
import { WorkItemStatus, WorkItemPriority } from '../types';
import { useAuth } from '../context/AuthContext';

export const WorkItemDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Conflict state
  const [conflictError, setConflictError] = useState<{
    code: string;
    message: string;
    details?: any;
  } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Inline editing states
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [editDesc, setEditDesc] = useState('');

  // Comment state
  const [commentBody, setCommentBody] = useState('');

  // Approval modal state
  const [approvalModal, setApprovalModal] = useState<{
    isOpen: boolean;
    decision: 'approved' | 'rejected';
    explanation: string;
  }>({ isOpen: false, decision: 'approved', explanation: '' });

  // 1. Fetch Work Item
  const {
    data: item,
    isLoading,
    isError,
    error,
    refetch: refetchItem,
  } = useQuery({
    queryKey: ['workItem', id],
    queryFn: () => (id ? api.workItems.get(id) : Promise.reject('No ID')),
    enabled: Boolean(id),
  });

  // 2. Fetch Comments
  const { data: comments, refetch: refetchComments } = useQuery({
    queryKey: ['workItemComments', id],
    queryFn: () => (id ? api.workItems.getComments(id) : Promise.resolve([])),
    enabled: Boolean(id),
  });

  // 3. Fetch Activity
  const { data: activityData, refetch: refetchActivity } = useQuery({
    queryKey: ['workItemActivity', id],
    queryFn: () => (id ? api.workItems.getActivity(id) : Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 })),
    enabled: Boolean(id),
  });

  // 4. Fetch Users in the same team for assignment dropdown
  const { data: teamUsers } = useQuery({
    queryKey: ['teamUsers', item?.team_id],
    queryFn: () => (item?.team_id ? api.users.list(item.team_id) : Promise.resolve([])),
    enabled: Boolean(item?.team_id),
  });

  const isViewer = user?.role === 'VIEWER';

  // Check if current user has approval privileges for this item's team
  const isApproverForTeam = Boolean(
    user?.role === 'ADMIN' ||
      user?.team_memberships.some(
        (m) =>
          m.team_id === item?.team_id &&
          (m.team_role === 'APPROVER' || m.team_role === 'LEAD')
      )
  );

  const handleConflict = (err: any) => {
    if (err instanceof ApiClientError && (err.code === 'STALE_VERSION' || err.code === 'ALREADY_CLAIMED')) {
      setConflictError({
        code: err.code,
        message: err.message,
        details: err.details,
      });
    } else {
      setActionError(err.message || 'Operation failed');
    }
  };

  const handleReload = async () => {
    setConflictError(null);
    setActionError(null);
    setIsEditingTitle(false);
    setIsEditingDesc(false);
    await Promise.all([refetchItem(), refetchComments(), refetchActivity()]);
  };

  // Claim Mutation (Atomic!)
  const claimMutation = useMutation({
    mutationFn: () => api.workItems.claim(item!.id),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Status Transition Mutation
  const transitionMutation = useMutation({
    mutationFn: (newStatus: WorkItemStatus) =>
      api.workItems.transition(item!.id, item!.version, newStatus),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Assign Mutation
  const assignMutation = useMutation({
    mutationFn: (newAssigneeId: string | null) =>
      api.workItems.assign(item!.id, item!.version, newAssigneeId),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Priority Update Mutation
  const priorityMutation = useMutation({
    mutationFn: (newPriority: WorkItemPriority) =>
      api.workItems.update(item!.id, item!.version, { priority: newPriority }),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Title Save Mutation
  const titleMutation = useMutation({
    mutationFn: (newTitle: string) =>
      api.workItems.update(item!.id, item!.version, { title: newTitle }),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      setIsEditingTitle(false);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Description Save Mutation
  const descMutation = useMutation({
    mutationFn: (newDesc: string) =>
      api.workItems.update(item!.id, item!.version, { description: newDesc }),
    onSuccess: (updated) => {
      setConflictError(null);
      setActionError(null);
      setIsEditingDesc(false);
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Comment Mutation
  const commentMutation = useMutation({
    mutationFn: (body: string) => api.workItems.addComment(item!.id, body),
    onSuccess: () => {
      setCommentBody('');
      refetchComments();
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Approval Decision Mutation
  const approvalMutation = useMutation({
    mutationFn: ({ decision, explanation }: { decision: 'approved' | 'rejected'; explanation?: string }) =>
      api.workItems.decideApproval(item!.id, decision, explanation),
    onSuccess: (updated) => {
      setApprovalModal({ isOpen: false, decision: 'approved', explanation: '' });
      queryClient.setQueryData(['workItem', id], updated);
      refetchActivity();
    },
    onError: handleConflict,
  });

  // Allowed transitions map
  const ALLOWED_TRANSITIONS: Record<WorkItemStatus, { label: string; status: WorkItemStatus; color: string }[]> = {
    OPEN: [
      { label: 'Start Work', status: 'IN_PROGRESS', color: 'bg-indigo-600 hover:bg-indigo-700' },
      { label: 'Close Item', status: 'CLOSED', color: 'bg-gray-600 hover:bg-gray-700' },
    ],
    IN_PROGRESS: [
      { label: 'Mark Blocked', status: 'BLOCKED', color: 'bg-amber-600 hover:bg-amber-700' },
      { label: 'Send for Review', status: 'IN_REVIEW', color: 'bg-purple-600 hover:bg-purple-700' },
      { label: 'Resolve', status: 'RESOLVED', color: 'bg-emerald-600 hover:bg-emerald-700' },
    ],
    BLOCKED: [
      { label: 'Resume Work', status: 'IN_PROGRESS', color: 'bg-indigo-600 hover:bg-indigo-700' },
      { label: 'Close Item', status: 'CLOSED', color: 'bg-gray-600 hover:bg-gray-700' },
    ],
    IN_REVIEW: [
      { label: 'Return to In Progress', status: 'IN_PROGRESS', color: 'bg-indigo-600 hover:bg-indigo-700' },
      { label: 'Resolve', status: 'RESOLVED', color: 'bg-emerald-600 hover:bg-emerald-700' },
    ],
    RESOLVED: [
      { label: 'Reopen Item', status: 'IN_PROGRESS', color: 'bg-indigo-600 hover:bg-indigo-700' },
      { label: 'Close Final', status: 'CLOSED', color: 'bg-gray-800 hover:bg-gray-900' },
    ],
    CLOSED: [], // Terminal
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs text-text-secondary">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mb-2" />
        <p>Loading work item details...</p>
      </div>
    );
  }

  if (isError || !item) {
    return (
      <div className="p-12 text-center text-xs text-danger">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-danger" />
        <h3 className="text-base font-bold text-text-primary">Work Item Not Accessible</h3>
        <p className="text-text-secondary mt-1 max-w-sm mx-auto">
          {(error as any)?.message ||
            'This work item does not exist or you do not have permission to access it.'}
        </p>
        <button
          onClick={() => navigate('/work-items')}
          className="mt-4 px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg"
        >
          Back to Work Items
        </button>
      </div>
    );
  }

  const allowedNextStatuses = ALLOWED_TRANSITIONS[item.status] || [];

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title={`${item.key}: ${item.title}`}
        subtitle={`Work item details in ${item.team?.name || 'team'} • Version ${item.version}`}
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-4">
        {/* Back Link & Quick Info */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/work-items')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-text-secondary hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Work Items</span>
          </button>

          <div className="flex items-center gap-2 font-mono text-xs text-text-secondary">
            <span>Database Version:</span>
            <span className="px-2 py-0.5 bg-gray-100 rounded font-bold text-text-primary">
              v{item.version}
            </span>
          </div>
        </div>

        {/* Optimistic Concurrency Conflict Banner */}
        {conflictError && (
          <ConflictBanner
            message={conflictError.message}
            onReload={handleReload}
            isLoading={isLoading}
          />
        )}

        {/* Action Error Banner */}
        {actionError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError(null)} className="text-red-500 hover:text-red-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Two-Column Responsive Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Column (2 spans) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Core Item Card */}
            <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-5">
              {/* Badges & Key */}
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="font-mono font-bold text-sm text-primary px-2.5 py-0.5 bg-primary-light rounded-md">
                  {item.key}
                </span>
                <StatusBadge status={item.status} size="md" />
                <PriorityBadge priority={item.priority} size="md" />
                <WorkTypeBadge workType={item.work_type} />
                {item.requires_approval && (
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${
                      item.approval_status === 'approved'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : item.approval_status === 'rejected'
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : 'bg-purple-50 text-purple-700 border-purple-200'
                    }`}
                  >
                    <FileCheck className="w-3.5 h-3.5" />
                    Approval: {item.approval_status.toUpperCase()}
                  </span>
                )}
              </div>

              {/* Title (Inline editable) */}
              <div>
                {isEditingTitle ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="flex-1 px-3 py-1.5 text-base font-bold bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <button
                      onClick={() => titleMutation.mutate(editTitle)}
                      disabled={titleMutation.isPending}
                      className="p-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setIsEditingTitle(false)}
                      className="p-2 bg-gray-100 text-text-secondary rounded-lg hover:bg-gray-200"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-3 group">
                    <h2 className="text-xl font-bold text-text-primary leading-snug">{item.title}</h2>
                    {!isViewer && (
                      <button
                        onClick={() => {
                          setEditTitle(item.title);
                          setIsEditingTitle(true);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-text-secondary hover:text-primary transition-opacity"
                        title="Edit title"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Description (Inline editable) */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider">
                    Description & Context
                  </h4>
                  {!isViewer && !isEditingDesc && (
                    <button
                      onClick={() => {
                        setEditDesc(item.description || '');
                        setIsEditingDesc(true);
                      }}
                      className="text-xs text-primary hover:text-primary-hover font-semibold flex items-center gap-1"
                    >
                      <Edit2 className="w-3 h-3" />
                      Edit
                    </button>
                  )}
                </div>

                {isEditingDesc ? (
                  <div className="space-y-2">
                    <textarea
                      rows={4}
                      value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                    />
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setIsEditingDesc(false)}
                        className="px-3 py-1 text-xs border border-border text-text-secondary rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => descMutation.mutate(editDesc)}
                        disabled={descMutation.isPending}
                        className="px-3 py-1 text-xs bg-primary text-white font-semibold rounded-md hover:bg-primary-hover"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-3.5 bg-background rounded-lg border border-border/80 text-xs text-text-primary whitespace-pre-wrap leading-relaxed">
                    {item.description || (
                      <span className="text-text-secondary italic">No description provided.</span>
                    )}
                  </div>
                )}
              </div>

              {/* Status Transition Action Bar */}
              {!isViewer && allowedNextStatuses.length > 0 && (
                <div className="pt-4 border-t border-border">
                  <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2.5">
                    Allowed Workflow Transitions
                  </h4>
                  <div className="flex flex-wrap items-center gap-2">
                    {allowedNextStatuses.map((t) => (
                      <button
                        key={t.status}
                        onClick={() => transitionMutation.mutate(t.status)}
                        disabled={transitionMutation.isPending}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold text-white shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5 ${t.color}`}
                      >
                        <span>{t.label}</span>
                        <span className="opacity-70 text-[10px]">({t.status})</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Comments & Discussion */}
            <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <MessageSquare className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-bold text-text-primary">
                  Comments & Discussion ({comments?.length || 0})
                </h3>
              </div>

              {/* Add Comment Input */}
              {!isViewer && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (commentBody.trim()) commentMutation.mutate(commentBody.trim());
                  }}
                  className="space-y-2"
                >
                  <textarea
                    rows={2}
                    placeholder="Add an operational note or update..."
                    value={commentBody}
                    onChange={(e) => setCommentBody(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                  />
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={commentMutation.isPending || !commentBody.trim()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 transition-colors"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{commentMutation.isPending ? 'Posting...' : 'Comment'}</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Comments Thread */}
              <div className="space-y-3 pt-2">
                {!comments || comments.length === 0 ? (
                  <p className="text-xs text-text-secondary italic text-center py-4">
                    No comments yet on this work item.
                  </p>
                ) : (
                  comments.map((comment) => (
                    <div
                      key={comment.id}
                      className="p-3 bg-background rounded-lg border border-border/70 space-y-1.5 text-xs"
                    >
                      <div className="flex items-center justify-between text-[11px] text-text-secondary">
                        <span className="font-semibold text-text-primary">
                          {comment.author?.name || 'Team Member'}
                        </span>
                        <span>{new Date(comment.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-text-primary whitespace-pre-wrap leading-relaxed">
                        {comment.body}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Activity Timeline */}
            <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <History className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-bold text-text-primary">
                  Activity Timeline ({activityData?.total || 0})
                </h3>
              </div>

              <div className="relative pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                {!activityData?.items || activityData.items.length === 0 ? (
                  <p className="text-xs text-text-secondary italic">No activity recorded.</p>
                ) : (
                  activityData.items.map((act) => (
                    <div key={act.id} className="relative text-xs space-y-0.5">
                      <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-primary border-2 border-white shadow-sm" />
                      <div className="flex items-center justify-between text-[11px] text-text-secondary">
                        <span className="font-semibold text-text-primary">
                          {act.actor?.name || 'System'}
                        </span>
                        <span className="font-mono text-[10px]">
                          {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •{' '}
                          {new Date(act.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-text-primary font-medium">{act.summary}</p>
                      {act.field_name && (
                        <div className="flex items-center gap-1.5 text-[10px] font-mono text-text-secondary pt-0.5">
                          <span className="px-1.5 py-0.2 bg-gray-100 rounded line-through">
                            {act.previous_value || 'none'}
                          </span>
                          <span>→</span>
                          <span className="px-1.5 py-0.2 bg-indigo-50 text-indigo-700 font-semibold rounded">
                            {act.new_value}
                          </span>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Side Panel (1 span) */}
          <div className="space-y-5">
            {/* Ownership & Claim Card */}
            <div className="bg-surface rounded-xl border border-border shadow-subtle p-5 space-y-4">
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider border-b border-border pb-2">
                Ownership & Assignment
              </h4>

              {/* Assignee State */}
              <div>
                <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                  Assignee
                </label>
                {item.assignee ? (
                  <div className="flex items-center gap-2 p-2 bg-background rounded-lg border border-border">
                    <div className="w-7 h-7 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center">
                      {item.assignee.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold text-text-primary truncate">{item.assignee.name}</p>
                      <p className="text-[10px] text-text-secondary truncate">{item.assignee.email}</p>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-center space-y-2">
                    <p className="text-xs font-bold text-amber-900">Unassigned</p>
                    <p className="text-[11px] text-amber-800">
                      This item has no owner. Anyone in this team can claim it.
                    </p>
                    {!isViewer && (
                      <button
                        onClick={() => claimMutation.mutate()}
                        disabled={claimMutation.isPending}
                        className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-md shadow-sm transition-colors"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        <span>{claimMutation.isPending ? 'Claiming...' : 'Claim This Item'}</span>
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Reassign Dropdown */}
              {!isViewer && (
                <div>
                  <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                    Reassign To
                  </label>
                  <select
                    value={item.assignee_id || ''}
                    onChange={(e) => assignMutation.mutate(e.target.value || null)}
                    disabled={assignMutation.isPending}
                    className="w-full px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Unassigned</option>
                    {teamUsers?.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Priority Selector */}
              {!isViewer && (
                <div>
                  <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                    Priority Level
                  </label>
                  <select
                    value={item.priority}
                    onChange={(e) => priorityMutation.mutate(e.target.value as WorkItemPriority)}
                    disabled={priorityMutation.isPending}
                    className="w-full px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              )}
            </div>

            {/* Approval Decision Card (if requires approval) */}
            {item.requires_approval && (
              <div className="bg-surface rounded-xl border border-purple-200 shadow-subtle p-5 space-y-3">
                <div className="flex items-center gap-2 text-purple-900 border-b border-purple-100 pb-2">
                  <FileCheck className="w-4 h-4 text-purple-700" />
                  <h4 className="text-xs font-bold uppercase tracking-wider">Approval Required</h4>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-text-secondary font-medium">Current Status:</span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-xs ${
                      item.approval_status === 'approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : item.approval_status === 'rejected'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-purple-100 text-purple-800'
                    }`}
                  >
                    {item.approval_status.toUpperCase()}
                  </span>
                </div>

                {item.approval_status === 'pending' && isApproverForTeam && (
                  <div className="pt-2 flex gap-2">
                    <button
                      onClick={() =>
                        setApprovalModal({ isOpen: true, decision: 'approved', explanation: '' })
                      }
                      className="flex-1 py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center justify-center gap-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() =>
                        setApprovalModal({ isOpen: true, decision: 'rejected', explanation: '' })
                      }
                      className="flex-1 py-1.5 px-3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center justify-center gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Metadata Card */}
            <div className="bg-surface rounded-xl border border-border shadow-subtle p-5 space-y-3 text-xs">
              <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider border-b border-border pb-2">
                Metadata & Tracking
              </h4>

              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Team:</span>
                <span className="font-semibold text-text-primary">{item.team?.name || '—'}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Created By:</span>
                <span className="font-semibold text-text-primary">{item.created_by?.name || '—'}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Created:</span>
                <span className="text-text-primary">{new Date(item.created_at).toLocaleDateString()}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Last Modified:</span>
                <span className="text-text-primary font-mono text-[11px]">
                  {new Date(item.updated_at).toLocaleString()}
                </span>
              </div>

              {item.due_at && (
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Due Date:</span>
                  <span className="font-semibold text-text-primary">
                    {new Date(item.due_at).toLocaleDateString()}
                  </span>
                </div>
              )}

              {item.resolved_at && (
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Resolved At:</span>
                  <span className="text-emerald-700 font-medium">
                    {new Date(item.resolved_at).toLocaleDateString()}
                  </span>
                </div>
              )}

              {item.closed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Closed At:</span>
                  <span className="text-gray-700 font-medium">
                    {new Date(item.closed_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Approval Decision Modal */}
      {approvalModal.isOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-surface rounded-xl border border-border shadow-modal max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-primary" />
              <span>Confirm {approvalModal.decision === 'approved' ? 'Approval' : 'Rejection'}</span>
            </h3>

            <p className="text-xs text-text-secondary leading-relaxed">
              Please provide an explanation or reference code for your decision. This will be stored
              in the official audit ledger.
            </p>

            <textarea
              rows={3}
              placeholder="e.g., Audit verified: invoice matched against bank statement."
              value={approvalModal.explanation}
              onChange={(e) => setApprovalModal({ ...approvalModal, explanation: e.target.value })}
              className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setApprovalModal({ ...approvalModal, isOpen: false })}
                className="px-3 py-1.5 border border-border rounded-lg text-xs font-semibold text-text-secondary hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() =>
                  approvalMutation.mutate({
                    decision: approvalModal.decision,
                    explanation: approvalModal.explanation,
                  })
                }
                disabled={approvalMutation.isPending}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold text-white shadow-sm ${
                  approvalModal.decision === 'approved'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {approvalMutation.isPending
                  ? 'Submitting...'
                  : `Confirm ${approvalModal.decision === 'approved' ? 'Approve' : 'Reject'}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
