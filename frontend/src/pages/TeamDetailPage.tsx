import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Users, Shield, ListTodo, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { WorkItemsPage } from './WorkItemsPage';

export const TeamDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: team, isLoading, isError, error } = useQuery({
    queryKey: ['teamDetail', id],
    queryFn: () => (id ? api.teams.get(id) : Promise.reject('No ID')),
    enabled: Boolean(id),
  });

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs text-text-secondary">Loading team details...</div>
    );
  }

  if (isError || !team) {
    return (
      <div className="p-12 text-center text-xs text-danger">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-danger" />
        <h3 className="text-base font-bold text-text-primary">Team Not Accessible</h3>
        <p className="text-text-secondary mt-1">
          {(error as any)?.message || 'You do not have permission to access this team.'}
        </p>
        <button
          onClick={() => navigate('/teams')}
          className="mt-4 px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg"
        >
          Back to Teams
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title={team.name}
        subtitle={team.description || 'Team roster and operational workload'}
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        <button
          onClick={() => navigate('/teams')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>All Teams</span>
        </button>

        {/* Team Overview Card */}
        <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-text-primary">{team.name}</h2>
            <button
              onClick={() => navigate(`/work-items?team_id=${team.id}`)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary-light text-primary hover:bg-primary hover:text-white rounded-lg text-xs font-semibold transition-colors"
            >
              <ListTodo className="w-4 h-4" />
              <span>View Team Work Items</span>
            </button>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed max-w-2xl">
            {team.description}
          </p>
        </div>

        {/* Member Roster */}
        <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Users className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-bold text-text-primary">
              Team Members ({team.members?.length || 0})
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {team.members?.map((m) => (
              <div
                key={m.user_id}
                className="p-3.5 rounded-lg border border-border bg-background/50 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center shrink-0">
                    {m.user?.name ? m.user.name.slice(0, 2).toUpperCase() : 'U'}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-text-primary truncate">{m.user?.name}</p>
                    <p className="text-[10px] text-text-secondary truncate">{m.user?.email}</p>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    m.team_role === 'LEAD'
                      ? 'bg-purple-100 text-purple-700'
                      : m.team_role === 'APPROVER'
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {m.team_role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
