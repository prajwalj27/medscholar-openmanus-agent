"""
Evidence Match Quality Metric

This metric evaluates whether cited sources actually support the claims made in the report.
It uses TF-IDF similarity and keyword matching to determine if the content from citation URLs
aligns with the claims that reference them.

Approach:
1. Fetch content from citation URLs
2. Extract clean text from HTML
3. Calculate TF-IDF similarity between claim and source
4. Perform keyword matching and proximity analysis
5. Find best matching passages
6. Generate composite match score

Score Range: 0.0 to 1.0
- 0.9-1.0: Strong evidence match
- 0.7-0.89: Good match
- 0.4-0.69: Partial match
- 0.0-0.39: Poor/no match
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..base import VerificationMetric, VerificationResult
from ..report_parser import ReportParser


class EvidenceMatchMetric(VerificationMetric):
    """
    Metric to evaluate whether cited sources support the claims made.

    This metric:
    1. Extracts claims with their inline citations
    2. Maps citations to URLs from References section
    3. Fetches and extracts text from source URLs
    4. Calculates similarity between claims and source content
    5. Provides detailed match analysis per claim

    Score represents the average match quality across all verifiable claims.
    """

    def __init__(self):
        super().__init__("evidence_match_quality")
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
        """
        Calculate evidence match quality for cited claims in the report.

        Args:
            report_path: Path to the markdown report file
            **kwargs: Additional parameters (unused)

        Returns:
            VerificationResult with match scores and detailed analysis
        """
        # Read report content
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Parse report to get citations and references
        parser = ReportParser(report_path)
        parser.parse()

        # Extract claims with citations
        claims_with_citations = self._extract_claims_with_citations(report_content)

        # Build citation URL map from References section
        citation_url_map = self._build_citation_url_map(report_content)

        # Verify each claim against its cited sources
        verification_results = await self._verify_claims(
            claims_with_citations, citation_url_map
        )

        # Calculate overall score
        total_claims = len(verification_results)
        if total_claims == 0:
            score = 0.0
            summary = "No verifiable claims found"
        else:
            # Average composite score across all claims
            scores = [
                r["composite_score"]
                for r in verification_results
                if r["composite_score"] is not None
            ]
            if scores:
                score = sum(scores) / len(scores)
                high_match = sum(1 for s in scores if s >= 0.7)
                summary = f"{high_match}/{len(scores)} claims have high evidence match ({score*100:.1f}% avg)"
            else:
                score = 0.0
                summary = "Unable to verify claims (sources inaccessible)"

        # Prepare detailed breakdown
        details = {
            "summary": summary,
            "total_claims_analyzed": total_claims,
            "verifiable_claims": len(
                [r for r in verification_results if r["composite_score"] is not None]
            ),
            "unverifiable_claims": len(
                [r for r in verification_results if r["composite_score"] is None]
            ),
            "average_match_score": round(score * 100, 2),
            "match_distribution": self._calculate_match_distribution(
                verification_results
            ),
            "claim_verification_details": verification_results,
        }

        return VerificationResult(
            metric_name=self.name,
            score=score,
            passed_checks=len(
                [
                    r
                    for r in verification_results
                    if r.get("composite_score") is not None
                    and r["composite_score"] >= 0.7
                ]
            ),
            total_checks=total_claims,
            details=details,
        )

    def _extract_claims_with_citations(
        self, report_content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract claims that have inline citations.

        Args:
            report_content: Markdown report content

        Returns:
            List of dicts with claim text and citation markers
        """
        # Remove References section
        content_without_refs = re.split(
            r"^#{1,3}\s*References?\s*$",
            report_content,
            flags=re.MULTILINE | re.IGNORECASE,
        )[0]

        # Find all sentences with citations
        citation_pattern = re.compile(r"([^.!?]+[\[\d\]]+[^.!?]*[.!?])")
        sentences_with_citations = citation_pattern.findall(content_without_refs)

        claims = []
        for sentence in sentences_with_citations:
            # Extract citation numbers from this sentence
            citations = re.findall(r"\[(\d+)\]", sentence)
            if citations:
                # Clean up the sentence
                clean_sentence = sentence.strip()
                claims.append(
                    {
                        "claim": clean_sentence,
                        "citations": list(set(citations)),  # Unique citations
                    }
                )

        return claims

    def _build_citation_url_map(self, report_content: str) -> Dict[str, str]:
        """
        Build a mapping from citation numbers to URLs from References section.

        Args:
            report_content: Markdown report content

        Returns:
            Dict mapping citation number (as string) to URL
        """
        # Extract References section
        refs_match = re.search(
            r"^#{1,3}\s*References?\s*$(.+)",
            report_content,
            flags=re.MULTILINE | re.IGNORECASE | re.DOTALL,
        )

        if not refs_match:
            return {}

        references_section = refs_match.group(1)

        # Extract citation number and URL pairs
        # Pattern: [1] ... URL: http://... or Available at: [URL](http://...)
        citation_url_map = {}

        # Pattern 1: [1] ... http://...
        pattern1 = re.compile(r"\[(\d+)\][^\n]+?(https?://[^\s\)]+)")
        for match in pattern1.finditer(references_section):
            citation_num = match.group(1)
            url = match.group(2).rstrip(".,;)")
            citation_url_map[citation_num] = url

        return citation_url_map

    async def _verify_claims(
        self,
        claims_with_citations: List[Dict[str, Any]],
        citation_url_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Verify each claim against its cited sources.

        Args:
            claims_with_citations: List of claims with citation numbers
            citation_url_map: Mapping from citation numbers to URLs

        Returns:
            List of verification results for each claim
        """
        results = []

        for claim_info in claims_with_citations:
            claim = claim_info["claim"]
            citations = claim_info["citations"]

            # Get URLs for these citations
            urls = []
            for cit in citations:
                if cit in citation_url_map:
                    urls.append(citation_url_map[cit])

            if not urls:
                # No URLs found for citations
                results.append(
                    {
                        "claim": claim,
                        "citations": citations,
                        "urls": [],
                        "composite_score": None,
                        "match_quality": "UNVERIFIABLE",
                        "reason": "No URLs found for citations",
                    }
                )
                continue

            # Verify against each URL (take best match)
            best_match = None
            best_score = 0.0

            for url in urls:
                match_result = await self._verify_claim_against_url(claim, url)
                if match_result and match_result.get("composite_score", 0) > best_score:
                    best_score = match_result["composite_score"]
                    best_match = match_result

            if best_match:
                results.append(
                    {"claim": claim, "citations": citations, "urls": urls, **best_match}
                )
            else:
                results.append(
                    {
                        "claim": claim,
                        "citations": citations,
                        "urls": urls,
                        "composite_score": None,
                        "match_quality": "UNVERIFIABLE",
                        "reason": "Unable to fetch or process source content",
                    }
                )

        return results

    async def _verify_claim_against_url(
        self, claim: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a single claim against a source URL.

        Args:
            claim: Claim text
            url: Source URL

        Returns:
            Dict with verification results, or None if verification failed
        """
        try:
            # Fetch content
            source_text = await self._fetch_and_extract_text(url)
            if not source_text or len(source_text) < 100:
                return None

            # Calculate TF-IDF similarity
            tfidf_score = self._calculate_tfidf_similarity(claim, source_text)

            # Calculate keyword match
            keyword_match = self._calculate_keyword_match(claim, source_text)

            # Find best matching passage
            best_passage = self._find_best_matching_passage(claim, source_text)

            # Calculate composite score
            composite_score = (
                tfidf_score * 0.5
                + keyword_match["match_rate"] * 0.3
                + best_passage["score"] * 0.2
            )

            # Classify match quality
            if composite_score >= 0.7:
                match_quality = "HIGH"
            elif composite_score >= 0.4:
                match_quality = "MEDIUM"
            else:
                match_quality = "LOW"

            return {
                "composite_score": composite_score,
                "match_quality": match_quality,
                "tfidf_similarity": round(tfidf_score, 3),
                "keyword_match_rate": round(keyword_match["match_rate"], 3),
                "best_passage": (
                    best_passage["passage"][:200] + "..."
                    if len(best_passage["passage"]) > 200
                    else best_passage["passage"]
                ),
                "passage_similarity": round(best_passage["score"], 3),
                "found_keywords": keyword_match["found_keywords"],
                "missing_keywords": keyword_match["missing_keywords"],
                "source_url": url,
            }

        except Exception as e:
            return None

    async def _fetch_and_extract_text(self, url: str) -> Optional[str]:
        """
        Fetch URL and extract clean text from HTML.

        Args:
            url: URL to fetch

        Returns:
            Extracted text, or None if failed
        """
        try:
            # Browser-like headers to avoid bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    url, headers=headers, allow_redirects=True
                ) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()

                    # Extract text using BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")

                    # Remove unwanted elements
                    for element in soup(
                        [
                            "script",
                            "style",
                            "nav",
                            "footer",
                            "header",
                            "aside",
                            "iframe",
                        ]
                    ):
                        element.decompose()

                    # Try to find main content
                    main_content = (
                        soup.find("article")
                        or soup.find("main")
                        or soup.find(class_=re.compile("article|content|main", re.I))
                        or soup.find("body")
                    )

                    if not main_content:
                        return None

                    # Extract text
                    text = main_content.get_text(separator=" ", strip=True)

                    # Clean up whitespace
                    text = " ".join(text.split())

                    return text

        except Exception:
            return None

    def _calculate_tfidf_similarity(self, claim: str, source_text: str) -> float:
        """
        Calculate TF-IDF cosine similarity between claim and source.

        Args:
            claim: Claim text
            source_text: Source document text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            # Limit source text to first 10000 chars for performance
            source_text = source_text[:10000]

            vectorizer = TfidfVectorizer(
                stop_words="english", max_features=500, ngram_range=(1, 2)
            )

            # Create vectors
            vectors = vectorizer.fit_transform([claim, source_text])

            # Calculate cosine similarity
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

            return float(similarity)

        except Exception:
            return 0.0

    def _calculate_keyword_match(self, claim: str, source_text: str) -> Dict[str, Any]:
        """
        Calculate keyword matching between claim and source.

        Args:
            claim: Claim text
            source_text: Source document text

        Returns:
            Dict with match rate and keyword details
        """
        # Extract keywords (words >= 4 chars, excluding common words)
        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "been",
            "were",
            "that",
            "which",
            "these",
            "those",
        }

        claim_words = set(
            word.lower()
            for word in re.findall(r"\b\w{4,}\b", claim)
            if word.lower() not in stop_words
        )

        if not claim_words:
            return {"match_rate": 0.0, "found_keywords": [], "missing_keywords": []}

        source_lower = source_text.lower()

        found = []
        missing = []

        for word in claim_words:
            if word in source_lower:
                found.append(word)
            else:
                missing.append(word)

        match_rate = len(found) / len(claim_words) if claim_words else 0.0

        return {
            "match_rate": match_rate,
            "found_keywords": found[:10],  # Limit to first 10
            "missing_keywords": missing[:10],
        }

    def _find_best_matching_passage(
        self, claim: str, source_text: str
    ) -> Dict[str, Any]:
        """
        Find the passage in source that best matches the claim.

        Args:
            claim: Claim text
            source_text: Source document text

        Returns:
            Dict with best passage and similarity score
        """
        # Split source into sentences
        sentences = re.split(r"(?<=[.!?])\s+", source_text[:10000])

        best_passage = ""
        best_score = 0.0

        try:
            for sentence in sentences:
                if len(sentence) < 20:
                    continue

                # Calculate similarity for this sentence
                score = self._calculate_tfidf_similarity(claim, sentence)

                if score > best_score:
                    best_score = score
                    best_passage = sentence

        except Exception:
            pass

        return {"passage": best_passage, "score": best_score}

    def _calculate_match_distribution(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Calculate distribution of match quality levels.

        Args:
            results: List of verification results

        Returns:
            Dict with counts for each quality level
        """
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNVERIFIABLE": 0}

        for result in results:
            quality = result.get("match_quality", "UNVERIFIABLE")
            distribution[quality] += 1

        return distribution
        return distribution
