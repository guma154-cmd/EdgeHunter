# SQLite Concurrency Validation

Date: 2026-05-21
Status: Validated
Owner: Rafael
Related ADR: [ADR-004](../architecture/adr_004_database_choice.md)

## Objective

Validate whether `SQLite + WAL mode + busy_timeout=5000ms` is technically sufficient for the expected EdgeHunter write workload before wider document cleanup or implementation proceeds.

This validation is intentionally centered on **write concurrency**, not database size. SQLite usually fails on lock contention before it fails on file size in this class of system.

## Scope

Writers analyzed:

1. Bet365 scraper
2. Betano scraper
3. Pinnacle scraper
4. OddsPortal scraper
5. APScheduler jobs writing operational state
6. Telegram bot callbacks writing user-confirmed bets

## Source Evidence

- `docs/architecture/adr_004_database_choice.md`
- `docs/prd/01_odds_historian.md`
- `docs/prd/05_auto_evolution.md`
- `src/edgehunter/database/schema.py`
- `src/edgehunter/database/sqlite_observability.py`
- `scripts/sqlite_contention_benchmark.py`
- `backend/app/data/scheduler.py`
- `backend/app/models/surebet.py`
- `backend/app/engine/autotuner.py`
- `_bmad-output/test-artifacts/sqlite-benchmark/sqlite_contention_results.json`

## Important Architectural Observation

The repository currently shows two different realities:

1. **Current code path**
   The current scheduler centralizes much of the work and commits writes in coarse batches. This means the database does **not** currently have six fully independent writer processes hammering it all the time.

2. **Target workload described by ADRs/PRDs**
   The intended production shape includes multiple scraper sources, scheduler-driven state updates, and Telegram callbacks. That future shape is the correct basis for architectural validation.

So the question is not "does SQLite survive the current thin workload?" It almost certainly does. The real question is "does SQLite remain acceptable once the intended writers all exist and occasionally overlap?"

## Empirical Validation Executed

To move beyond inference, a controlled benchmark was implemented and executed locally with:

- WAL enabled
- `busy_timeout=5000ms`
- six logical writer classes
- a measured observer for:
  - write lock wait time
  - full transaction duration
  - lock timeout count
  - per-writer throughput in the synthetic benchmark

Artifacts created:

- `src/edgehunter/database/sqlite_observability.py`
- `scripts/sqlite_contention_benchmark.py`
- `_bmad-output/test-artifacts/sqlite-benchmark/sqlite_contention_results.json`

### Scenario A — re-benchmark after transaction-discipline implementation

Synthetic stress shape:

- 12 compressed hot windows
- 4 scraper writers x 9 write transactions per round
- APScheduler writer x 4 write transactions per round
- Telegram callback writer x 1 write transaction per round

Measured result:

- `492 total write transactions`
- `0 locked errors`
- `551.41 writes/second` in the synthetic hot window
- `p95 wait = 41.56ms`
- `p95 transaction duration = 41.87ms`
- `max wait = 91.36ms`
- `max transaction duration = 91.57ms`

Interpretation:

- Under short transactions, six overlapping logical writers remained far below the 5-second timeout ceiling.
- The re-benchmark improved the prior p95 figures and still completed with zero lock errors.
- This directly supports SQLite viability for the intended MVP workload.

### Scenario B — control case for an intentionally long transaction

Synthetic failure shape:

- APScheduler-like writer deliberately held the write transaction open for `5500ms`
- the other 5 writers attempted writes concurrently

Measured result:

- `6 total write attempts`
- `0 locked errors` in this isolated rerun
- `p95 transaction duration = 4160.49ms`
- `max transaction duration = 5536.04ms`

Interpretation:

- This still demonstrates that a single long-lived transaction is operationally unacceptable even when a timeout does not fire in a small rerun.
- `busy_timeout=5000ms` remains adequate only if transaction lifetime stays comfortably below that threshold.

## ADR-004 Limits Already Defined

ADR-004 already contains concurrency limits and migration triggers:

- Acceptable limit: `5 concurrent write transactions per second`
- Migration trigger if sustained for >10 minutes:
  - `>5 write transactions per second`
  - `>2 simultaneous users performing writes`
  - `average write latency >50ms`
- Re-evaluate if `1M+ snapshots/month` or `10+ concurrent scrapers`

These are useful, but they are incomplete unless paired with transaction-duration discipline. SQLite with WAL still allows only **one writer at a time**.

## WAL + busy_timeout Technical Reality

