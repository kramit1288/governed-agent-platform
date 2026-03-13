"""Model creation tests for the db package."""

from __future__ import annotations

from db.enums import ApprovalStatus, EvalResultStatus, EvalRunStatus, RunStatus, ToolInvocationStatus
from db.models import ApprovalRequest, EvalCase, EvalResult, EvalRun, PromptVersion, Run, RunEvent, ToolInvocation


def test_model_creation_defaults(session) -> None:
    run = Run(workflow_key="support.ticket")
    tool_invocation = ToolInvocation(run=run, tool_name="lookup_ticket")
    approval_request = ApprovalRequest(run=run, tool_invocation=tool_invocation, reason="Needs approval")
    prompt_version = PromptVersion(name="answer", version="v1", template_text="Hello")
    eval_case = EvalCase(key="case-1", input_text="Question")
    eval_run = EvalRun(name="baseline")
    eval_result = EvalResult(eval_run=eval_run, eval_case=eval_case, status=EvalResultStatus.PASSED)
    run_event = RunEvent(run=run, sequence=1, event_type="run.created")

    session.add_all([
        run,
        tool_invocation,
        approval_request,
        prompt_version,
        eval_case,
        eval_run,
        eval_result,
        run_event,
    ])
    session.commit()

    assert run.status is RunStatus.PENDING
    assert tool_invocation.status is ToolInvocationStatus.PENDING
    assert approval_request.status is ApprovalStatus.PENDING
    assert eval_run.status is EvalRunStatus.PENDING
    assert eval_result.status is EvalResultStatus.PASSED
    assert run.created_at is not None
    assert prompt_version.prompt_metadata is None
