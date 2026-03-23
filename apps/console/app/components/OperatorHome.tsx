"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { createRun, runEvals } from "../lib/api";

export function OperatorHome() {
  const router = useRouter();
  const [query, setQuery] = useState("Summarize ticket T-100 for me.");
  const [tenantId, setTenantId] = useState("tenant-1");
  const [requestedBy, setRequestedBy] = useState("operator-1");
  const [workflowKey, setWorkflowKey] = useState("support.ticket");
  const [evalName, setEvalName] = useState("demo-suite");
  const [compareToLatest, setCompareToLatest] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"run" | "eval" | null>(null);

  async function handleCreateRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setPendingAction("run");
      setError(null);
      const run = await createRun({
        workflow_key: workflowKey,
        user_input: query,
        tenant_id: tenantId,
        requested_by: requestedBy,
      });
      router.push(`/runs/${run.run_id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create run.");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleRunEvals() {
    try {
      setPendingAction("eval");
      setError(null);
      const report = await runEvals({ name: evalName, compare_to_latest: compareToLatest });
      if (report.eval_run_id) {
        router.push(`/evals/${report.eval_run_id}`);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to start evals.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <main className="grid two">
      <section className="panel stack">
        <div>
          <p className="eyebrow">Runs</p>
          <h2>Create a Demo Run</h2>
          <p className="panel-muted">
            Submit a support or ops query, then inspect the final response, trace timeline,
            and any approval checkpoint.
          </p>
        </div>
        <form className="stack" onSubmit={handleCreateRun}>
          <div className="field">
            <label htmlFor="workflow-key">Workflow key</label>
            <input
              id="workflow-key"
              onChange={(event) => setWorkflowKey(event.target.value)}
              value={workflowKey}
            />
          </div>
          <div className="field">
            <label htmlFor="tenant-id">Tenant ID</label>
            <input
              id="tenant-id"
              onChange={(event) => setTenantId(event.target.value)}
              value={tenantId}
            />
          </div>
          <div className="field">
            <label htmlFor="requested-by">Requested by</label>
            <input
              id="requested-by"
              onChange={(event) => setRequestedBy(event.target.value)}
              value={requestedBy}
            />
          </div>
          <div className="field">
            <label htmlFor="query">Query</label>
            <textarea
              id="query"
              onChange={(event) => setQuery(event.target.value)}
              value={query}
            />
          </div>
          <div className="button-row">
            <button className="button" disabled={pendingAction !== null} type="submit">
              {pendingAction === "run" ? "Starting run..." : "Start run"}
            </button>
          </div>
        </form>
        <div className="notice">
          Try a risky path with: Draft a refund request for customer C-100 on ticket T-100 for
          42.50.
        </div>
      </section>

      <section className="panel stack">
        <div>
          <p className="eyebrow">Evals</p>
          <h2>Run Offline Regression Check</h2>
          <p className="panel-muted">
            Execute the curated V1 eval suite and open a readable summary report.
          </p>
        </div>
        <div className="field">
          <label htmlFor="eval-name">Eval run name</label>
          <input
            id="eval-name"
            onChange={(event) => setEvalName(event.target.value)}
            value={evalName}
          />
        </div>
        <label className="meta-label" htmlFor="compare-to-latest">
          <input
            checked={compareToLatest}
            id="compare-to-latest"
            onChange={(event) => setCompareToLatest(event.target.checked)}
            style={{ marginRight: 10 }}
            type="checkbox"
          />
          Compare against the latest completed run with the same name
        </label>
        <div className="button-row">
          <button
            className="button secondary"
            disabled={pendingAction !== null}
            onClick={handleRunEvals}
            type="button"
          >
            {pendingAction === "eval" ? "Running evals..." : "Run evals"}
          </button>
        </div>
        <div className="notice">
          The report includes pass/fail counts, per-dimension averages, and regression deltas
          when a baseline exists.
        </div>
        {error ? <div className="error">{error}</div> : null}
      </section>
    </main>
  );
}
