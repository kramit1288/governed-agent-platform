"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import type { ApprovalResponse } from "../lib/api";
import { resolveApproval } from "../lib/api";

type ApprovalCardProps = {
  approval: ApprovalResponse;
  actionable?: boolean;
};

export function ApprovalCard({ approval, actionable = false }: ApprovalCardProps) {
  const router = useRouter();
  const [currentApproval, setCurrentApproval] = useState(approval);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | null>(null);

  async function handleDecision(decision: "approve" | "reject") {
    try {
      setPendingAction(decision);
      setError(null);
      const updated = await resolveApproval(currentApproval.id, decision);
      setCurrentApproval(updated);
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to resolve approval.");
    } finally {
      setPendingAction(null);
    }
  }

  const statusClass = statusClassName(currentApproval.status);

  return (
    <section className="panel stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Approval</p>
          <h3>{currentApproval.reason}</h3>
        </div>
        <span className={`status-badge ${statusClass}`}>{currentApproval.status}</span>
      </div>

      <div className="meta-grid">
        <div>
          <span className="meta-label">Approval ID</span>
          <p className="meta-value">{currentApproval.id}</p>
        </div>
        <div>
          <span className="meta-label">Run ID</span>
          <p className="meta-value">{currentApproval.run_id}</p>
        </div>
        <div>
          <span className="meta-label">Requested At</span>
          <p className="meta-value">{new Date(currentApproval.requested_at).toLocaleString()}</p>
        </div>
      </div>

      <div>
        <span className="meta-label">Action Preview</span>
        <pre className="payload">
          {JSON.stringify(currentApproval.action_preview ?? {}, null, 2)}
        </pre>
      </div>

      {currentApproval.resume_result ? (
        <div className="notice">
          Resume state: {currentApproval.resume_result.run_state ?? "unknown"}
          {currentApproval.resume_result.response_text ? ` | ${currentApproval.resume_result.response_text}` : ""}
        </div>
      ) : null}

      {error ? <div className="error">{error}</div> : null}

      <div className="button-row">
        <Link className="link-button" href={`/runs/${currentApproval.run_id}`}>
          View run
        </Link>
        {!actionable || currentApproval.status !== "PENDING" ? null : (
          <>
            <button
              className="button success"
              disabled={pendingAction !== null}
              onClick={() => handleDecision("approve")}
              type="button"
            >
              {pendingAction === "approve" ? "Approving..." : "Approve"}
            </button>
            <button
              className="button danger"
              disabled={pendingAction !== null}
              onClick={() => handleDecision("reject")}
              type="button"
            >
              {pendingAction === "reject" ? "Rejecting..." : "Reject"}
            </button>
          </>
        )}
      </div>
    </section>
  );
}

function statusClassName(status: string): string {
  if (status === "PENDING") {
    return "status-waiting";
  }
  if (status === "APPROVED") {
    return "status-completed";
  }
  return "status-rejected";
}
