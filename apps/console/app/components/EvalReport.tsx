import type { EvalRun } from "../lib/api";

type EvalReportProps = {
  report: EvalRun;
};

export function EvalReport({ report }: EvalReportProps) {
  return (
    <div className="grid">
      <section className="panel stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Offline Evals</p>
            <h2>{report.run_name}</h2>
          </div>
          <span className="status-badge status-progress">
            avg {report.average_score.toFixed(2)}
          </span>
        </div>
        <div className="report-grid">
          <Metric label="Cases" value={String(report.total_cases)} />
          <Metric label="Passed" value={String(report.passed_cases)} />
          <Metric label="Failed" value={String(report.failed_cases)} />
          <Metric label="Model" value={report.model_name ?? "unknown"} />
        </div>
        <div className="report-grid">
          {Object.entries(report.dimension_averages).map(([dimension, score]) => (
            <Metric key={dimension} label={dimension} value={score.toFixed(2)} />
          ))}
        </div>
        {report.regression ? (
          <pre className="payload">{JSON.stringify(report.regression, null, 2)}</pre>
        ) : (
          <p className="panel-muted">No regression baseline attached to this report.</p>
        )}
      </section>

      <section className="panel">
        <h3>Case Results</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Case</th>
              <th>Outcome</th>
              <th>Tool</th>
              <th>Approval</th>
              <th>Citations</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {report.results.map((result) => (
              <tr key={result.case_key}>
                <td>
                  <strong>{result.case_key}</strong>
                  <div className="panel-muted">{result.summary}</div>
                </td>
                <td>{result.passed ? "pass" : "fail"}</td>
                <td>{result.tool_name ?? "none"}</td>
                <td>{result.requires_approval ? "required" : "not required"}</td>
                <td>{result.citation_count}</td>
                <td>{result.latency_ms} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="meta-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