What WAL mode gives:

- readers do not block writers
- one writer can proceed while readers continue
- write throughput improves compared to DELETE journal mode

What WAL mode does **not** give:

- it does not allow many writers to write truly in parallel
- it does not save the system from long-lived write transactions
- it does not prevent lock timeouts if one transaction holds the write lock for too long

What `busy_timeout=5000ms` means:

- a blocked writer will wait up to 5 seconds for the lock
- if the lock is still held after ~5 seconds, SQLite raises `database is locked`

So the decisive variable is not only writer count. It is:

`writer overlap x write frequency x transaction duration`

## Estimated Write Rate by Process

The ADR estimates `100k snapshots/month`.

That converts to:

- `~3,333 snapshots/day`
- `~139 snapshots/hour`
- `~2.31 snapshot writes/minute` across the whole system on average
- `~34.7 snapshot writes per 15-minute window`

Because four scraper sources are involved, a practical even-split estimate is:

- `~8.7 write operations per scraper per 15-minute cycle`
- `~0.58 writes/minute average per scraper`

This is the average. The risk is the **burst at the 15-minute boundary**, not the minute-average.

### Estimated Rate Table

| Writer | Basis | Estimated avg writes/min | Estimated burst behavior |
|---|---|---:|---|
| Bet365 scraper | 1/4 of 100k snapshots/month | ~0.58 | ~9 writes near each 15-min cycle |
| Betano scraper | 1/4 of 100k snapshots/month | ~0.58 | ~9 writes near each 15-min cycle |
| Pinnacle scraper | 1/4 of 100k snapshots/month | ~0.58 | ~9 writes near each 15-min cycle |
| OddsPortal scraper | 1/4 of 100k snapshots/month | ~0.58 | ~9 writes near each 15-min cycle |
| APScheduler jobs | health/state/result/autotune writes | ~0.01 to ~0.10 | usually 1-10 writes in a burst, depending on game settlement and future auto-evolution features |
| Telegram callbacks | manual `placed_bets`/manual overrides | ~0.001 to ~0.02 | low frequency, but can collide with cycle boundaries |

### Notes on the table

- The scraper figures are architecture-level estimates using ADR-004 volume, not production telemetry.
- `34.7 snapshot writes per 15-minute window` is derived from ADR-004 monthly volume and should be treated as a planning envelope, not a measured runtime fact.
- The current `odds_snapshots` schema aggregates multiple bookmaker columns in one row and does not yet represent every planned source symmetrically. That means the equal split across four scraper writers is a conservative simplification for concurrency planning, not a literal current-row model.
- APScheduler is currently mixed:
  - some jobs write nothing to SQLite
  - `_check_results_task()` can update multiple rows in one run
  - `autotuner` writes are negligible in frequency
  - future PRD-05 jobs increase state-write frequency modestly, but still not scraper-class throughput
- Telegram callback writes are low-frequency but safety-critical because they may happen during an ongoing odds cycle.

## Worst-Case Concurrency Analysis

### Worst-case scenario modeled

At a 15-minute boundary:

- Bet365 writes its cycle
- Betano writes its cycle
- Pinnacle writes its cycle
- OddsPortal writes its cycle
- APScheduler writes health/state/result rows
- Telegram callback writes a `placed_bet`

That is **6 logical writers** contending for the same SQLite file.

### Best-case lock behavior

If each writer does:

- short transaction
- local insert/update only
- no network call while transaction is open
- batch commit in well-bounded blocks

Then SQLite serializes the writers quickly.

Using a practical envelope:

- 35-40 row writes in the hot window
- row-level insert/update cost on local disk typically in the low milliseconds
- 6 short transactions serialized should usually finish well below `5000ms`

Observed benchmark confirmation:

- 492 synthetic write transactions completed with `0 locked errors`
- measured `p95 wait` was `41.56ms`
- measured `p95 transaction duration` was `41.87ms`
- measured `max transaction duration` was `91.57ms`

Under that discipline, `WAL + busy_timeout=5000ms` is acceptable.

### Actual risk condition

If any writer:

- opens a write transaction early
- performs network I/O before commit
- loops over many rows before commit
- mixes business logic, confirmation calls, or Telegram sends inside the same write transaction

then the write lock can be held long enough for queued writers to exceed `busy_timeout`.

### Implemented transaction-discipline control

That warning pattern existed in the previous implementation of `_fetch_odds_task()` in `backend/app/data/scheduler.py`, where Telegram I/O happened before commit.

