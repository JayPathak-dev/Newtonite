import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileCheck2, CheckCircle2, XCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { api } from '../lib/api';
import { Header } from '../components/Header';
import { PriorityBadge } from '../components/PriorityBadge';
import { WorkTypeBadge } from '../components/WorkTypeBadge';
import { useAuth } from '../context/AuthContext';
import { WorkItem } from '../types';

export const ApprovalsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [modalItem, setModalItem] = useState<{
    item: WorkItem;
    decision: 'approved' | 'rejected';
    explanation: string;
  } | null>(null);

  // Query work items with approval_status = 'pending'
  const { data: approvalsData, isLoading } = useQuery({
    queryKey: ['pendingApprovals', user?.id],
    queryFn: () => api.workItems.list({ approval_status: 'pending', page_size: 50 }),
  });

  const approvalMutation = useMutation({
    mutationFn: ({ itemId, decision, explanation }: { itemId: string; decision: 'approved' | 'rejected'; explanation?: string }) =>
      api.workItems.decideApproval(itemId, decision, explanation),
    onSuccess: () => {
      setModalItem(null);
      queryClient.invalidateQueries({ queryKey: ['pendingApprovals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] });
    },
  });

  const isApproverForTeam = (teamId: string) =>
    user?.role === 'ADMIN' ||
    user?.team_memberships.some(
      (m) => m.team_id === teamId && (m.team_role === 'APPROVER' || m.team_role === 'LEAD')
    );

  const pendingItems = approvalsData?.items || [];

  return (
    <div className="min-h-full flex flex-col">
      <Header
        title="Pending Approvals"
        subtitle="Operational and financial sign-offs awaiting team approver authorization"
      />

      <div className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-4">
        <div className="bg-surface rounded-xl border border-border shadow-subtle overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-text-secondary">Loading pending approvals...</div>
          ) : pendingItems.length === 0 ? (
            <div className="p-16 text-center">
              <ShieldCheck className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-text-primary">All Approvals Clear</h3>
              <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                No items are currently awaiting your approval. Any new high-value requests will appear here.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {pendingItems.map((item) => {
                const canDecide = isApproverForTeam(item.team_id);
                return (
                  <div
                    key={item.id}
                    className="p-4 hover:bg-background/80 transition-colors flex items-center justify-between gap-4"
                  >
                    <div
                      onClick={() => navigate(`/work-items/${item.id}`)}
                      className="min-w-0 flex-1 space-y-1 cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-primary">{item.key}</span>
                        <PriorityBadge priority={item.priority} size="sm" />
                        <WorkTypeBadge workType={item.work_type} />
                        <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.2 rounded">
                          PENDING APPROVAL
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-text-primary truncate">{item.title}</h4>
                      <p className="text-xs text-text-secondary">
                        Team: {item.team?.name || '—'} • Created by: {item.created_by?.name || '—'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {canDecide ? (
                        <>
                          <button
                            onClick={() => setModalItem({ item, decision: 'approved', explanation: '' })}
                            className="inline-flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                          <button
                            onClick={() => setModalItem({ item, decision: 'rejected', explanation: '' })}
                            className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </>
                      ) : (
                        <span className="text-[11px] text-text-secondary italic">
                          (Approver role required)
                        </span>
                      )}
                      <button
                        onClick={() => navigate(`/work-items/${item.id}`)}
                        className="p-1.5 text-text-secondary hover:text-text-primary rounded-lg hover:bg-gray-100"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Decision Modal */}
      {modalItem && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-surface rounded-xl border border-border shadow-modal max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-primary" />
              <span>
                Confirm {modalItem.decision === 'approved' ? 'Approval' : 'Rejection'} for {modalItem.item.key}
              </span>
            </h3>

            <p className="text-xs text-text-secondary leading-relaxed">
              Provide an explanation for the decision on "{modalItem.item.title}".
            </p>

            <textarea
              rows={3}
              placeholder="e.g., Audit verified: invoice matched against bank statement."
              value={modalItem.explanation}
              onChange={(e) => setModalItem({ ...modalItem, explanation: e.target.value })}
              className="w-full px-3 py-2 text-xs bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalItem(null)}
                className="px-3 py-1.5 border border-border rounded-lg text-xs font-semibold text-text-secondary hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() =>
                  approvalMutation.mutate({
                    itemId: modalItem.item.id,
                    decision: modalItem.decision,
                    explanation: modalItem.explanation,
                  })
                }
                disabled={approvalMutation.isPending}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold text-white shadow-sm ${
                  modalItem.decision === 'approved'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {approvalMutation.isPending
                  ? 'Submitting...'
                  : `Confirm ${modalItem.decision === 'approved' ? 'Approve' : 'Reject'}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
