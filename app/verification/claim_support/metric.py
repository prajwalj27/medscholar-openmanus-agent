"""
Claim Support Rate Metric

This metric calculates the percentage of factual claims in a literature survey
that are supported by inline citations (e.g., [1], [2], [3]).

Formula: (Claims with Citations / Total Claims) × 100

A high claim support rate indicates that the report properly attributes factual
statements to their sources, which is essential for scientific credibility.
"""

import re
from typing import Any, Dict, List, Tuple

from ..base import VerificationMetric, VerificationResult


class ClaimSupportMetric(VerificationMetric):
    """
    Metric to calculate the percentage of claims supported by inline citations.

    This metric:
    1. Extracts all factual claims from the report
    2. Identifies which claims have inline citation markers [1], [2], etc.
    3. Calculates the support rate as a percentage
    4. Provides detailed breakdown of supported vs unsupported claims

    Score Range: 0.0 to 1.0
    - 1.0: All claims have inline citations (100% support)
    - 0.5: Half of claims have citations (50% support)
    - 0.0: No claims have citations (0% support)
    """

    def __init__(self):
        super().__init__("claim_support_rate")

    async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
        """
        Calculate the claim support rate for a literature survey report.

        Args:
            report_path: Path to the markdown report file
            **kwargs: Additional parameters (unused)

        Returns:
            VerificationResult with score and detailed breakdown
        """
        # Read the report content
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()

        # Extract claims with their section information
        claims_with_sections = self._extract_claims_with_sections(report_content)

        # Analyze which claims have inline citations
        supported_claims, unsupported_claims = self._analyze_claim_support(claims_with_sections)

        # Calculate the support rate
        total_claims = len(claims_with_sections)
        supported_count = len(supported_claims)

        if total_claims == 0:
            score = 0.0
            summary = "No claims found in the report"
        else:
            score = supported_count / total_claims
            summary = f"{supported_count}/{total_claims} claims have inline citations ({score*100:.1f}%)"

        # Prepare detailed breakdown
        details = {
            "summary": summary,
            "total_claims": total_claims,
            "supported_claims": supported_count,
            "unsupported_claims": len(unsupported_claims),
            "support_rate_percentage": round(score * 100, 2),
            "supported_examples": supported_claims,  # All supported claims with sections
            "unsupported_examples": unsupported_claims,  # All unsupported claims with sections
            "analysis": {
                "claims_by_section": self._analyze_claims_by_section(claims_with_sections),
                "citation_pattern": self._analyze_citation_pattern([c['claim'] for c in claims_with_sections])
            }
        }

        return VerificationResult(
            metric_name=self.name,
            score=score,
            passed_checks=supported_count,
            total_checks=total_claims,
            details=details
        )

    def _extract_claims_with_sections(self, report_content: str) -> List[Dict[str, str]]:
        """
        Extract factual claims from the report along with their section information.

        Args:
            report_content: The markdown report content

        Returns:
            List of dicts with 'claim' and 'section' keys
        """
        # Remove the References section
        content_without_refs = re.split(
            r'^#{1,3}\s*References?\s*$',
            report_content,
            flags=re.MULTILINE | re.IGNORECASE
        )[0]

        lines = content_without_refs.split('\n')
        claims_with_sections = []
        current_section = "Introduction"

        for line in lines:
            line = line.strip()

            # Check if this is a heading (new section)
            heading_match = re.match(r'^#{1,6}\s+(.+)$', line)
            if heading_match:
                current_section = heading_match.group(1).strip()
                continue

            # Skip empty lines
            if not line:
                continue

            # Handle numbered lists like "1. **Title**: content"
            list_match = re.match(r'^\d+\.\s*\*\*[^*]+\*\*:\s*(.+)$', line)
            if list_match:
                content = list_match.group(1)
                sentences = self._split_into_sentences(content)
                for sent in sentences:
                    if self._is_valid_claim(sent):
                        claims_with_sections.append({
                            'claim': sent,
                            'section': current_section
                        })
                continue

            # Handle regular numbered lists "1. content"
            list_match = re.match(r'^\d+\.\s*(.+)$', line)
            if list_match:
                content = list_match.group(1)
                content = re.sub(r'\*\*([^*]+)\*\*:\s*', r'\1: ', content)
                sentences = self._split_into_sentences(content)
                for sent in sentences:
                    if self._is_valid_claim(sent):
                        claims_with_sections.append({
                            'claim': sent,
                            'section': current_section
                        })
                continue

            # Regular line - split into sentences
            sentences = self._split_into_sentences(line)
            for sent in sentences:
                if self._is_valid_claim(sent):
                    claims_with_sections.append({
                        'claim': sent,
                        'section': current_section
                    })

        return claims_with_sections

    def _extract_claims(self, report_content: str) -> List[str]:
        """
        Extract factual claims from the report.

        A claim is defined as a sentence that:
        - Contains factual medical/scientific information
        - Is not a heading, question, or metadata
        - Is in the main content (excludes References section)

        Args:
            report_content: The markdown report content

        Returns:
            List of claim sentences
        """
        # Remove the References section
        content_without_refs = re.split(
            r'^#{1,3}\s*References?\s*$',
            report_content,
            flags=re.MULTILINE | re.IGNORECASE
        )[0]

        # Remove markdown headings (h1-h6) but preserve the rest
        content_cleaned = re.sub(r'^#{1,6}\s+.*$', '', content_without_refs, flags=re.MULTILINE)

        # Remove code blocks
        content_cleaned = re.sub(r'```.*?```', '', content_cleaned, flags=re.DOTALL)

        # Split into lines and process
        lines = content_cleaned.split('\n')

        claims = []
        current_claim = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                if current_claim:
                    # End current claim
                    claim_text = ' '.join(current_claim)
                    if self._is_valid_claim(claim_text):
                        claims.append(claim_text)
                    current_claim = []
                continue

            # Skip metadata or list markers at the start, but keep the content
            # Handle numbered lists like "1. **Title**: content"
            list_match = re.match(r'^\d+\.\s*\*\*[^*]+\*\*:\s*(.+)$', line)
            if list_match:
                # This is a numbered list item with bold title
                # Split the content part into sentences
                content = list_match.group(1)
                sentences = self._split_into_sentences(content)
                for sent in sentences:
                    if self._is_valid_claim(sent):
                        claims.append(sent)
                current_claim = []
                continue

            # Handle regular numbered lists "1. content"
            list_match = re.match(r'^\d+\.\s*(.+)$', line)
            if list_match:
                content = list_match.group(1)
                # Remove bold formatting but keep text
                content = re.sub(r'\*\*([^*]+)\*\*:\s*', r'\1: ', content)
                sentences = self._split_into_sentences(content)
                for sent in sentences:
                    if self._is_valid_claim(sent):
                        claims.append(sent)
                current_claim = []
                continue

            # Regular line - split into sentences
            sentences = self._split_into_sentences(line)
            for sent in sentences:
                if self._is_valid_claim(sent):
                    claims.append(sent)

        # Don't forget the last claim if any
        if current_claim:
            claim_text = ' '.join(current_claim)
            if self._is_valid_claim(claim_text):
                claims.append(claim_text)

        return claims

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences, preserving inline citations.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on period, exclamation, or question mark followed by space and capital letter
        # But be careful not to split on periods inside citations or abbreviations

        # First, protect citations by temporarily replacing them
        citation_pattern = r'\[\d+\]'
        citations = re.findall(citation_pattern, text)
        protected_text = text
        for i, citation in enumerate(citations):
            protected_text = protected_text.replace(citation, f'CITATION{i}PLACEHOLDER', 1)

        # Now split on sentence boundaries
        # Pattern: period/exclamation/question followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected_text)

        # Restore citations
        result = []
        for sent in sentences:
            for i, citation in enumerate(citations):
                sent = sent.replace(f'CITATION{i}PLACEHOLDER', citation)
            result.append(sent.strip())

        return [s for s in result if s]

    def _is_valid_claim(self, text: str) -> bool:
        """
        Check if text is a valid claim worth analyzing.

        Args:
            text: Text to check

        Returns:
            True if valid claim, False otherwise
        """
        text = text.strip()

        # Skip empty or very short text
        if len(text) < 20:
            return False

        # Skip questions
        if text.endswith('?'):
            return False

        # Skip lines that are just bold titles without content
        if re.match(r'^\*\*[^*]+\*\*:?$', text):
            return False

        # IMPORTANT: If the sentence has an inline citation, it's definitely a claim
        # This ensures we don't miss claims just because they lack keywords
        citation_pattern = re.compile(r'\[\d+\]')
        if citation_pattern.search(text):
            return True

        # Keep sentences that look like factual claims
        # (contain medical/scientific terms or percentages/numbers)
        if re.search(r'\d+%|\d+\.\d+|study|studies|research|evidence|patients?|treatment|therapy|clinical|trial|data|analysis|findings|results', text, re.IGNORECASE):
            return True

        # Also keep sentences with modal verbs indicating claims
        if re.search(r'\b(is|are|was|were|has|have|shows?|indicates?|suggests?|demonstrates?|found|reported|revealed|observed)\b', text, re.IGNORECASE):
            return True

        return False

    def _analyze_claim_support(self, claims_with_sections: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Analyze which claims have inline citation support.

        Args:
            claims_with_sections: List of dicts with 'claim' and 'section' keys

        Returns:
            Tuple of (supported_claims, unsupported_claims) with details
        """
        supported = []
        unsupported = []

        # Pattern to match inline citations: [1], [2], [3], etc.
        citation_pattern = re.compile(r'\[\d+\]')

        for item in claims_with_sections:
            claim = item['claim']
            section = item['section']
            citations = citation_pattern.findall(claim)

            if citations:
                # Get unique citations (avoid duplicates like [1][1])
                unique_citations = list(dict.fromkeys(citations))  # Preserves order

                # Claim has inline citations
                supported.append({
                    "claim": claim,
                    "section": section,
                    "citations": unique_citations,
                    "citation_count": len(unique_citations)
                })
            else:
                # Claim lacks inline citations
                unsupported.append({
                    "claim": claim,
                    "section": section,
                    "reason": "No inline citation marker found"
                })

        return supported, unsupported

    def _analyze_claims_by_section(self, claims_with_sections: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze claims by section, showing total, supported, and unsupported counts.

        Args:
            claims_with_sections: List of dicts with 'claim' and 'section' keys

        Returns:
            Dictionary with section analysis
        """
        citation_pattern = re.compile(r'\[\d+\]')
        section_stats = {}

        for item in claims_with_sections:
            section = item['section']
            claim = item['claim']
            has_citation = bool(citation_pattern.search(claim))

            if section not in section_stats:
                section_stats[section] = {
                    'total': 0,
                    'supported': 0,
                    'unsupported': 0,
                    'support_rate': 0.0
                }

            section_stats[section]['total'] += 1
            if has_citation:
                section_stats[section]['supported'] += 1
            else:
                section_stats[section]['unsupported'] += 1

        # Calculate support rate for each section
        for section in section_stats:
            total = section_stats[section]['total']
            supported = section_stats[section]['supported']
            if total > 0:
                section_stats[section]['support_rate'] = round((supported / total) * 100, 2)

        return section_stats

    def _count_claims_by_section(self, report_content: str) -> Dict[str, int]:
        """
        Count claims by section to identify which parts need more citations.

        Args:
            report_content: The markdown report content

        Returns:
            Dictionary mapping section names to claim counts
        """
        sections = {}
        current_section = "Introduction"

        lines = report_content.split('\n')
        claim_count = 0

        for line in lines:
            # Check if this is a heading
            heading_match = re.match(r'^#{1,3}\s+(.+)$', line)
            if heading_match:
                # Save count for previous section
                if claim_count > 0:
                    sections[current_section] = claim_count

                # Start new section
                current_section = heading_match.group(1).strip()
                claim_count = 0

                # Stop at References
                if re.match(r'References?', current_section, re.IGNORECASE):
                    break
            else:
                # Count sentences in this line as potential claims
                sentences = re.split(r'[.!?]\s+', line)
                for sent in sentences:
                    if len(sent.strip()) > 20:  # Minimum claim length
                        claim_count += 1

        # Save final section
        if claim_count > 0:
            sections[current_section] = claim_count

        return sections

    def _analyze_citation_pattern(self, claims: List[str]) -> Dict[str, Any]:
        """
        Analyze patterns in citation usage.

        Args:
            claims: List of claim sentences

        Returns:
            Dictionary with citation pattern analysis
        """
        citation_pattern = re.compile(r'\[\d+\]')

        total_citations = 0
        unique_citations_set = set()
        claims_with_multiple_citations = 0
        max_citations_per_claim = 0

        for claim in claims:
            citations = citation_pattern.findall(claim)
            # Count unique citations in this claim
            unique_in_claim = set(citations)
            citation_count = len(unique_in_claim)

            total_citations += citation_count
            unique_citations_set.update(unique_in_claim)

            if citation_count > 1:
                claims_with_multiple_citations += 1

            max_citations_per_claim = max(max_citations_per_claim, citation_count)

        avg_citations_per_supported_claim = 0
        supported_claims_count = sum(1 for claim in claims if citation_pattern.search(claim))

        if supported_claims_count > 0:
            avg_citations_per_supported_claim = total_citations / supported_claims_count

        return {
            "total_unique_citations": len(unique_citations_set),
            "claims_with_multiple_citations": claims_with_multiple_citations,
            "max_citations_per_claim": max_citations_per_claim,
            "avg_citations_per_supported_claim": round(avg_citations_per_supported_claim, 2)
        }
        }
