import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Inbox as InboxIcon, AlertOctagon, ArrowRight } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { useAuth } from '../context/AuthContext';

export const InboxPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: items, isLoading } = useQuery({
    queryKey: ['needsAttention', user?.id],
    queryFn: api.dashboard.getNeedsAttention,
  });

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Inbox"
        subtitle="Work items requiring immediate operational review, unblocking, or resolution"
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-4">
        <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden">
          <div className="p-4 border-b border-border bg-background/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-danger" />
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                Action Required Items
              </h3>
            </div>
            <span className="text-xs text-text-secondary font-medium">
              {items?.length || 0} urgent items
            </span>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-xs text-text-secondary">Loading inbox items...</div>
          ) : !items || items.length === 0 ? (
            <div className="p-16 text-center">
              <InboxIcon className="w-10 h-10 text-primary mx-auto mb-2 opacity-60" />
              <h3 className="text-sm font-bold text-text-primary">Inbox is Clear</h3>
              <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                No items in your teams are currently marked as critical, blocked, or overdue.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/work-items/${item.id}`)}
                  className="p-4 hover:bg-background/80 transition-colors cursor-pointer flex items-center justify-between gap-4"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-primary">{item.key}</span>
                      <StatusBadge status={item.status} size="sm" />
                      <PriorityBadge priority={item.priority} size="sm" />
                      <WorkTypeBadge workType={item.work_type} />
                    </div>
                    <h4 className="text-sm font-semibold text-text-primary truncate">{item.title}</h4>
                    <div className="flex items-center gap-4 text-xs text-text-secondary">
                      <span>Team: {item.team_name || '—'}</span>
                      <span>Assignee: {item.assignee_name || 'Unassigned'}</span>
                      {item.due_at && (
                        <span className="text-danger font-medium">
                          Due: {new Date(item.due_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-text-secondary shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
