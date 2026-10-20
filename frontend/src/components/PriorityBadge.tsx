import React from 'react';
import { AlertCircle, ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { WorkItemPriority } from '../types';

interface PriorityBadgeProps {
  priority: WorkItemPriority;
  size?: 'sm' | 'md';
  hideIcon?: boolean;
}

const priorityConfig: Record<
  WorkItemPriority,
  { label: string; bg: string; text: string; icon: React.ReactNode; border: string }
> = {
  CRITICAL: {
    label: 'Critical',
    bg: 'bg-red-50',
    text: 'text-red-700',
    icon: <AlertCircle className="w-3.5 h-3.5 text-red-600" />,
    border: 'border-red-200',
  },
  HIGH: {
    label: 'High',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    icon: <ArrowUp className="w-3.5 h-3.5 text-orange-600" />,
    border: 'border-orange-200',
  },
  MEDIUM: {
    label: 'Medium',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    icon: <Minus className="w-3.5 h-3.5 text-blue-600" />,
    border: 'border-blue-200',
  },
  LOW: {
    label: 'Low',
    bg: 'bg-gray-50',
    text: 'text-gray-600',
    icon: <ArrowDown className="w-3.5 h-3.5 text-gray-500" />,
    border: 'border-gray-200',
  },
};

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  size = 'sm',
  hideIcon = false,
}) => {
  const config = priorityConfig[priority] || priorityConfig.MEDIUM;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-medium border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {!hideIcon && config.icon}
      {config.label}
    </span>
  );
};