It has now been corrected by splitting the persistence path from Telegram delivery, guarding the write-only helpers with `@SHORT_TX(max_duration_ms=100)`, documenting the rule in `docs/architecture/transaction-discipline.md`, and enforcing the static check with `python scripts/check_transaction_discipline.py`.

So the limiting factor is **transaction design**, not raw write volume.

## Veredict

**SQLite: APROVADO**

### Why not "REPROVADO"

- The estimated write rate is still low for a single-machine SQLite deployment.
- The ADR-004 limits are directionally reasonable.
- The 6 writers are not all high-frequency writers.
- With WAL and short transactions, this workload is still within SQLite territory.

### Why "APROVADO" is justified now

- WAL still does not make 6 concurrent writers safe by itself, but the implemented transaction discipline directly addresses the lock-amplifying pattern previously found.
- `busy_timeout=5000ms` is now paired with explicit short-transaction controls instead of relying on convention alone.
- The re-benchmark completed with `0 locked errors`, `p95 wait = 41.56ms`, and `p95 transaction duration = 41.87ms`, which is comfortably below the migration-warning thresholds.
- The control set is no longer hypothetical: it exists in code, documentation, tests, and the transaction-discipline checker.

## Active Controls

SQLite remains acceptable with the following controls in place:

1. **No network I/O inside open write transactions**
   Telegram sends, scraper confirmations, and external API calls must happen before the transaction begins or after commit.

2. **Short, bounded write transactions**
   Keep write transactions to local row persistence only.

3. **One commit per bounded batch**
   Prefer compact batch writes over many tiny commits, but do not hold the transaction open while doing unrelated work.

4. **Retry and telemetry around lock contention**
   Record:
   - `sqlite_lock_time_ms`
   - `write_tx_duration_ms`
   - `database is locked` count
   - writes per second in hot windows
   Minimum implementation already exists in `src/edgehunter/database/sqlite_observability.py` and remains available for deeper runtime instrumentation.

5. **Do not add new independent writers casually**
   New writer classes should be justified architecturally, especially around APScheduler and Telegram callback paths.

6. **Consider a write-serialization pattern if PRD-05 is implemented fully**
   A single internal write queue or repository-layer serializer is safer than letting many components open independent SQLite write transactions.

## Recommended Future Migration Criteria

SQLite should be reconsidered and PostgreSQL should become the default path if any of these conditions occur in production or staging validation:

1. `database is locked` errors occur at all in normal operation after transaction cleanup
2. write lock wait `p95 > 250ms` during normal 15-minute cycles
3. write transaction duration `p95 > 500ms`
4. more than `3 overlapping writer classes` become normal, not exceptional
5. sustained `>5 write transactions/second` for `>10 minutes`
6. Telegram/manual callbacks and odds collection routinely collide and create user-visible delays
7. PRD-05 introduces frequent state mutation that cannot be cleanly serialized

These thresholds are intentionally much looser than the measured benchmark baseline (`p95 tx ~= 41.87ms`, `max tx ~= 91.57ms`) so they can function as operational warning lines, not merely benchmark vanity targets.

## PostgreSQL vs Architectural Adjustment

If SQLite later fails these conditions, the next move should be:

### First choice

**Architectural adjustment before full migration**

Preferred immediate mitigation:

- centralize DB writes behind one write service / queue / repository serializer
- shorten transactions
- separate compute/network work from persistence

Reason:

- if the problem is poor transaction design, PostgreSQL hides the symptom but does not fix the architecture

### Second choice

**PostgreSQL migration**

Use PostgreSQL if:

- the write workload is truly becoming multi-writer by design
- manual interaction + schedulers + scrapers all need independent writes routinely
- operational telemetry proves SQLite lock contention despite disciplined transaction cleanup

## Decision Summary

- All 6 writer classes were analyzed
- Worst-case with `busy_timeout=5000ms` was considered
- Controlled benchmark evidence was collected and re-benchmarked after the scheduler refactor
- The transaction-discipline refactor removed the known lock-amplifying anti-pattern and is now an implemented control
- SQLite is **approved**
- SQLite remains dependent on preserving transaction discipline as the operational control
- The next blocker is not file size; it is transaction lifetime and writer overlap

## Required Human Sign-Off

Rafael must review this verdict before continuing with the next document-cleanup or implementation prompt.

If Rafael judges the constraints above unrealistic for the intended PRD-05 evolution, the correct action is to stop and escalate the persistence decision before proceeding.
