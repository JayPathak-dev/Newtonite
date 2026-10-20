import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  Clock,
  UserX,
  FileCheck2,
  FolderOpen,
  ArrowRight,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { useAuth } from '../context/AuthContext';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const {
    data: summary,
    isLoading: loadingSummary,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['dashboardSummary', user?.id],
    queryFn: api.dashboard.getSummary,
  });

  const {
    data: breakdown,
    isLoading: loadingBreakdown,
  } = useQuery({
    queryKey: ['statusBreakdown', user?.id],
    queryFn: api.dashboard.getStatusBreakdown,
  });

  const {
    data: attentionItems,
    isLoading: loadingAttention,
  } = useQuery({
    queryKey: ['needsAttention', user?.id],
    queryFn: api.dashboard.getNeedsAttention,
  });

  const {
    data: myItems,
    isLoading: loadingMyWork,
  } = useQuery({
    queryKey: ['myWork', user?.id],
    queryFn: api.dashboard.getMyWork,
  });

  const {
    data: recentActivityItems,
    isLoading: loadingRecent,
  } = useQuery({
    queryKey: ['recentActivityItems', user?.id],
    queryFn: api.dashboard.getRecentActivity,
  });

  const metricCards = [
    {
      title: 'Open Items',
      value: summary?.open_items ?? 0,
      icon: FolderOpen,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      border: 'border-blue-100',
      onClick: () => navigate('/work-items?status=OPEN'),
    },
    {
      title: 'Critical Priority',
      value: summary?.critical_items ?? 0,
      icon: AlertOctagon,
      color: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-100',
      onClick: () => navigate('/work-items?priority=CRITICAL'),
    },
    {
      title: 'Unassigned',
      value: summary?.unassigned_items ?? 0,
      icon: UserX,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-100',
      onClick: () => navigate('/work-items?assignee_id=unassigned'),
    },
    {
      title: 'Overdue Items',
      value: summary?.overdue_items ?? 0,
      icon: Clock,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      border: 'border-orange-100',
      onClick: () => navigate('/work-items?overdue=true'),
    },
    {
      title: 'Pending Approvals',
      value: summary?.pending_approvals ?? 0,
      icon: FileCheck2,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      border: 'border-purple-100',
      onClick: () => navigate('/approvals'),
    },
  ];

  const STATUS_COLORS: Record<string, string> = {
    OPEN: '#3B82F6',
    IN_PROGRESS: '#6366F1',
    BLOCKED: '#F59E0B',
    IN_REVIEW: '#A855F7',
    RESOLVED: '#10B981',
    CLOSED: '#9CA3AF',
  };

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Operational Dashboard"
        subtitle={`Real-time work statistics scoped to ${user?.name}'s permissions`}
      />

      <div className="flex-1 p-6 space-y-6 max-w-7xl w-full mx-auto">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {metricCards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.title}
                onClick={card.onClick}
                className={`bg-surface p-4 rounded-xl border ${card.border} shadow-subtle hover:shadow-card transition-all cursor-pointer flex flex-col justify-between group`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-text-secondary">{card.title}</span>
                  <div className={`p-2 rounded-lg ${card.bg}`}>
                    <Icon className={`w-4 h-4 ${card.color}`} />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-text-primary tracking-tight">
                    {loadingSummary ? '...' : card.value}
                  </span>
                  <ArrowRight className="w-4 h-4 text-text-secondary opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Charts & Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Breakdown Bar Chart */}
          <div className="lg:col-span-2 bg-surface p-5 rounded-xl border border-border shadow-subtle flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-primary" />
                  Work Items by Status
                </h3>
                <p className="text-xs text-text-secondary">Current workload distribution in permitted teams</p>
              </div>
              <button
                onClick={() => refetchSummary()}
                className="p-1.5 text-text-secondary hover:text-text-primary rounded-md hover:bg-background transition-colors"
                title="Refresh Metrics"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-56 w-full">
              {loadingBreakdown ? (
                <div className="h-full flex items-center justify-center text-xs text-text-secondary">
                  Loading metrics...
                </div>
              ) : !breakdown || breakdown.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-text-secondary">
                  No work items recorded
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdown} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis
                      dataKey="status"
                      tick={{ fontSize: 11, fill: '#6B7280' }}
                      tickLine={false}
                      axisLine={{ stroke: '#E5E7EB' }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 11, fill: '#6B7280' }}
                      tickLine={false}
                      axisLine={{ stroke: '#E5E7EB' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={36}>
                      {breakdown.map((entry) => (
                        <Cell
                          key={`cell-${entry.status}`}
                          fill={STATUS_COLORS[entry.status] || '#4F46E5'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Quick Summary / Status Chips */}
          <div className="bg-surface p-5 rounded-xl border border-border shadow-subtle flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-text-primary mb-1">Status Overview</h3>
              <p className="text-xs text-text-secondary mb-4">Direct click to filter list</p>

              <div className="space-y-2.5">
                {(breakdown || []).map((b) => (
                  <div
                    key={b.status}
                    onClick={() => navigate(`/work-items?status=${b.status}`)}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-background cursor-pointer transition-colors group"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: STATUS_COLORS[b.status] || '#9CA3AF' }}
                      />
                      <span className="text-xs font-semibold text-text-primary group-hover:text-primary transition-colors">
                        {b.status}
                      </span>
                    </div>
                    <span className="text-xs font-bold text-text-secondary bg-gray-100 px-2 py-0.5 rounded-full">
                      {b.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => navigate('/work-items')}
              className="mt-4 w-full py-2 bg-background hover:bg-gray-100 text-xs font-semibold text-text-primary border border-border rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <span>View All Items</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Two-column Bottom Tables: Needs Attention & My Work */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Needs Attention Table */}
          <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden flex flex-col">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-danger" />
                  Needs Immediate Attention
                </h3>
                <p className="text-xs text-text-secondary">Critical, blocked, or overdue work items</p>
              </div>
              <button
                onClick={() => navigate('/inbox')}
                className="text-xs font-semibold text-primary hover:text-primary-hover"
              >
                Open Inbox
              </button>
            </div>

            <div className="divide-y divide-border flex-1 overflow-y-auto max-h-80">
              {loadingAttention ? (
                <div className="p-6 text-center text-xs text-text-secondary">Loading attention items...</div>
              ) : !attentionItems || attentionItems.length === 0 ? (
                <div className="p-8 text-center text-xs text-text-secondary">
                  🎉 No urgent items needing immediate attention!
                </div>
              ) : (
                attentionItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => navigate(`/work-items/${item.id}`)}
                    className="p-3.5 hover:bg-background/80 transition-colors cursor-pointer flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-primary font-mono">{item.key}</span>
                        <StatusBadge status={item.status} size="sm" />
                        <PriorityBadge priority={item.priority} size="sm" />
                      </div>
                      <h4 className="text-xs font-medium text-text-primary truncate">{item.title}</h4>
                    </div>
                    <ArrowRight className="w-4 h-4 text-text-secondary shrink-0" />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* My Work / Assigned Items */}
          <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden flex flex-col">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
                  <FolderOpen className="w-4 h-4 text-primary" />
                  Assigned to Me
                </h3>
                <p className="text-xs text-text-secondary">Active tasks assigned to {user?.name}</p>
              </div>
              <button
                onClick={() => navigate('/my-work')}
                className="text-xs font-semibold text-primary hover:text-primary-hover"
              >
                View All
              </button>
            </div>

            <div className="divide-y divide-border flex-1 overflow-y-auto max-h-80">
              {loadingMyWork ? (
                <div className="p-6 text-center text-xs text-text-secondary">Loading your items...</div>
              ) : !myItems || myItems.length === 0 ? (
                <div className="p-8 text-center text-xs text-text-secondary">
                  No active work items currently assigned to you.
                </div>
              ) : (
                myItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => navigate(`/work-items/${item.id}`)}
                    className="p-3.5 hover:bg-background/80 transition-colors cursor-pointer flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-primary font-mono">{item.key}</span>
                        <StatusBadge status={item.status} size="sm" />
                        <PriorityBadge priority={item.priority} size="sm" />
                        <WorkTypeBadge workType={item.work_type} />
                      </div>
                      <h4 className="text-xs font-medium text-text-primary truncate">{item.title}</h4>
                    </div>
                    <ArrowRight className="w-4 h-4 text-text-secondary shrink-0" />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
