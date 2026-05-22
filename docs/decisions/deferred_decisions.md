# Deferred Decisions

Date: 2026-05-21
Scope: EdgeHunter PRDs 00-05

This document records decisions that were intentionally deferred because they are optimizations, optional features, or validation follow-ups that do not change the initial implementation contract.

## PRD-00

### Support tennis in Phase 4
- Decision: defer
- Default: no tennis in v1
- Revisit when: the core value-betting pipeline is stable for at least 3 months and the PRD is explicitly expanded

### Historical OddsPortal backtest
- Decision: defer
- Default: do not block implementation on this analysis; use it only if data is readily available during future validation
- Revisit when: there is a dedicated backtest/validation pass for OddsPortal historical coverage

### Multi-bankroll by league
- Decision: defer
- Default: single bankroll in v1
- Revisit when: the bankroll model needs to be split by league for operational reasons

## PRD-01

### Cross-validation threshold between Pinnacle and OddsPortal
- Decision: defer
- Default: keep the 10% threshold for v1
- Revisit when: staging/backtest evidence shows a materially better threshold

## PRD-02

### Temporal decay in training
- Decision: defer
- Default: no temporal decay in v1; all historical matches have uniform weight
- Revisit when: backtests show recency weighting materially improves accuracy

## PRD-03

### Initial EV threshold
- Decision: defer
- Default: 2% threshold
- Revisit when: production telemetry or backtests justify a different default

### Overround in EV calculation
- Decision: defer
- Default: v1 does not adjust EV by overround
- Revisit when: the market model requires a more conservative formula

### Deduplication window
- Decision: defer
- Default: 1 hour deduplication window
- Revisit when: observed alert duplication or missed-opportunity rate suggests a different window

## PRD-04

### Use Gemini Pro for critical validations
- Decision: defer
- Default: Gemini Flash for all v1 validations
- Revisit when: Flash proves insufficient for a specific high-risk validation path

### Claude API fallback
- Decision: defer
- Default: no external fallback in v1; use graceful degradation only
- Revisit when: a second external provider is required for operational resilience

### Validation cache duration
- Decision: defer
- Default: 1 hour cache
- Revisit when: measured duplicate-validation patterns justify a longer cache

### Auto-apply `risk='medium'`
- Decision: defer
- Default: `risk='medium'` remains suggestion-only in v1 and still requires manual approval
- Revisit when: the operational trust model explicitly allows broader autonomous action

## PRD-05

### Multi-bankroll by league
- Decision: defer
- Default: single bankroll in v1
- Revisit when: bankroll management needs to diverge by competition

### Backup bankroll_state to file
- Decision: defer
- Default: rely on the SQLite backup/restore process; no separate bankroll_state file backup in v1
- Revisit when: file-level recovery for bankroll state becomes a distinct requirement

### Telegram /backtest command
- Decision: defer
- Default: no `/backtest` command in v1
- Revisit when: on-demand historical analysis becomes an operational need

### Auto-resume after pause
- Decision: defer
- Default: manual `/resume`
- Revisit when: the pause semantics are redefined for safe automatic recovery

### Push notifications beyond Telegram
- Decision: defer
- Default: Telegram only
- Revisit when: a second delivery channel is explicitly required
