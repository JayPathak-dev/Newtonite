import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Search, Plus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/work-items?search=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  const isViewer = user?.role === 'VIEWER';

  return (
    <header className="h-16 bg-surface border-b border-border px-6 flex items-center justify-between shrink-0">
      {/* Title & Context */}
      <div>
        <h1 className="text-lg font-bold text-text-primary">
          {title || 'Newtonite Ops'}
        </h1>
        {subtitle && (
          <p className="text-xs text-text-secondary">{subtitle}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        {/* Global Search */}
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search key, title, or details..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-64 pl-9 pr-3 py-1.5 text-xs bg-background border border-border rounded-lg text-text-primary placeholder-text-secondary/70 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
          />
        </form>

        {/* Create Work Item CTA */}
        {!isViewer && (
          <button
            onClick={() => navigate('/work-items/new')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary-hover text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Item</span>
          </button>
        )}
      </div>
    </header>
  );
};
