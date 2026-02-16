"""Section-specific analysis prompts for LLM research analysis."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an expert financial analyst specializing in company research \
for investment decisions.

CRITICAL RULES:
1. For every finding, you MUST classify it as either "fact" \
(directly stated in the source document) or "inference" \
(your analytical conclusion drawn from the facts).
2. Be precise: cite specific numbers, percentages, and dates.
3. Focus on investment-relevant signals: what matters for someone \
deciding whether to buy, hold, or sell.
4. Generate multiple signals per document — cover all material findings.
5. For financial metrics, include prior period values when available.
"""

FILING_10K_PROMPT = """\
Analyze this 10-K annual report filing. Focus on:
1. **Risk Factors** (Item 1A): Classify each major risk. Identify NEW risks vs. unchanged. \
Flag any risk that has materially changed from typical boilerplate.
2. **MD&A** (Item 7): Extract revenue trends, margin changes, guidance, segment performance. \
Note tone: optimistic, cautious, or defensive.
3. **Financial Statements**: Key metrics — revenue, net income, EPS, free cash flow, debt levels. \
Compare YoY and note significant changes (>10%).
4. **Business Overview** (Item 1): Competitive position, market size claims, growth strategy.

Generate signals for each material finding. Use "fact" for numbers/statements from the filing, \
"inference" for your analytical conclusions about what they mean for the company's outlook.
"""

FILING_10Q_PROMPT = """\
Analyze this 10-Q quarterly report. Focus on:
1. **Quarterly financials**: Revenue, earnings, margins vs. prior quarter and year-ago quarter.
2. **MD&A updates**: Any changes in outlook, new challenges, or segment shifts.
3. **Risk factor changes**: New risks added or existing risks removed/modified since last filing.
4. **Guidance updates**: Forward-looking statements about next quarter or full year.

Prioritize what has CHANGED from the last quarter. Generate signals with "fact" for extracted data \
and "inference" for your analysis of trends and implications.
"""

FILING_8K_PROMPT = """\
Analyze this 8-K current event filing. 8-Ks report material events. Focus on:
1. **Type of event**: Leadership change, M&A, earnings, restatement, material agreement, or other.
2. **Impact assessment**: How material is this event? What does it signal?
3. **Leadership changes**: If executive appointments/departures are reported, extract: \
name, role (CEO/CTO/CFO/etc.), whether it's an appointment or departure, effective date.
4. **Financial impact**: Any immediate financial implications mentioned?

For leadership changes, generate a "leadership_change" signal type. \
For other material events, use the most appropriate signal type.
"""

EARNINGS_TRANSCRIPT_PROMPT = """\
Analyze this earnings call transcript. Separate management discussion from Q&A:

**Management Discussion**:
1. Key messages management wants investors to hear
2. Revenue/earnings figures and guidance (forward-looking estimates)
3. Tone assessment: confident, cautious, evasive, or defensive
4. Strategic priorities and capital allocation plans

**Q&A Session**:
1. What questions did analysts ask? What are they concerned about?
2. How did management respond — direct or evasive?
3. Any new information revealed under questioning that wasn't in prepared remarks?

Generate signals covering: sentiment, guidance changes, financial metrics, risk factors, \
and competitive insights. Mark management statements as "fact" and your tone/intent analysis \
as "inference".
"""

PODCAST_DEEP_DIVE_PROMPT = """\
Analyze this podcast deep-dive episode about a company. Extract investment-relevant insights:

1. **Competitive Advantages**: What moats, network effects, or structural advantages are identified?
2. **Growth Catalysts**: What growth opportunities or tailwinds are discussed?
3. **Risk Factors**: What risks, challenges, or headwinds are mentioned?
4. **Investment Thesis**: What would be the bull case and bear case based on this analysis?
5. **Referenced Sources**: Any data sources, reports, or experts \
mentioned worth following up on.
6. **Company mentions**: Identify all companies discussed and their \
relationship to the main subject.

Mark host opinions and analysis as "inference" and cited facts/data as "fact".
"""

PODCAST_INTERVIEW_PROMPT = """\
Analyze this podcast interview episode. Extract investment-relevant insights:

1. **Leadership Insights**: What does the interviewee reveal about strategy, vision, or priorities?
2. **Industry Perspectives**: Market trends, competitive dynamics, regulatory outlook.
3. **Company Mentions**: Which companies are discussed? In what context?
4. **Quotable Statements**: Key quotes that reveal strategic thinking or market outlook.

Focus on what's actionable for investment decisions. Mark direct quotes as "fact" and your \
interpretation of their significance as "inference".
"""

