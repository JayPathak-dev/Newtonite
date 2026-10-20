import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Users2, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { useAuth } from '../context/AuthContext';

export const TeamsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: teams, isLoading } = useQuery({
    queryKey: ['teamsList', user?.id],
    queryFn: api.teams.list,
  });

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Teams"
        subtitle="Operational departments and cross-functional working groups"
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-4">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-text-secondary">Loading teams...</div>
        ) : !teams || teams.length === 0 ? (
          <div className="p-16 text-center bg-surface rounded-xl border border-border">
            <Users2 className="w-10 h-10 text-primary mx-auto mb-2 opacity-60" />
            <h3 className="text-sm font-bold text-text-primary">No Teams Accessible</h3>
            <p className="text-xs text-text-secondary mt-1">
              Your account is not assigned to any active teams yet.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {teams.map((team) => (
              <div
                key={team.id}
                onClick={() => navigate(`/teams/${team.id}`)}
                className="bg-surface p-5 rounded-xl border border-border shadow-subtle hover:shadow-card cursor-pointer transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-primary font-mono bg-primary-light px-2.5 py-0.5 rounded">
                      TEAM
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3" />
                      Active
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-text-primary group-hover:text-primary transition-colors">
                    {team.name}
                  </h3>
                  <p className="text-xs text-text-secondary mt-1.5 leading-relaxed line-clamp-3">
                    {team.description || 'No description provided.'}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs text-text-secondary">
                  <span className="font-medium">{team.member_count ?? '—'} Members</span>
                  <div className="flex items-center gap-1 text-primary font-semibold group-hover:translate-x-1 transition-transform">
                    <span>View Team</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
