"""Minimal happy-path demo runner for the V1 API surface."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import error, request


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the V1 demo flow against the API.")
    parser.add_argument("--api-base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    api_base_url = args.api_base_url.rstrip("/")

    print("Creating grounded run...")
    grounded_run = post_json(
        f"{api_base_url}/runs",
        {
            "workflow_key": "support.ticket",
            "tenant_id": "tenant-1",
            "requested_by": "demo-script",
            "user_input": "Summarize ticket T-100 for me.",
        },
    )
    print(json.dumps(grounded_run, indent=2))

    print("\nCreating approval-gated run...")
    risky_run = post_json(
        f"{api_base_url}/runs",
        {
            "workflow_key": "support.ticket",
            "tenant_id": "tenant-1",
            "requested_by": "demo-script",
            "user_input": "Draft a refund request for customer C-100 on ticket T-100 for 42.50.",
        },
    )
    print(json.dumps(risky_run, indent=2))

    approval_id = risky_run.get("approval_request_id")
    if isinstance(approval_id, str):
        print("\nApproving pending action...")
        approval = post_json(f"{api_base_url}/approvals/{approval_id}/approve", {})
        print(json.dumps(approval, indent=2))

        resumed_run = get_json(f"{api_base_url}/runs/{risky_run['run_id']}")
        print("\nResumed run detail...")
        print(json.dumps(resumed_run, indent=2))

    print("\nRunning eval suite...")
    eval_report = post_json(
        f"{api_base_url}/evals/run",
        {"name": "demo-script-suite", "compare_to_latest": True},
    )
    print(json.dumps(eval_report, indent=2))


def get_json(url: str) -> dict[str, Any]:
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise SystemExit(f"Request to {url} failed: {exc.code} {body}") from exc


if __name__ == "__main__":
    main()
