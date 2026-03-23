import { notFound } from "next/navigation";

import { ApprovalCard } from "../../components/ApprovalCard";
import { getApproval } from "../../lib/api";

type ApprovalDetailPageProps = {
  params: { approvalId: string };
};

export default async function ApprovalDetailPage({ params }: ApprovalDetailPageProps) {
  const { approvalId } = params;

  try {
    const approval = await getApproval(approvalId);

    return (
      <main className="grid">
        <ApprovalCard actionable approval={approval} />
      </main>
    );
  } catch {
    notFound();
  }
}
