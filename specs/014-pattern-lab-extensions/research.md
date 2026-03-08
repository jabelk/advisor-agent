# Research: Pattern Lab Extensions

**Feature**: 014-pattern-lab-extensions
**Date**: 2026-03-08

## R1: Statistical Test Selection for A/B Testing

**Decision**: Use Fisher's exact test for win rate comparison (binary outcome: each trade is a win or loss) and Welch's t-test for average return comparison (continuous outcome: each trade has a return percentage).

**Rationale**: Jordan's backtests typically produce 10-50 trades per variant. At these sample sizes, test selection matters significantly:

- **Fisher's exact test** computes the exact p-value for a 2x2 contingency table (variant A wins/losses vs variant B wins/losses) without relying on large-sample approximations. It is the gold standard for comparing proportions when sample sizes are small. Win/loss is a natural binary framing: a trade with return > 0% is a win, otherwise a loss.
- **Welch's t-test** compares means of two groups without assuming equal variances. Trade return distributions across pattern variants almost certainly have unequal variance (a 3% spike threshold catches more events with smaller returns; a 7% threshold catches fewer events with more volatile returns). Welch's t-test handles this correctly via separate variance estimates and Satterthwaite degrees of freedom.

At n=10-50, both tests have reasonable power to detect meaningful effect sizes. For example, Fisher's exact test can detect a win rate difference of 60% vs 30% with ~80% power at n=25 per group. Welch's t-test can detect a 1-standard-deviation difference in mean returns at n=20 per group.

**Alternatives considered**:
- **Chi-squared test (for win rate)**: Approximates the exact distribution using a continuous chi-squared curve. The approximation breaks down when expected cell counts fall below 5, which happens frequently at n=10-20 trades. Fisher's exact test has no such limitation. Rejected -- Fisher's is strictly better for small samples with no computational penalty.
- **Mann-Whitney U test (for returns)**: A non-parametric rank-based test that makes no distributional assumptions. Useful when data is heavily skewed or has outliers. However, it tests whether one distribution is stochastically greater than the other, not whether the means differ -- a subtle but important distinction for comparing average returns. Also harder to interpret for Jordan ("ranks" vs "average returns"). Rejected -- Welch's t-test is more interpretable and robust to moderate non-normality at n>10.
- **Bootstrap resampling**: Resample trades with replacement 10,000+ times, compute the metric difference each time, and derive a confidence interval. Conceptually elegant and makes no distributional assumptions. However: (a) at n=10-15 trades, bootstrap confidence intervals are unreliable because the resample space is too small; (b) adds implementation complexity with no accuracy gain over exact/parametric tests for our sample sizes; (c) results are non-deterministic, which complicates reproducibility. Rejected -- overkill for 2-sample comparisons at these sample sizes.
- **Permutation test**: Similar to bootstrap but enumerates or samples all possible re-assignments of trades to variants. Exact for small samples, but computationally expensive for n>20 and adds implementation complexity. Rejected -- Fisher's exact test already provides exact inference for the binary outcome; Welch's t-test is sufficient for the continuous outcome.

## R2: Multi-Ticker Aggregation Strategy

**Decision**: Pool all trades across tickers into a single combined dataset for aggregate metrics. Report per-ticker breakdowns alongside the aggregate. Run regime analysis on the combined (pooled) trade set. Tickers with no qualifying events appear in the per-ticker breakdown with zero counts and are excluded from aggregate calculations.

**Rationale**: Pooling treats the pattern as a sector-level strategy, which matches Jordan's mental model: "does the pharma dip pattern work across pharma stocks?" Each trade is an independent observation of the pattern regardless of which ticker generated it. If ABBV produces 8 trades and MRNA produces 12, pooling gives a combined dataset of 20 trades with more statistical power than either alone.

Per-ticker breakdowns surface whether the pattern works uniformly or is carried by one outlier ticker. If ABBV has a 70% win rate and the other three tickers are at 30%, the pooled aggregate (say 42%) is technically correct but misleading -- the per-ticker breakdown reveals this.

Regime analysis on the combined trade set detects sector-wide regime shifts. If the pharma dip pattern stopped working in Q3 2024, trades from all tickers in that period contribute to the "breakdown" regime label. This matches Jordan's observation that the pattern "worked for 3 months then stopped" across the sector, not just for one stock.

Tickers with no events during the backtest period are a normal outcome (not all pharma stocks have major news catalysts in every period). They appear as zero-count rows in the breakdown so Jordan knows they were tested, but they do not affect aggregate statistics.

