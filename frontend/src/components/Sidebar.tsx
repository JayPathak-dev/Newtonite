import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CheckCircle2,
  Inbox,
  ListTodo,
  FileCheck2,
  Users2,
  Settings,
  LogOut,
  ChevronDown,
  Layers,
  Shield,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const DEMO_ACCOUNTS = [
  { name: 'Alex Admin', email: 'admin@newtonite.internal', role: 'ADMIN', badge: 'Admin' },
  { name: 'Sarah Chen', email: 'sarah.payments@newtonite.internal', role: 'USER', badge: 'Payments Approver' },
  { name: 'Alex Rivera', email: 'alex.payments@newtonite.internal', role: 'USER', badge: 'Payments Member' },
  { name: 'Marcus Vance', email: 'marcus.platform@newtonite.internal', role: 'USER', badge: 'Platform Lead' },
  { name: 'Valerie Viewer', email: 'viewer@newtonite.internal', role: 'VIEWER', badge: 'Read-only Viewer' },
  { name: 'Oscar Outsider', email: 'outsider@newtonite.internal', role: 'USER', badge: 'Customer Ops Only' },
];

export const Sidebar: React.FC = () => {
  const { user, logout, quickSwitchUser } = useAuth();
  const navigate = useNavigate();
  const [showDemoSwitcher, setShowDemoSwitcher] = useState(false);
  const [switching, setSwitching] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleQuickSwitch = async (email: string) => {
    setSwitching(true);
    try {
      await quickSwitchUser(email);
      setShowDemoSwitcher(false);
      // Reload current page or navigate to dashboard to reflect permission changes
      navigate('/dashboard');
    } finally {
      setSwitching(false);
    }
  };

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/work-items', label: 'All Work Items', icon: ListTodo },
    { to: '/my-work', label: 'My Work', icon: CheckCircle2 },
    { to: '/inbox', label: 'Inbox', icon: Inbox },
    { to: '/approvals', label: 'Approvals', icon: FileCheck2 },
    { to: '/teams', label: 'Teams', icon: Users2 },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col h-screen select-none shrink-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-border gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-white shadow-sm font-bold text-lg">
          <Layers className="w-5 h-5 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-text-primary text-base tracking-tight flex items-center gap-1.5">
            Newtonite <span className="text-primary font-semibold">Ops</span>
          </span>
          <span className="text-xs text-text-secondary font-medium">Internal Work Platform</span>
        </div>
      </div>

      {/* Quick Demo Switcher Banner */}
      <div className="px-3 pt-3">
        <div className="bg-primary-light border border-indigo-200 rounded-lg p-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <Shield className="w-3.5 h-3.5" />
              <span>Demo Role Switcher</span>
            </div>
            <button
              onClick={() => setShowDemoSwitcher(!showDemoSwitcher)}
              className="text-xs text-primary hover:text-primary-hover font-medium flex items-center gap-0.5"
            >
              Switch <ChevronDown className={`w-3 h-3 transition-transform ${showDemoSwitcher ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {showDemoSwitcher && (
            <div className="mt-2.5 pt-2 border-t border-indigo-200/60 space-y-1">
              {DEMO_ACCOUNTS.map((acc) => {
                const isActive = user?.email === acc.email;
                return (
                  <button
                    key={acc.email}
                    onClick={() => handleQuickSwitch(acc.email)}
                    disabled={switching}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors flex items-center justify-between ${
                      isActive
                        ? 'bg-primary text-white font-semibold'
                        : 'text-text-primary hover:bg-white'
                    }`}
                  >
                    <span className="truncate">{acc.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                        isActive ? 'bg-white/20 text-white' : 'bg-gray-100 text-text-secondary'
                      }`}
                    >
                      {acc.badge}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-background'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-border bg-background/50">
        <div className="flex items-center justify-between p-2 rounded-lg bg-surface border border-border shadow-subtle">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-xs flex items-center justify-center shrink-0">
              {user?.name ? user.name.slice(0, 2).toUpperCase() : 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-text-primary truncate">{user?.name || 'User'}</p>
              <div className="flex items-center gap-1">
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.2 rounded ${
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
          </div>
          <button
            onClick={handleLogout}
            title="Log out"
            className="p-1.5 text-text-secondary hover:text-danger hover:bg-danger-light rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
