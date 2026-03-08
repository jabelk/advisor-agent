# Feature Specification: Pattern Lab Extensions

**Feature Branch**: `014-pattern-lab-extensions`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Pattern Lab extensions: Multi-ticker aggregation — backtest a pattern across a basket of pharma stocks at once and see combined stats. A/B testing framework — compare pattern variants systematically (e.g., 3% vs 5% vs 7% spike thresholds) with statistical significance testing. Export/reporting — generate PDF or markdown reports of backtest results for review."

## User Scenarios & Testing

### User Story 1 — Multi-Ticker Aggregation (Priority: P1)

Jordan wants to backtest a pharma dip pattern across a basket of pharma stocks (ABBV, MRNA, PFE, BMY) simultaneously and see combined aggregate statistics rather than per-ticker results. This tells him whether the pattern works across the sector, not just one stock.

**Why this priority**: Currently backtests run per-ticker with separate reports. Jordan needs a portfolio-level view to validate that his pattern generalizes across the pharma sector before committing real capital. This is the foundation for both A/B testing and reporting.

**Independent Test**: Run `finance-agent pattern backtest 15 --tickers ABBV,MRNA,PFE,BMY --start 2024-01-01 --end 2025-12-31` and verify a single combined report shows aggregate statistics across all tickers plus a per-ticker breakdown.

**Acceptance Scenarios**:

1. **Given** a pattern and 4 tickers, **When** Jordan runs backtest, **Then** the output shows combined aggregate stats (total events, total trades, overall win rate, combined return) AND a per-ticker breakdown table.
2. **Given** a backtest across multiple tickers, **When** some tickers have no qualifying events, **Then** those tickers appear in the per-ticker breakdown with "0 events" and are excluded from aggregate win rate calculation.
3. **Given** a multi-ticker backtest result, **When** Jordan runs `pattern show`, **Then** the saved result includes which tickers were tested and their individual contributions.

---

### User Story 2 — A/B Testing Framework (Priority: P2)

Jordan wants to systematically compare pattern variants — for example, testing 3%, 5%, and 7% spike thresholds on the same data set — and know whether the differences are statistically meaningful or just random noise.

**Why this priority**: Jordan already has `pattern compare` for side-by-side metrics. A/B testing adds the critical "is this difference real?" layer with statistical significance testing, preventing him from optimizing on noise.

**Independent Test**: Run `finance-agent pattern ab-test 15 16 17 --tickers ABBV,MRNA --start 2024-01-01 --end 2025-12-31` and verify statistical comparison output with confidence levels.

**Acceptance Scenarios**:

1. **Given** 2+ pattern variants and a ticker set, **When** Jordan runs the A/B test, **Then** the system backtests each variant on identical data and reports per-variant metrics side-by-side with statistical comparison.
2. **Given** an A/B test comparing two variants, **When** one variant has a higher win rate than the other, **Then** the system reports whether the difference is statistically significant (at 95% confidence) or within the margin of noise.
3. **Given** variants with fewer than 10 trades each, **When** the A/B test runs, **Then** the system warns that sample size is insufficient for meaningful statistical comparison.
4. **Given** 3+ variants, **When** the A/B test completes, **Then** the system identifies the best-performing variant and states whether it is significantly better than the next best.

---

### User Story 3 — Export & Reporting (Priority: P3)

Jordan wants to export backtest results and A/B test comparisons as formatted markdown reports he can save, share, or review offline. This gives him a paper trail of what patterns he tested and what the results were.

**Why this priority**: The CLI output is ephemeral. Jordan needs persistent, shareable records of his analysis for his own reference and to discuss strategies with colleagues.

**Independent Test**: Run `finance-agent pattern export 15 --format markdown` and verify a well-formatted markdown file is generated with all backtest results, regime analysis, and trade log.

**Acceptance Scenarios**:

1. **Given** a pattern with backtest results, **When** Jordan exports as markdown, **Then** a `.md` file is generated containing the pattern description, backtest configuration, aggregate stats, regime analysis, trade log, and no-entry events.
2. **Given** an A/B test result, **When** Jordan exports it, **Then** the report includes the comparison table, statistical significance results, and a recommendation.
3. **Given** a pattern with no backtest results, **When** Jordan tries to export, **Then** the system shows an error: "No backtest results found for pattern #N. Run a backtest first."
4. **Given** an export command, **When** no output path is specified, **Then** the file is saved to the current directory with a descriptive filename (e.g., `pattern-15-backtest-2026-03-08.md`).

