import Link from "next/link";
import { notFound } from "next/navigation";

import { EvalReport } from "../../components/EvalReport";
import { getEvalRun } from "../../lib/api";

type EvalDetailPageProps = {
  params: { evalRunId: string };
};

export default async function EvalDetailPage({ params }: EvalDetailPageProps) {
  const { evalRunId } = params;

  try {
    const report = await getEvalRun(evalRunId);

    return (
      <main className="grid">
        <div className="button-row">
          <Link className="link-button" href="/">
            Back to home
          </Link>
        </div>
        <EvalReport report={report} />
      </main>
    );
  } catch {
    notFound();
  }
}
