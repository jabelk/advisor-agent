"""LLM analysis orchestrator using Anthropic Claude API."""

from __future__ import annotations

import logging
from typing import Any

from anthropic import Anthropic

from finance_agent.data.models import DocumentAnalysis
from finance_agent.research.prompts import SYSTEM_PROMPT, get_analysis_prompt

logger = logging.getLogger(__name__)

# Maximum content length before we use section-based analysis
MAX_SINGLE_PASS_CHARS = 80_000


class Analyzer:
    """Orchestrates LLM analysis of source documents."""

    def __init__(self, api_key: str) -> None:
        self.client = Anthropic(api_key=api_key)

    def analyze_document(
        self,
        content: str,
        content_type: str,
        company_ticker: str,
    ) -> DocumentAnalysis:
        """Analyze a document and return structured analysis.

        For large documents (>80K chars), uses section-based map-reduce.
        """
        prompt = get_analysis_prompt(content_type)

        if len(content) > MAX_SINGLE_PASS_CHARS:
            return self._analyze_large_document(content, content_type, company_ticker, prompt)

        return self._analyze_single_pass(content, content_type, company_ticker, prompt)

    def _analyze_single_pass(
        self,
        content: str,
        content_type: str,
        company_ticker: str,
        prompt: str,
    ) -> DocumentAnalysis:
        """Analyze a document in a single LLM call with structured output."""
        user_message = (
            f"Analyze this {content_type} document for {company_ticker}.\n\n"
            f"{prompt}\n\n"
            f"--- DOCUMENT START ---\n{content}\n--- DOCUMENT END ---"
        )

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            extra_headers={"anthropic-beta": "pdfs-2024-09-25"},
        )

        # Parse the response into structured output
        return self._parse_response(message, company_ticker)

    def _analyze_large_document(
        self,
        content: str,
        content_type: str,
        company_ticker: str,
        prompt: str,
    ) -> DocumentAnalysis:
        """Analyze a large document by splitting into sections and synthesizing."""
        sections = self._split_into_sections(content)
        logger.info(
            "Large document (%d chars) split into %d sections for %s",
            len(content), len(sections), company_ticker,
        )

        all_signals = []
        all_takeaways = []
        all_companies = set()

        for i, section in enumerate(sections):
            logger.debug("Analyzing section %d/%d for %s", i + 1, len(sections), company_ticker)
            try:
                analysis = self._analyze_single_pass(section, content_type, company_ticker, prompt)
                all_signals.extend(analysis.signals)
                all_takeaways.extend(analysis.key_takeaways)
                all_companies.update(analysis.companies_mentioned)
            except Exception as e:
                logger.warning("Section %d analysis failed for %s: %s", i + 1, company_ticker, e)

        # Determine overall sentiment
        sentiments = [s.summary.lower() for s in all_signals if s.signal_type.value == "sentiment"]
        bullish_count = sum(1 for s in sentiments if any(
            w in s for w in ["bullish", "positive", "strong", "grew", "beat"]
        ))
        bearish_count = sum(1 for s in sentiments if any(
            w in s for w in ["bearish", "negative", "weak", "decline", "miss"]
        ))
        if bullish_count > bearish_count:
            overall = "bullish"
        elif bearish_count > bullish_count:
            overall = "bearish"
        else:
            overall = "neutral"

        # Deduplicate takeaways (keep unique)
        unique_takeaways = list(dict.fromkeys(all_takeaways))[:5]

        return DocumentAnalysis(
            company_ticker=company_ticker,
            overall_sentiment=overall,
            signals=all_signals,
            key_takeaways=unique_takeaways,
            companies_mentioned=sorted(all_companies - {company_ticker}),
        )

    def _parse_response(self, message: Any, company_ticker: str) -> DocumentAnalysis:
        """Parse LLM response into a DocumentAnalysis object."""
        import json

        # Extract text content
        text = ""
        for block in message.content:
            if hasattr(block, "text"):
                text = block.text
                break

        # Try to find JSON in the response
        try:
            # Look for JSON block in the response
            if "```json" in text:
                json_start = text.index("```json") + 7
                json_end = text.index("```", json_start)
                json_str = text[json_start:json_end].strip()
            elif "{" in text:
                # Find the outermost JSON object
                brace_start = text.index("{")
                # Find matching closing brace
                depth = 0
                for i, c in enumerate(text[brace_start:], brace_start):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            json_str = text[brace_start : i + 1]
                            break
                else:
                    json_str = text[brace_start:]
            else:
                json_str = ""

            if json_str:
                data = json.loads(json_str)
                return DocumentAnalysis.model_validate(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        # Fallback: create a basic analysis from the text response
        from finance_agent.data.models import (
            Confidence,
            EvidenceType,
            ResearchSignalOutput,
            SignalType,
        )

        return DocumentAnalysis(
            company_ticker=company_ticker,
            overall_sentiment="neutral",
            signals=[
                ResearchSignalOutput(
                    signal_type=SignalType.SENTIMENT,
                    evidence_type=EvidenceType.INFERENCE,
                    confidence=Confidence.MEDIUM,
                    summary=text[:500] if text else "Analysis produced no structured output",
                )
            ],
            key_takeaways=[text[:200]] if text else ["No takeaways extracted"],
        )

    @staticmethod
    def _split_into_sections(content: str) -> list[str]:
        """Split content into sections based on markdown headers or length."""
        # Try to split on markdown headers
        lines = content.split("\n")
        sections: list[str] = []
        current: list[str] = []

        for line in lines:
            if line.startswith("# ") or line.startswith("## "):
                if current:
                    section_text = "\n".join(current)
                    if len(section_text.strip()) > 100:
                        sections.append(section_text)
                    current = []
            current.append(line)

        if current:
            section_text = "\n".join(current)
            if len(section_text.strip()) > 100:
                sections.append(section_text)

        # If no good section breaks, split by character count
        if len(sections) <= 1:
            chunk_size = MAX_SINGLE_PASS_CHARS
            sections = []
            for i in range(0, len(content), chunk_size):
                sections.append(content[i : i + chunk_size])

        return sections
