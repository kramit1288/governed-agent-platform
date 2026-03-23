"""Run offline evals against the current deterministic V1 behavior."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package in ("db", "evals", "tools", "retrieval"):
    src = ROOT / "packages" / package / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from db.session import create_db_engine, create_session_factory
from db.repositories import EvalRepository
from evals import OfflineEvalRunner, format_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline eval cases.")
    parser.add_argument("--name", default="smoke-suite", help="Logical eval run name.")
    parser.add_argument(
        "--compare-latest",
        action="store_true",
        help="Compare this run to the latest completed run with the same name.",
    )
    args = parser.parse_args()

    engine = create_db_engine()
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        runner = OfflineEvalRunner(repository=EvalRepository(session))
        report = runner.run(run_name=args.name, compare_to_latest=args.compare_latest)
        session.commit()
    print(format_report(report))


if __name__ == "__main__":
    main()