ANALYST_RATINGS_PROMPT = """\
Analyze this analyst ratings/recommendation trends data. Focus on:
1. **Consensus Direction**: Is the consensus bullish, bearish, or mixed? How strong is agreement?
2. **Trend Over Time**: Are ratings improving or deteriorating over recent months?
3. **Outliers**: Any notable strong-buy or strong-sell positions that stand out?
4. **Implications**: What does the analyst consensus suggest for near-term price action?

Generate signals for consensus direction and any significant rating changes. \
Mark analyst ratings as "fact" and your assessment of implications as "inference".
"""

EARNINGS_HISTORY_PROMPT = """\
Analyze this earnings beat/miss history. Focus on:
1. **Beat/Miss Pattern**: How consistently does this company beat or miss estimates?
2. **Surprise Magnitude**: Are the surprises getting larger or smaller over time?
3. **EPS Trend**: Is the actual EPS trending up, down, or flat?
4. **Estimate Accuracy**: How well do analysts estimate this company's earnings?

Generate signals for earnings trend direction and predictability. \
Mark historical data as "fact" and your trend analysis as "inference".
"""

INSIDER_ACTIVITY_PROMPT = """\
Analyze this insider transaction data. Focus on:
1. **Net Direction**: Are insiders net buying or selling? What's the total value?
2. **Who's Trading**: Are C-suite executives buying/selling, or lower-level insiders?
3. **Cluster Detection**: Are multiple insiders trading in the same direction around the same time?
4. **Signal Strength**: Insider buying is a stronger signal than selling \
(selling can be for personal reasons). Are there notable buys?

Generate signals for insider sentiment. Mark transaction data as "fact" \
and your interpretation of insider intent as "inference".
"""

INSIDER_SENTIMENT_PROMPT = """\
Analyze this monthly insider sentiment (MSPR) data. Focus on:
1. **MSPR Trend**: Is the Monthly Share Purchase Ratio trending positive or negative?
2. **Recent vs. Historical**: How does recent sentiment compare to the longer-term average?
3. **Inflection Points**: Are there any months where sentiment reversed sharply?
4. **Conviction Level**: How strong is insider conviction based on MSPR magnitude?

Generate signals for insider sentiment trends. Mark MSPR values as "fact" \
and your assessment of conviction and trend implications as "inference".
"""

COMPANY_NEWS_PROMPT = """\
Analyze these recent news headlines and summaries. Focus on:
1. **Sentiment Mix**: What's the overall news tone — positive, negative, or mixed?
2. **Material Events**: Are there any potentially market-moving headlines (M&A, lawsuits, \
product launches, regulatory actions)?
3. **Narrative Themes**: What recurring themes or topics appear across multiple headlines?
4. **Source Quality**: Are the reports from major financial outlets or smaller sources?

Generate signals for news sentiment and any material events identified. \
Mark reported facts as "fact" and your narrative analysis as "inference".
"""

STRATECHERY_ARTICLE_PROMPT = """\
Analyze this Stratechery analysis article. Ben Thompson provides strategic tech analysis. Extract:

1. **Company Direction**: What strategic moves are analyzed? What's the author's assessment?
2. **Competitive Positioning**: How does the company stack up against competitors?
3. **Market Structure**: Are there market shifts, platform dynamics, or industry changes discussed?
4. **Technology Trends**: AI adoption, platform shifts, business model evolution.
5. **Multiple Companies**: If the article covers multiple companies, \
generate separate signals for each.

Mark Thompson's stated opinions and analysis as "inference" \
(even though they're from a respected analyst, they're still \
analytical conclusions). Mark cited facts, financials, and \
company statements as "fact".
"""

# Map content types to their analysis prompts
CONTENT_TYPE_PROMPTS: dict[str, str] = {
    "10-K": FILING_10K_PROMPT,
    "10-Q": FILING_10Q_PROMPT,
    "8-K": FILING_8K_PROMPT,
    "earnings_call": EARNINGS_TRANSCRIPT_PROMPT,
    "analyst_ratings": ANALYST_RATINGS_PROMPT,
    "earnings_history": EARNINGS_HISTORY_PROMPT,
    "insider_activity": INSIDER_ACTIVITY_PROMPT,
    "insider_sentiment": INSIDER_SENTIMENT_PROMPT,
    "company_news": COMPANY_NEWS_PROMPT,
    "podcast_deep_dive": PODCAST_DEEP_DIVE_PROMPT,
    "podcast_interview": PODCAST_INTERVIEW_PROMPT,
    "analysis_article": STRATECHERY_ARTICLE_PROMPT,
    "daily_update": STRATECHERY_ARTICLE_PROMPT,
}


def get_analysis_prompt(content_type: str) -> str:
    """Get the analysis prompt for a given content type."""
    return CONTENT_TYPE_PROMPTS.get(content_type, FILING_10K_PROMPT)