**Alternatives considered**:
- **Average per-ticker metrics**: Calculate win rate and average return for each ticker independently, then average those per-ticker metrics. This weights each ticker equally regardless of trade count. A ticker with 2 trades gets the same influence as one with 20 trades, which is statistically unsound -- a 100% win rate on 2 trades is far less informative than 60% on 20 trades. Rejected -- pooling naturally weights by evidence.
- **Weighted average by trade count**: Compute per-ticker metrics, then weight by trade count when averaging. Mathematically equivalent to pooling for win rate and average return. Adds complexity for no benefit. Rejected -- pooling is simpler and produces identical results.
- **Per-ticker regime analysis**: Run regime detection on each ticker independently, then display separate regime timelines. With 3-10 trades per ticker, regime detection has almost no power. Pooling across tickers gives the regime algorithm more data to work with. Rejected -- insufficient data per ticker for meaningful regimes.

## R3: scipy vs Pure Python for Statistical Tests

**Decision**: Add scipy as a dependency. Use `scipy.stats.fisher_exact` for Fisher's exact test and `scipy.stats.ttest_ind` (with `equal_var=False` for Welch's variant) for the t-test.

**Rationale**: The existing codebase deliberately avoided scipy for option pricing (R5 in 012-covered-call-strategy) because only a single function (`norm_cdf`) was needed and `math.erf` provided an exact equivalent. The situation here is different:

- **Fisher's exact test** requires computing the hypergeometric distribution and summing tail probabilities. A correct implementation needs arbitrary-precision arithmetic for the factorials in the hypergeometric PMF (at n=50, factorials exceed float64 range). Python's `math.comb` handles this, but the full implementation is 30-50 lines of careful edge-case handling (one-tailed vs two-tailed, ties, zero cells). scipy's implementation is battle-tested and handles all edge cases.
- **Welch's t-test** requires the Satterthwaite degrees of freedom approximation and the regularized incomplete beta function for the t-distribution CDF (to compute p-values). The incomplete beta function is non-trivial to implement correctly -- it requires either a continued fraction expansion or numerical integration. This is fundamentally harder than `norm_cdf`.
- **Dependency cost**: scipy is already transitively installed in the environment (pandas, which is pulled in by alpaca-py, depends on numpy; scipy depends on numpy). Running `pip list` in the venv confirms scipy is available. Adding it as an explicit dependency formalizes what is already present rather than adding new weight.

If scipy were truly a new heavyweight addition, pure Python would be worth considering. Since it is already in the dependency tree, the tradeoff favors correctness and maintainability.

**Alternatives considered**:
- **Pure Python Fisher's exact test**: Feasible using `math.comb` for hypergeometric probabilities. Would need ~40 lines for the two-tailed version with proper handling of edge cases (zero cells, tied odds ratios). The risk is subtle bugs in tail probability summation -- Fisher's two-tailed test has multiple valid definitions (double the one-sided p-value, sum probabilities <= observed, likelihood ratio). Getting this wrong silently produces incorrect p-values. Rejected -- not worth the correctness risk for a statistical test that must be trustworthy.
- **Pure Python Welch's t-test**: The t-statistic is straightforward (`(mean1 - mean2) / sqrt(var1/n1 + var2/n2)`), but converting it to a p-value requires the t-distribution CDF, which requires the regularized incomplete beta function. Implementing this from scratch is 50-100 lines of numerical code (continued fraction expansion with convergence checks). Rejected -- this is library-grade numerical code, not application logic.
- **statsmodels**: Provides the same tests plus more (proportion z-tests, ANOVA). But statsmodels is a much heavier dependency than scipy and is not already in the dependency tree. Rejected -- scipy is sufficient.

## R4: Export Format Strategy

**Decision**: Markdown only. No PDF support in this feature. Default filename format: `pattern-{id}-{type}-{date}.md` where type is `backtest` or `ab-test`. Overwrite protection via numeric suffix append (e.g., `pattern-15-backtest-2026-03-08-1.md`).

**Rationale**: Markdown is the natural output format for a CLI tool:

- Renders well in terminals (it is plain text), GitHub, VS Code preview, and note-taking tools.
- Jordan can copy-paste sections into Slack, email, or documents.
- No additional dependencies required -- just string formatting.
- The spec explicitly states "Markdown is the only export format" with PDF deferred to future work.

The filename convention encodes enough context to be self-describing in a directory listing. The pattern ID identifies which pattern was tested, the type distinguishes backtests from A/B tests, and the date provides chronological ordering.

