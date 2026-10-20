import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ConflictBannerProps {
  message: string;
  onReload: () => void;
  isLoading?: boolean;
}

export const ConflictBanner: React.FC<ConflictBannerProps> = ({
  message,
  onReload,
  isLoading = false,
}) => {
  return (
    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-4 shadow-sm animate-pulse-once">
      <div className="flex items-start gap-3">
        <div className="p-1 bg-amber-100 rounded-md text-amber-700 mt-0.5">
          <AlertTriangle className="w-5 h-5 text-amber-700" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-amber-900">
            Concurrent Modification Conflict
          </h4>
          <p className="text-sm text-amber-800 mt-0.5 leading-relaxed">
            {message}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={onReload}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-700 hover:bg-amber-800 rounded-md shadow-sm transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              Reload Latest Version
            </button>
            <span className="text-xs text-amber-700">
              Reloading ensures you don't accidentally overwrite changes made by another team member.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
