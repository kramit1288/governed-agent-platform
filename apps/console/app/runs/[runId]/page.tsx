import Link from "next/link";
import { notFound } from "next/navigation";

import { ApprovalCard } from "../../components/ApprovalCard";
import { TraceTimeline } from "../../components/TraceTimeline";
import { getApproval, getRun, getRunTrace } from "../../lib/api";

type RunDetailPageProps = {
  params: { runId: string };
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { runId } = params;

  try {
    const run = await getRun(runId);
    const trace = await getRunTrace(runId);
    const approval = run.approval_request_id ? await getApproval(run.approval_request_id) : null;

    return (
      <main className="grid">
        <section className="panel stack">
          <div className="page-header">
            <div>
              <p className="eyebrow">Run</p>
              <h2>{run.workflow_key}</h2>
            </div>
            <span className={`status-badge ${runStatusClassName(run.status)}`}>{run.status}</span>
          </div>
          <div className="meta-grid">
            <div>
              <span className="meta-label">Run ID</span>
              <p className="meta-value">{run.run_id}</p>
            </div>
            <div>
              <span className="meta-label">Approval request</span>
              <p className="meta-value">{run.approval_request_id ?? "none"}</p>
            </div>
          </div>
          <div>
            <span className="meta-label">User input</span>
            <p className="meta-value">{run.user_input ?? "none"}</p>
          </div>
          <div>
            <span className="meta-label">Run output</span>
            <p className="meta-value">{run.response_text ?? run.last_error ?? "No output yet."}</p>
          </div>
          <div className="button-row">
            <Link className="link-button" href="/">
              Back to home
            </Link>
            {run.approval_request_id ? (
              <Link className="link-button" href={`/approvals/${run.approval_request_id}`}>
                Open approval
              </Link>
            ) : null}
          </div>
        </section>

        {approval ? <ApprovalCard approval={approval} /> : null}
        <TraceTimeline timeline={trace} />
      </main>
    );
  } catch {
    notFound();
  }
}

function runStatusClassName(status: string): string {
  if (status === "COMPLETED") {
    return "status-completed";
  }
  if (status === "WAITING_FOR_APPROVAL") {
    return "status-waiting";
  }
  if (status === "FAILED") {
    return "status-failed";
  }
  if (status === "CANCELED") {
    return "status-canceled";
  }
  return "status-progress";
}
