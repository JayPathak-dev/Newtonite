import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { useAuth } from '../context/AuthContext';

export const MyWorkPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: items, isLoading } = useQuery({
    queryKey: ['myWork', user?.id],
    queryFn: api.dashboard.getMyWork,
  });

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="My Work"
        subtitle={`Items currently assigned to ${user?.name}`}
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-4">
        <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-text-secondary">Loading your items...</div>
          ) : !items || items.length === 0 ? (
            <div className="p-16 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-text-primary">No assigned work</h3>
              <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                You currently have no open work items assigned to you. Check the unassigned items queue in All Work Items to claim new work.
              </p>
              <button
                onClick={() => navigate('/work-items?assignee_id=unassigned')}
                className="mt-4 px-3 py-1.5 bg-primary text-white text-xs font-semibold rounded-lg shadow-sm"
              >
                Browse Unassigned Items
              </button>
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
                    <p className="text-xs text-text-secondary">Team: {item.team_name || '—'}</p>
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
