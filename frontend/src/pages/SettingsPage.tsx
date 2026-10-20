import React from 'react';
import { User, Shield, Check, X, Key, Info } from 'lucide-react';
import { Header } from '../components/Header';
import { useAuth } from '../context/AuthContext';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();

  const permissionsMatrix = [
    { action: 'View assigned & permitted team work items', admin: true, lead: true, user: true, viewer: true },
    { action: 'Search & filter operational inventory', admin: true, lead: true, user: true, viewer: true },
    { action: 'Create work items in permitted teams', admin: true, lead: true, user: true, viewer: false },
    { action: 'Update title, description, priority', admin: true, lead: true, user: true, viewer: false },
    { action: 'Claim unassigned work items (atomic)', admin: true, lead: true, user: true, viewer: false },
    { action: 'Reassign work items to team members', admin: true, lead: true, user: true, viewer: false },
    { action: 'Advance status transitions (workflow rules)', admin: true, lead: true, user: true, viewer: false },
    { action: 'Add comments and discussion notes', admin: true, lead: true, user: true, viewer: false },
    { action: 'Approve or reject high-value financial requests', admin: true, lead: true, user: false, viewer: false },
    { action: 'Global cross-team access (all departments)', admin: true, lead: false, user: false, viewer: false },
  ];

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Settings & Access Control"
        subtitle="User profile, team assignments, and server-enforced authorization policies"
      />

      <div className="flex-1 p-6 max-w-5xl w-full mx-auto space-y-6">
        {/* Profile Card */}
        <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <User className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-bold text-text-primary">Current Session Profile</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-background rounded-lg border border-border">
              <span className="text-text-secondary block mb-1">Full Name</span>
              <span className="font-bold text-text-primary text-sm">{user?.name}</span>
            </div>

            <div className="p-3 bg-background rounded-lg border border-border">
              <span className="text-text-secondary block mb-1">Email Address</span>
              <span className="font-mono text-text-primary">{user?.email}</span>
            </div>

            <div className="p-3 bg-background rounded-lg border border-border">
              <span className="text-text-secondary block mb-1">System Role</span>
              <span
                className={`inline-block font-bold px-2 py-0.5 rounded text-xs mt-0.5 ${
                  user?.role === 'ADMIN'
                    ? 'bg-purple-100 text-purple-700'
                    : user?.role === 'VIEWER'
                    ? 'bg-gray-100 text-gray-700'
                    : 'bg-blue-100 text-blue-700'
                }`}
              >
                {user?.role}
              </span>
            </div>
          </div>

          {/* Team Memberships */}
          <div className="pt-2">
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider block mb-2">
              Team Memberships & Local Roles
            </span>
            <div className="flex flex-wrap gap-2">
              {user?.team_memberships.map((m) => (
                <div
                  key={m.team_id}
                  className="px-3 py-1.5 bg-background border border-border rounded-lg text-xs flex items-center gap-2"
                >
                  <span className="font-semibold text-text-primary">{m.team_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 bg-primary/10 text-primary font-bold rounded">
                    {m.team_role}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RBAC Matrix Card */}
        <div className="bg-surface rounded-xl border border-border shadow-subtle p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-bold text-text-primary">
                Role-Based Access Control (RBAC) Specification
              </h3>
            </div>
            <span className="text-xs text-text-secondary flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-primary" />
              Server-enforced on every API endpoint
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-background/50 text-[11px] font-semibold text-text-secondary uppercase">
                  <th className="py-2.5 px-3">Operation / Capability</th>
                  <th className="py-2.5 px-3 text-center">Admin</th>
                  <th className="py-2.5 px-3 text-center">Team Lead</th>
                  <th className="py-2.5 px-3 text-center">Team Member</th>
                  <th className="py-2.5 px-3 text-center">Viewer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {permissionsMatrix.map((row, idx) => (
                  <tr key={idx} className="hover:bg-background/50">
                    <td className="py-2.5 px-3 font-medium text-text-primary">{row.action}</td>
                    <td className="py-2.5 px-3 text-center">
                      {row.admin ? (
                        <Check className="w-4 h-4 text-emerald-600 mx-auto" />
                      ) : (
                        <X className="w-4 h-4 text-gray-300 mx-auto" />
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {row.lead ? (
                        <Check className="w-4 h-4 text-emerald-600 mx-auto" />
                      ) : (
                        <X className="w-4 h-4 text-gray-300 mx-auto" />
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {row.user ? (
                        <Check className="w-4 h-4 text-emerald-600 mx-auto" />
                      ) : (
                        <X className="w-4 h-4 text-gray-300 mx-auto" />
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {row.viewer ? (
                        <Check className="w-4 h-4 text-emerald-600 mx-auto" />
                      ) : (
                        <X className="w-4 h-4 text-red-500 mx-auto" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