---

### Edge Cases

- What happens when all tickers in a multi-ticker backtest have zero events? The system reports "No qualifying events detected across any ticker" with suggestions to lower thresholds or widen the date range.
- What happens when A/B test variants have wildly different trade counts (e.g., 3% threshold finds 50 events, 7% threshold finds 3)? The system warns about unbalanced samples and notes that statistical comparisons may be unreliable.
- What happens when a user exports a pattern with multiple backtest runs? The export includes the most recent backtest by default, with a `--backtest-id` option to specify which run.
- What happens when the export file path already exists? The system appends a numeric suffix (e.g., `pattern-15-backtest-2026-03-08-1.md`) rather than overwriting.
- What happens when a multi-ticker backtest includes a ticker with no price data available? That ticker is listed as "no data" in the breakdown and excluded from aggregates.

## Requirements

### Functional Requirements

- **FR-001**: System MUST aggregate backtest results across multiple tickers into a single combined report showing total events detected, total trades entered, overall win rate, average return, total return, max drawdown, and Sharpe ratio across the full basket.
- **FR-002**: System MUST display a per-ticker breakdown table within the aggregated report showing each ticker's events, trades, win rate, and average return.
- **FR-003**: System MUST run regime analysis on the combined trade set when aggregating multi-ticker results, providing a sector-level regime view.
- **FR-004**: System MUST accept 2 or more pattern IDs for A/B testing and backtest each variant against identical ticker sets and date ranges.
- **FR-005**: System MUST calculate statistical significance of win rate differences between pattern variants using a hypothesis test, reporting p-values and confidence levels.
- **FR-006**: System MUST calculate statistical significance of average return differences between variants.
- **FR-007**: System MUST warn when sample sizes are insufficient for meaningful statistical comparison (fewer than 10 trades per variant).
- **FR-008**: System MUST identify the best-performing variant by win rate and average return, stating whether the advantage is statistically significant.
- **FR-009**: System MUST export backtest results to a markdown file containing pattern description, configuration, aggregate stats, regime analysis, trade log, and no-entry events.
- **FR-010**: System MUST export A/B test results to a markdown file containing the comparison table, statistical significance results, and a performance summary.
- **FR-011**: System MUST generate a descriptive default filename when no output path is specified (format: `pattern-{id}-{type}-{date}.md`).
- **FR-012**: System MUST avoid overwriting existing export files by appending a numeric suffix.
- **FR-013**: System MUST support `--format markdown` for export output (markdown is the only required format; this flag exists for future extensibility).

### Key Entities

- **AggregatedBacktestReport**: Combined results across multiple tickers for a single pattern — includes overall metrics, per-ticker breakdown, and combined regime analysis.
- **ABTestResult**: Comparison of 2+ pattern variants on identical data — includes per-variant metrics, statistical significance of differences (p-values, confidence intervals), and best variant identification.
- **ExportReport**: A formatted document generated from backtest or A/B test results — contains all relevant data in a human-readable format suitable for sharing.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Multi-ticker backtests complete within 2x the time of the slowest individual ticker backtest (aggregation overhead is minimal).
- **SC-002**: A/B test results include statistical significance indicators for 100% of pairwise variant comparisons when sample sizes are sufficient.
- **SC-003**: Exported markdown reports contain all data present in the CLI output with no information loss.
- **SC-004**: Jordan can complete a full workflow — describe variant patterns, backtest across a basket, compare with statistical significance, and export results — in a single terminal session.
- **SC-005**: Statistical significance warnings appear for 100% of comparisons where either variant has fewer than 10 trades.

## Assumptions

- Fisher's exact test for win rate comparison and Welch's t-test for average return comparison are appropriate statistical methods for small-sample financial comparisons (typical trade counts of 10-50).
- Trades are pooled across tickers for aggregate calculations (not averaged per-ticker), treating the pattern as a sector-level strategy.
- Markdown is the only export format. PDF can be added later via external conversion tools.
- 95% confidence (p < 0.05) is the default significance threshold, consistent with financial industry standards.
- Multi-ticker regime analysis runs on the combined trade set, providing a sector-level regime view rather than per-ticker regimes.