For overwrite protection, appending a numeric suffix is the simplest approach that avoids data loss. The sequence is: check if `pattern-15-backtest-2026-03-08.md` exists; if so, try `-1`, `-2`, etc. This matches common behavior in download managers and is immediately understandable.

**Alternatives considered**:
- **Markdown + PDF (via weasyprint or pandoc)**: PDF provides a polished, non-editable format suitable for formal sharing. However: (a) weasyprint adds a C library dependency (cairo/pango) that is painful to install cross-platform; (b) pandoc requires a system-level installation; (c) the spec defers PDF to "future work via external conversion tools." Jordan can always convert markdown to PDF externally (`pandoc report.md -o report.pdf`). Rejected -- out of scope, adds dependency burden.
- **HTML export**: More visually flexible than markdown (charts, tables with styling). But adds complexity (CSS, templating) without clear user need. Jordan hasn't asked for visual reports -- he wants a text record. Rejected -- YAGNI.
- **Overwrite with prompt**: Ask "File exists. Overwrite? (y/n)". Appropriate for interactive tools but the CLI may be used in scripts or piped workflows where prompts are problematic. Rejected -- silent suffix append is safer and scriptable.
- **Timestamped filenames (include HH-MM-SS)**: Guarantees uniqueness without suffix logic. But produces long, less-readable filenames like `pattern-15-backtest-2026-03-08-143022.md`. Rejected -- the numeric suffix is cleaner for the common case of 1-2 exports per day.

## R5: A/B Test Multiple Comparison Problem

**Decision**: For 3+ variants, run all pairwise comparisons without p-value correction. Display a warning that multiple comparisons inflate false positive rates. Report raw p-values with a note explaining the implication. Do not apply Bonferroni or any other correction.

**Rationale**: The multiple comparison problem is real: comparing 3 variants produces 3 pairwise tests, and comparing 5 variants produces 10. At alpha=0.05 per test, the probability of at least one false positive is 1-(0.95)^k, which is 14% for 3 comparisons and 40% for 10. However, applying corrections in this context does more harm than good:

- **Bonferroni is too conservative for small samples.** Bonferroni divides alpha by the number of comparisons. With 5 variants (10 comparisons), the corrected threshold is p < 0.005. At n=20 trades per variant, even a large real effect (e.g., 60% vs 30% win rate) may not reach p < 0.005. The correction would cause Jordan to miss genuinely significant differences.
- **Jordan is comparing 2-5 variants, not 50.** The multiple comparison problem is most dangerous in high-throughput screening (genomics, A/B testing at web scale) where thousands of comparisons make false positives nearly certain. With 3-10 pairwise comparisons, the inflation is modest and manageable with a warning.
- **A warning is more educational than an automatic correction.** Jordan is learning to use statistical tools. Showing raw p-values with an explanation ("With 3 comparisons, there's a ~14% chance one of these significant results is a false positive") teaches him to interpret results critically. An automatic correction hides the nuance.
- **The "best variant" recommendation uses the smallest p-value**, which naturally provides some protection -- the strongest signal is least likely to be a false positive.

The spec supports this approach: it defines 2-5 variants as the expected range and focuses on identifying whether the best variant is significantly better than the next best, which is a single comparison.

**Alternatives considered**:
- **Bonferroni correction**: Divide alpha by the number of comparisons (e.g., use p < 0.0167 for 3 comparisons instead of p < 0.05). Simple to implement but overly conservative for small samples. At n=15-20 trades per variant, real differences would be marked as non-significant. Rejected -- too conservative for the expected sample sizes and variant counts.
- **Holm-Bonferroni (step-down)**: A less conservative sequential correction that sorts p-values and applies progressively less stringent thresholds. Better than Bonferroni but still reduces power meaningfully. Adds implementation complexity for marginal benefit with 2-5 variants. Rejected -- complexity not justified.
- **False Discovery Rate (Benjamini-Hochberg)**: Controls the expected proportion of false positives among rejected hypotheses rather than the probability of any false positive. More powerful than Bonferroni for many comparisons. However, with only 3-10 comparisons, FDR and Bonferroni give similar results. Rejected -- designed for high-throughput settings, not 3-10 comparisons.
- **Always apply Bonferroni, with user override**: Correct by default, allow `--no-correction` flag. Reasonable but the "correct" default would confuse Jordan when real differences show as non-significant. The tool should empower the user, not gatekeep with conservative defaults. Rejected -- raw p-values with a warning is more transparent.
