import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  X,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Plus,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { WorkItemStatus, WorkItemPriority, WorkType } from '../types';
import { useAuth } from '../context/AuthContext';

export const WorkItemsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  // Query state derived from searchParams
  const page = parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('search') || '';
  const status = (searchParams.get('status') as WorkItemStatus) || undefined;
  const priority = (searchParams.get('priority') as WorkItemPriority) || undefined;
  const workType = (searchParams.get('work_type') as WorkType) || undefined;
  const teamId = searchParams.get('team_id') || undefined;
  const assigneeId = searchParams.get('assignee_id') || undefined;
  const overdue = searchParams.get('overdue') === 'true';
  const sortBy = searchParams.get('sort_by') || 'updated_at';
  const sortOrder = (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc';

  const [searchInput, setSearchInput] = useState(search);

  // Debounced search sync
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== search) {
        updateFilter({ search: searchInput || undefined, page: 1 });
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const updateFilter = (updates: Record<string, string | number | boolean | undefined>) => {
    const nextParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === undefined || value === '' || value === false) {
        nextParams.delete(key);
      } else {
        nextParams.set(key, String(value));
      }
    });
    setSearchParams(nextParams);
  };

  const clearAllFilters = () => {
    setSearchInput('');
    setSearchParams(new URLSearchParams());
  };

  // Fetch teams for filter dropdown
  const { data: teams } = useQuery({
    queryKey: ['teamsList'],
    queryFn: api.teams.list,
  });

  // Fetch work items
  const {
    data: workItemsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      'workItems',
      page,
      search,
      status,
      priority,
      workType,
      teamId,
      assigneeId,
      overdue,
      sortBy,
      sortOrder,
      user?.id,
    ],
    queryFn: () =>
      api.workItems.list({
        page,
        page_size: 15,
        search: search || undefined,
        status,
        priority,
        work_type: workType,
        team_id: teamId,
        assignee_id: assigneeId,
        overdue: overdue ? true : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
  });

  const handleSort = (field: string) => {
    if (sortBy === field) {
      updateFilter({ sort_order: sortOrder === 'asc' ? 'desc' : 'asc' });
    } else {
      updateFilter({ sort_by: field, sort_order: 'desc' });
    }
  };

  const hasActiveFilters = Boolean(
    search || status || priority || workType || teamId || assigneeId || overdue
  );

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="All Work Items"
        subtitle="Operational inventory with real-time server-side filtering and optimistic concurrency"
      />

      <div className="flex-1 p-6 space-y-4 max-w-7xl w-full mx-auto">
        {/* Filters and Search Bar */}
        <div className="bg-surface p-4 rounded-xl border border-border shadow-subtle space-y-3">
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by key, title, or description..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full pl-9 pr-8 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              {searchInput && (
                <button
                  onClick={() => setSearchInput('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => updateFilter({ overdue: !overdue, page: 1 })}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                  overdue
                    ? 'bg-danger text-white border-danger shadow-sm'
                    : 'bg-background text-text-secondary border-border hover:bg-gray-100'
                }`}
              >
                Overdue Only
              </button>

              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-danger hover:bg-danger-light rounded-lg transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          {/* Filter Dropdowns Grid */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/60">
            {/* Status Dropdown */}
            <select
              value={status || ''}
              onChange={(e) => updateFilter({ status: e.target.value || undefined, page: 1 })}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="BLOCKED">Blocked</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>

            {/* Priority Dropdown */}
            <select
              value={priority || ''}
              onChange={(e) => updateFilter({ priority: e.target.value || undefined, page: 1 })}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            {/* Work Type Dropdown */}
            <select
              value={workType || ''}
              onChange={(e) => updateFilter({ work_type: e.target.value || undefined, page: 1 })}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Types</option>
              <option value="incident">Incident</option>
              <option value="task">Task</option>
              <option value="customer_issue">Customer Issue</option>
              <option value="engineering_issue">Engineering Issue</option>
              <option value="payment_investigation">Payment Investigation</option>
              <option value="compliance_request">Compliance Request</option>
              <option value="approval_request">Approval Request</option>
            </select>

            {/* Team Dropdown */}
            <select
              value={teamId || ''}
              onChange={(e) => updateFilter({ team_id: e.target.value || undefined, page: 1 })}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Teams</option>
              {(teams || []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>

            {/* Assignment Dropdown */}
            <select
              value={assigneeId || ''}
              onChange={(e) => updateFilter({ assignee_id: e.target.value || undefined, page: 1 })}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Any Assignee</option>
              <option value="unassigned">Unassigned Only</option>
              {user && <option value={user.id}>Assigned to Me</option>}
            </select>
          </div>
        </div>

        {/* Work Items Table */}
        <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-text-secondary">
              <div className="inline-block animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mb-2" />
              <p>Loading work items from database...</p>
            </div>
          ) : isError ? (
            <div className="p-12 text-center text-xs text-danger">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-danger" />
              <p className="font-semibold">Failed to load work items</p>
              <p className="text-text-secondary mt-1">{(error as any)?.message}</p>
              <button
                onClick={() => refetch()}
                className="mt-3 px-3 py-1.5 bg-primary text-white text-xs font-semibold rounded-lg"
              >
                Retry
              </button>
            </div>
          ) : !workItemsData || workItemsData.items.length === 0 ? (
            <div className="p-16 text-center">
              <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3 text-text-secondary">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-text-primary">No work items found</h3>
              <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                {hasActiveFilters
                  ? 'Try adjusting your filters or search terms to find what you are looking for.'
                  : 'Get started by creating your first work item in the system.'}
              </p>
              {hasActiveFilters ? (
                <button
                  onClick={clearAllFilters}
                  className="mt-4 px-3 py-1.5 bg-background border border-border text-xs font-semibold rounded-lg hover:bg-gray-100"
                >
                  Clear Filters
                </button>
              ) : (
                user?.role !== 'VIEWER' && (
                  <button
                    onClick={() => navigate('/work-items/new')}
                    className="mt-4 px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg shadow-sm"
                  >
                    Create Work Item
                  </button>
                )
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-background/50 text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                    <th
                      onClick={() => handleSort('key')}
                      className="py-3 px-4 cursor-pointer hover:text-text-primary select-none"
                    >
                      <div className="flex items-center gap-1">
                        <span>Key</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3 px-4">Title</th>
                    <th className="py-3 px-4">Type</th>
                    <th
                      onClick={() => handleSort('status')}
                      className="py-3 px-4 cursor-pointer hover:text-text-primary select-none"
                    >
                      <div className="flex items-center gap-1">
                        <span>Status</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('priority')}
                      className="py-3 px-4 cursor-pointer hover:text-text-primary select-none"
                    >
                      <div className="flex items-center gap-1">
                        <span>Priority</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3 px-4">Team</th>
                    <th className="py-3 px-4">Assignee</th>
                    <th
                      onClick={() => handleSort('due_at')}
                      className="py-3 px-4 cursor-pointer hover:text-text-primary select-none"
                    >
                      <div className="flex items-center gap-1">
                        <span>Due Date</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('updated_at')}
                      className="py-3 px-4 cursor-pointer hover:text-text-primary select-none text-right"
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Updated</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-xs">
                  {workItemsData.items.map((item) => {
                    const isOverdue =
                      item.due_at &&
                      new Date(item.due_at) < new Date() &&
                      item.status !== 'RESOLVED' &&
                      item.status !== 'CLOSED';

                    return (
                      <tr
                        key={item.id}
                        onClick={() => navigate(`/work-items/${item.id}`)}
                        className="hover:bg-primary-light/30 cursor-pointer transition-colors group"
                      >
                        <td className="py-3 px-4 font-mono font-bold text-primary group-hover:underline">
                          {item.key}
                        </td>
                        <td className="py-3 px-4 font-medium text-text-primary max-w-xs truncate">
                          {item.title}
                        </td>
                        <td className="py-3 px-4">
                          <WorkTypeBadge workType={item.work_type} />
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={item.status} size="sm" />
                        </td>
                        <td className="py-3 px-4">
                          <PriorityBadge priority={item.priority} size="sm" />
                        </td>
                        <td className="py-3 px-4 text-text-secondary font-medium">
                          {item.team?.name || '—'}
                        </td>
                        <td className="py-3 px-4 text-text-primary">
                          {item.assignee ? (
                            <span className="font-medium text-text-primary">{item.assignee.name}</span>
                          ) : (
                            <span className="text-amber-600 font-semibold bg-amber-50 px-2 py-0.5 rounded text-[11px] border border-amber-200">
                              Unassigned
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {item.due_at ? (
                            <span
                              className={`text-xs ${
                                isOverdue ? 'text-danger font-bold' : 'text-text-secondary'
                              }`}
                            >
                              {new Date(item.due_at).toLocaleDateString()}
                              {isOverdue && ' (Overdue)'}
                            </span>
                          ) : (
                            <span className="text-text-secondary/50">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right text-text-secondary font-mono text-[11px]">
                          {new Date(item.updated_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {workItemsData && workItemsData.total_pages > 1 && (
            <div className="px-5 py-3 border-t border-border bg-background/50 flex items-center justify-between text-xs text-text-secondary">
              <div>
                Showing{' '}
                <span className="font-semibold text-text-primary">
                  {(page - 1) * 15 + 1}
                </span>{' '}
                to{' '}
                <span className="font-semibold text-text-primary">
                  {Math.min(page * 15, workItemsData.total)}
                </span>{' '}
                of{' '}
                <span className="font-semibold text-text-primary">{workItemsData.total}</span>{' '}
                items
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => updateFilter({ page: page - 1 })}
                  disabled={page <= 1}
                  className="px-2.5 py-1.5 bg-surface border border-border rounded-md text-text-primary disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50 flex items-center gap-1 font-medium"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Previous
                </button>
                <span className="px-2 font-medium">
                  Page {page} of {workItemsData.total_pages}
                </span>
                <button
                  onClick={() => updateFilter({ page: page + 1 })}
                  disabled={page >= workItemsData.total_pages}
                  className="px-2.5 py-1.5 bg-surface border border-border rounded-md text-text-primary disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50 flex items-center gap-1 font-medium"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
