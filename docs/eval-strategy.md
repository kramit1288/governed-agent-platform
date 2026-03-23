# Eval Strategy

V1 evals are curated, offline, and deterministic by design.

Goals:

- catch regressions during safe iteration
- make approval and tool behavior visible
- keep scores understandable in an interview

The runner executes versioned JSON eval cases against the current deterministic platform behavior and scores:

- groundedness / citation presence
- correct tool choice
- approval trigger correctness
- response usefulness
- format correctness
- latency signal
- cost estimate presence / threshold signal

The system intentionally does not depend on an external judge model in V1.

Reports are small and readable:

- case pass/fail
- average score
- per-dimension averages
- optional regression delta against the latest completed run with the same name
