import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Save, AlertCircle, ShieldAlert, KeyRound } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { WorkItemPriority, WorkType } from '../types';
import { useAuth } from '../context/AuthContext';

export const CreateWorkItemPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Stable client-generated idempotency key for this logical create session
  const [idempotencyKey] = useState(() => {
    return 'idem-' + Math.random().toString(36).substring(2, 15) + '-' + Date.now();
  });

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [workType, setWorkType] = useState<WorkType>('task');
  const [priority, setPriority] = useState<WorkItemPriority>('MEDIUM');
  const [teamId, setTeamId] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [requiresApproval, setRequiresApproval] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Fetch permitted teams
  const { data: teams, isLoading: loadingTeams } = useQuery({
    queryKey: ['teamsList'],
    queryFn: api.teams.list,
  });

  // Automatically select first team when loaded
  useEffect(() => {
    if (teams && teams.length > 0 && !teamId) {
      setTeamId(teams[0].id);
    }
  }, [teams, teamId]);

  // Fetch assignable users for the selected team
  const { data: teamMembers } = useQuery({
    queryKey: ['teamUsers', teamId],
    queryFn: () => (teamId ? api.users.list(teamId) : Promise.resolve([])),
    enabled: Boolean(teamId),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!teamId) {
      setError('Please select a team');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const newItem = await api.workItems.create({
        title: title.trim(),
        description: description.trim() || undefined,
        work_type: workType,
        priority,
        team_id: teamId,
        assignee_id: assigneeId || undefined,
        due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
        requires_approval: requiresApproval,
        idempotency_key: idempotencyKey, // Guaranteed reuse on retries!
      });

      navigate(`/work-items/${newItem.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create work item. You can safely retry.');
    } finally {
      setSubmitting(false);
    }
  };

  if (user?.role === 'VIEWER') {
    return (
      <div className="p-8 text-center">
        <ShieldAlert className="w-12 h-12 text-amber-500 mx-auto mb-3" />
        <h2 className="text-base font-bold text-text-primary">Read-Only Permission</h2>
        <p className="text-xs text-text-secondary mt-1">
          Your role (VIEWER) does not permit creating new work items.
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

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Create Work Item"
        subtitle="Submit a new operational request, incident, or task with transactional guarantee"
      />

      <div className="flex-1 p-6 max-w-3xl w-full mx-auto">
        <button
          onClick={() => navigate('/work-items')}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Work Items</span>
        </button>

        <div className="bg-surface rounded-xl border border-border shadow-subtle p-6">
          {error && (
            <div className="mb-5 p-3.5 rounded-lg bg-danger-light border border-red-200 flex items-start gap-2.5 text-xs text-danger font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span>{error}</span>
                <p className="mt-1 text-[11px] text-red-700">
                  Note: The same idempotency key is preserved, so retrying is 100% duplicate-safe.
                </p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Title */}
            <div>
              <label className="block text-xs font-bold text-text-primary mb-1">
                Title <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g., Stripe webhook retry queue backoff spike"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-medium"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-bold text-text-primary mb-1">
                Description / Context
              </label>
              <textarea
                rows={4}
                placeholder="Detailed context, reproduction steps, impacted systems, or ledger discrepancies..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent leading-relaxed"
              />
            </div>

            {/* Work Type, Priority & Team Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-text-primary mb-1">Work Type</label>
                <select
                  value={workType}
                  onChange={(e) => setWorkType(e.target.value as WorkType)}
                  className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="incident">🚨 Incident</option>
                  <option value="task">📋 Task</option>
                  <option value="payment_investigation">💳 Payment Investigation</option>
                  <option value="customer_issue">👥 Customer Issue</option>
                  <option value="engineering_issue">⚙️ Engineering Issue</option>
                  <option value="compliance_request">🛡️ Compliance Request</option>
                  <option value="approval_request">📝 Approval Request</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-text-primary mb-1">Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as WorkItemPriority)}
                  className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="CRITICAL">Critical (P0)</option>
                  <option value="HIGH">High (P1)</option>
                  <option value="MEDIUM">Medium (P2)</option>
                  <option value="LOW">Low (P3)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-text-primary mb-1">
                  Assigned Team <span className="text-danger">*</span>
                </label>
                <select
                  value={teamId}
                  onChange={(e) => setTeamId(e.target.value)}
                  disabled={loadingTeams}
                  className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {teams?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Assignee & Due Date Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-text-primary mb-1">
                  Assignee (Optional)
                </label>
                <select
                  value={assigneeId}
                  onChange={(e) => setAssigneeId(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Leave Unassigned (Claimable)</option>
                  {teamMembers?.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.email})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-text-primary mb-1">
                  Due Date (Optional)
                </label>
                <input
                  type="date"
                  value={dueAt}
                  onChange={(e) => setDueAt(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {/* Approval Requirement Checkbox */}
            <div className="p-3.5 bg-background rounded-lg border border-border flex items-start gap-3">
              <input
                type="checkbox"
                id="requiresApproval"
                checked={requiresApproval}
                onChange={(e) => setRequiresApproval(e.target.checked)}
                className="mt-0.5 rounded text-primary focus:ring-primary h-4 w-4 border-gray-300"
              />
              <div>
                <label htmlFor="requiresApproval" className="text-xs font-bold text-text-primary cursor-pointer">
                  Requires Financial / Managerial Approval
                </label>
                <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed">
                  When enabled, this work item cannot be resolved or closed until a team Approver or Lead formally reviews and signs off on the request.
                </p>
              </div>
            </div>

            {/* Idempotency Footer Info */}
            <div className="p-3 bg-indigo-50/50 border border-indigo-100 rounded-lg flex items-center justify-between text-[11px] text-indigo-900">
              <div className="flex items-center gap-1.5 font-mono text-[10px]">
                <KeyRound className="w-3.5 h-3.5 text-primary" />
                <span>Idempotency Key: {idempotencyKey.slice(0, 18)}...</span>
              </div>
              <span className="text-indigo-700">Protected against double-click & retry duplicates</span>
            </div>

            {/* Submit Action */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => navigate('/work-items')}
                className="px-4 py-2 border border-border text-xs font-semibold text-text-secondary hover:text-text-primary rounded-lg transition-colors"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-1.5 px-5 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{submitting ? 'Creating Work Item...' : 'Create Work Item'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
