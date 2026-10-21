import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { WorkItemStatus, WorkItemPriority, WorkType } from '../types';

describe('Badges and Status presentation', () => {
  it('renders status badges with appropriate labels and colors', () => {
    const { rerender } = render(<StatusBadge status="OPEN" />);
    expect(screen.getByText('Open')).toBeInTheDocument();

    rerender(<StatusBadge status="IN_PROGRESS" />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();

    rerender(<StatusBadge status="BLOCKED" />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();

    rerender(<StatusBadge status="RESOLVED" />);
    expect(screen.getByText('Resolved')).toBeInTheDocument();
  });

  it('renders priority badges with correct accessibility indicators', () => {
    const { rerender } = render(<PriorityBadge priority="CRITICAL" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();

    rerender(<PriorityBadge priority="HIGH" />);
    expect(screen.getByText('High')).toBeInTheDocument();

    rerender(<PriorityBadge priority="LOW" />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('renders human readable work type labels', () => {
    const { rerender } = render(<WorkTypeBadge workType="payment_investigation" />);
    expect(screen.getByText('Payment')).toBeInTheDocument();

    rerender(<WorkTypeBadge workType="compliance_request" />);
    expect(screen.getByText('Compliance')).toBeInTheDocument();
  });
});


