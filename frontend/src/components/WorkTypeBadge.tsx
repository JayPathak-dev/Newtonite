import React from 'react';
import {
  AlertTriangle,
  CheckSquare,
  Users,
  Cpu,
  CreditCard,
  ShieldCheck,
  FileCheck,
} from 'lucide-react';
import { WorkType } from '../types';

interface WorkTypeBadgeProps {
  workType: WorkType;
}

const typeConfig: Record<
  WorkType,
  { label: string; icon: React.ReactNode; bg: string; text: string }
> = {
  incident: {
    label: 'Incident',
    icon: <AlertTriangle className="w-3 h-3 text-red-500" />,
    bg: 'bg-red-50',
    text: 'text-red-700',
  },
  task: {
    label: 'Task',
    icon: <CheckSquare className="w-3 h-3 text-gray-500" />,
    bg: 'bg-gray-50',
    text: 'text-gray-700',
  },
  customer_issue: {
    label: 'Customer Issue',
    icon: <Users className="w-3 h-3 text-blue-500" />,
    bg: 'bg-blue-50',
    text: 'text-blue-700',
  },
  engineering_issue: {
    label: 'Engineering',
    icon: <Cpu className="w-3 h-3 text-purple-500" />,
    bg: 'bg-purple-50',
    text: 'text-purple-700',
  },
  payment_investigation: {
    label: 'Payment',
    icon: <CreditCard className="w-3 h-3 text-emerald-600" />,
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
  },
  compliance_request: {
    label: 'Compliance',
    icon: <ShieldCheck className="w-3 h-3 text-amber-600" />,
    bg: 'bg-amber-50',
    text: 'text-amber-800',
  },
  approval_request: {
    label: 'Approval Request',
    icon: <FileCheck className="w-3 h-3 text-indigo-600" />,
    bg: 'bg-indigo-50',
    text: 'text-indigo-700',
  },
};

export const WorkTypeBadge: React.FC<WorkTypeBadgeProps> = ({ workType }) => {
  const config = typeConfig[workType] || typeConfig.task;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border border-border ${config.bg} ${config.text}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
};
