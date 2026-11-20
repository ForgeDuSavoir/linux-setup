# CLOSE-WAIT-001 — workspace-empty polling holds the common desktop lock

Status: reproduced in R0 on 2026-11-19, **not fixed**. Separate functional change,
not automatic Rust-port acceptance. Reference: frozen controller SHA-256 in
`oracles/manifest.json`; production Python remains unchanged.

## Reproduction without desktop mutation

```sh
python3 tools/runtime-migration/benchmark.py --samples 3
```

The synthetic world has a remaining window on workspace 1. Call
`closed(state, 1)` with fake native queries: the function polls for the **whole
workspace** to become empty, sleeps 40 × 50 ms and returns without doing useful
cleanup/navigation. Reproduce once with a virtual sleep recorder (40 polls,
2000 ms requested) and once using actual sleeping (~2007 ms on this run).

The production CLI invokes this handler while holding `workspace-columns.lock`.
The lock is also used by navigation, status, graphical session actions and
scratchpads. The benchmark independently measures contention on a **private**
lock, never intentionally blocks the real desktop lock. Wall time is scheduling
and IPC dependent; 2.0 s is requested sleeping, not a strict upper bound.

## Fix task (still open)

- [ ] Inspect native close-event timing/payload in source and fake Lua callbacks;
  identify whether a just-closed address can be passed without accessing an
  invalidated native object.
- [ ] Choose a bounded settlement rule for the **closing window**, not all
  windows. Remaining unrelated windows must not force a two-second wait.
- [ ] Avoid polling while monopolizing the shared lock where possible. After
  releasing/reacquiring it, revalidate current workspace, owner, existence,
  visible monitors and live clients before cleanup/focus; never act on stale
  events or transfer to a different owner.
- [ ] Preserve last-visible-empty retention, previous/same-owner fallback,
  external-switch behavior, scratchpad handling and no session stop by cleanup.
- [ ] Add deterministic fake-clock/process tests: another window remains,
  closing window disappears late, duplicate/old event, concurrent navigation,
  owner/state change and bounded timeout. Measure lock hold duration separately
  from total handler latency.
- [ ] Review/install the fix as its own change with private tests and the targeted
  installer only; no real close/switch as an implicit test. If fixed before R1,
  create a clearly identified new oracle baseline rather than rewriting the R0
  hashes/history silently. If fixed after the port, retain the defect reproduction
  as historical evidence, not a test demanding that production keep the delay.

No actual window/session was closed and no runtime binary/handler was replaced
while diagnosing this issue in R0.
