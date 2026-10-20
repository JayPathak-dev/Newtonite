import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layers, ShieldCheck, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('Password123!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // If already logged in, redirect
  if (user) {
    const from = (location.state as any)?.from?.pathname || '/dashboard';
    navigate(from, { replace: true });
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (userEmail: string) => {
    setEmail(userEmail);
    setPassword('Password123!');
    setError(null);
  };

  const demoPresets = [
    {
      role: 'Admin',
      name: 'Alex Admin',
      email: 'admin@newtonite.internal',
      desc: 'System-wide administrative access',
      color: 'border-purple-200 bg-purple-50/50 hover:bg-purple-50',
      badge: 'bg-purple-100 text-purple-700',
    },
    {
      role: 'Payments Approver',
      name: 'Sarah Chen',
      email: 'sarah.payments@newtonite.internal',
      desc: 'Lead & approver for payments team',
      color: 'border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50',
      badge: 'bg-indigo-100 text-indigo-700',
    },
    {
      role: 'Payments Member',
      name: 'Alex Rivera',
      email: 'alex.payments@newtonite.internal',
      desc: 'Individual contributor in payments',
      color: 'border-blue-200 bg-blue-50/50 hover:bg-blue-50',
      badge: 'bg-blue-100 text-blue-700',
    },
    {
      role: 'Platform Lead',
      name: 'Marcus Vance',
      email: 'marcus.platform@newtonite.internal',
      desc: 'Infrastructure & platform operations',
      color: 'border-emerald-200 bg-emerald-50/50 hover:bg-emerald-50',
      badge: 'bg-emerald-100 text-emerald-700',
    },
    {
      role: 'Viewer',
      name: 'Valerie Viewer',
      email: 'viewer@newtonite.internal',
      desc: 'Read-only access across teams',
      color: 'border-gray-200 bg-gray-50/50 hover:bg-gray-100',
      badge: 'bg-gray-100 text-gray-700',
    },
    {
      role: 'Outsider',
      name: 'Oscar Outsider',
      email: 'outsider@newtonite.internal',
      desc: 'Customer Ops only (proves isolation)',
      color: 'border-amber-200 bg-amber-50/50 hover:bg-amber-50',
      badge: 'bg-amber-100 text-amber-700',
    },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center text-white shadow-md">
            <Layers className="w-7 h-7 text-white" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-text-primary">
          Newtonite <span className="text-primary">Ops</span>
        </h2>
        <p className="mt-1 text-center text-xs text-text-secondary">
          Internal Operational Work Management Platform
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-6 shadow-card border border-border sm:rounded-xl sm:px-10">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-danger-light border border-red-200 flex items-start gap-2.5 text-xs text-danger font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-text-primary mb-1">
                Email address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@newtonite.internal"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text-primary mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <span>Sign in</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials Switcher */}
          <div className="mt-6 pt-6 border-t border-border">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary mb-2.5">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span>Assessment Demo Accounts</span>
            </div>
            <p className="text-[11px] text-text-secondary mb-3 leading-relaxed">
              Click any demo persona to automatically fill credentials:
            </p>

            <div className="grid grid-cols-2 gap-2">
              {demoPresets.map((preset) => (
                <button
                  key={preset.email}
                  type="button"
                  onClick={() => fillCredentials(preset.email)}
                  className={`p-2 rounded-lg border text-left transition-all ${preset.color}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-text-primary">{preset.name}</span>
                  </div>
                  <span className={`inline-block text-[10px] px-1.5 py-0.2 rounded font-medium mt-1 ${preset.badge}`}>
                    {preset.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
