"""
Evidence Match Quality V2 - Embeddings-based

This metric uses OpenAI embeddings to calculate semantic similarity between
claims and their cited sources. Simpler and more accurate than TF-IDF.

Approach:
1. Fetch content from citation URLs
2. Extract clean text from HTML
3. Generate embeddings for claim and source text
4. Calculate cosine similarity between embeddings
5. Score based on semantic similarity

Score Range: 0.0 to 1.0
- 0.8-1.0: High semantic match
- 0.6-0.79: Medium match
- 0.0-0.59: Low match
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

import aiohttp
import numpy as np
from bs4 import BeautifulSoup
from openai import OpenAI

from ..base import VerificationMetric, VerificationResult
from ..report_parser import ReportParser


class EvidenceMatchV2Metric(VerificationMetric):
    """
    Embeddings-based metric to evaluate whether cited sources support claims.

    Uses OpenAI text-embedding-3-small for semantic similarity calculation.
    Simpler and more accurate than TF-IDF + keyword matching.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        super().__init__("evidence_match_quality_v2")
        self.timeout = aiohttp.ClientTimeout(total=15)

        # Initialize OpenAI client
        import os

        from app.config import config

        # Try to get API key from: parameter > env var > config.toml
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                # config.llm is a dict with keys like "default"
                # Each value is an LLMSettings object with api_key attribute
                api_key = config.llm.get("default").api_key
            except (KeyError, TypeError, AttributeError):
                pass

        if not api_key:
            raise ValueError(
                "OpenAI API key required. Options:\n"
                "1. Pass openai_api_key parameter\n"
                "2. Set OPENAI_API_KEY environment variable\n"
                "3. Configure api_key in config/config.toml [llm] section"
            )

        self.client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-3-small"

    async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
        """
        Calculate evidence match quality using embeddings.

        Args:
            report_path: Path to the markdown report file
            **kwargs: Additional parameters (unused)

        Returns:
            VerificationResult with match scores and detailed analysis
        """
        # Read report content
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Parse report
        parser = ReportParser(report_path)
        parser.parse()

        # Extract claims with citations
        claims_with_citations = self._extract_claims_with_citations(report_content)

        # Build citation URL map
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
            # Average similarity score across all claims
            scores = [
                r["similarity_score"]
                for r in verification_results
                if r["similarity_score"] is not None
            ]
            if scores:
                score = sum(scores) / len(scores)
                high_match = sum(1 for s in scores if s >= 0.8)
                summary = f"{high_match}/{len(scores)} claims have high semantic match ({score*100:.1f}% avg)"
            else:
                score = 0.0
                summary = "Unable to verify claims (sources inaccessible)"

        # Prepare detailed breakdown
        details = {
            "summary": summary,
            "total_claims_analyzed": total_claims,
            "verifiable_claims": len(
                [r for r in verification_results if r["similarity_score"] is not None]
            ),
            "unverifiable_claims": len(
                [r for r in verification_results if r["similarity_score"] is None]
            ),
            "average_similarity_score": round(score * 100, 2),
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
                    if r.get("similarity_score") is not None
                    and r["similarity_score"] >= 0.8
                ]
            ),
            total_checks=total_claims,
            details=details,
        )

    def _extract_claims_with_citations(
        self, report_content: str
    ) -> List[Dict[str, Any]]:
        """Extract claims that have inline citations."""
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
            # Extract citation numbers
            citations = re.findall(r"\[(\d+)\]", sentence)
            if citations:
                claims.append(
                    {"claim": sentence.strip(), "citations": list(set(citations))}
                )

        return claims

    def _build_citation_url_map(self, report_content: str) -> Dict[str, str]:
        """Build mapping from citation numbers to URLs."""
        refs_match = re.search(
            r"^#{1,3}\s*References?\s*$(.+)",
            report_content,
            flags=re.MULTILINE | re.IGNORECASE | re.DOTALL,
        )

        if not refs_match:
            return {}

        references_section = refs_match.group(1)
        citation_url_map = {}

        # Extract citation number and URL pairs
        pattern = re.compile(r"\[(\d+)\][^\n]+?(https?://[^\s\)]+)")
        for match in pattern.finditer(references_section):
            citation_num = match.group(1)
            url = match.group(2).rstrip(".,;)")
            citation_url_map[citation_num] = url

        return citation_url_map

    async def _verify_claims(
        self,
        claims_with_citations: List[Dict[str, Any]],
        citation_url_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Verify each claim against its cited sources using embeddings."""
        results = []

        for claim_info in claims_with_citations:
            claim = claim_info["claim"]
            citations = claim_info["citations"]

            # Get URLs for citations
            urls = [
                citation_url_map[cit] for cit in citations if cit in citation_url_map
            ]

            if not urls:
                results.append(
                    {
                        "claim": claim,
                        "citations": citations,
                        "urls": [],
                        "similarity_score": None,
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
                if (
                    match_result
                    and match_result.get("similarity_score", 0) > best_score
                ):
                    best_score = match_result["similarity_score"]
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
                        "similarity_score": None,
                        "match_quality": "UNVERIFIABLE",
                        "reason": "Unable to fetch or process source content",
                    }
                )

        return results

    async def _verify_claim_against_url(
        self, claim: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Verify a claim against a source URL using embeddings."""
        try:
            # Fetch and extract text
            source_text = await self._fetch_and_extract_text(url)
            if not source_text or len(source_text) < 100:
                return None

            # Calculate similarity using embeddings
            similarity = self._calculate_embedding_similarity(claim, source_text)

            # Find best matching passage for context (uses embeddings)
            best_passage = self._find_best_passage(claim, source_text)

            # Classify match quality
            if similarity >= 0.8:
                match_quality = "HIGH"
            elif similarity >= 0.6:
                match_quality = "MEDIUM"
            else:
                match_quality = "LOW"

            return {
                "similarity_score": round(similarity, 3),
                "match_quality": match_quality,
                "best_passage": best_passage,  # Already truncated in _find_best_passage
                "source_url": url,
            }

        except Exception as e:
            return None

    async def _fetch_and_extract_text(self, url: str) -> Optional[str]:
        """Fetch URL and extract clean text from HTML."""
        try:
            # Browser-like headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
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

                    # Find main content
                    main_content = (
                        soup.find("article")
                        or soup.find("main")
                        or soup.find(class_=re.compile("article|content|main", re.I))
                        or soup.find("body")
                    )

                    if not main_content:
                        return None

                    # Extract and clean text
                    text = main_content.get_text(separator=" ", strip=True)
                    text = " ".join(text.split())

                    return text

        except Exception:
            return None

    def _calculate_embedding_similarity(self, claim: str, source_text: str) -> float:
        """
        Calculate cosine similarity between claim and source using embeddings.

        Args:
            claim: Claim text
            source_text: Source document text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            # Limit source text for embedding (max ~8000 tokens for embedding model)
            max_chars = 30000  # ~8k tokens
            if len(source_text) > max_chars:
                source_text = source_text[:max_chars]

            # Remove citation markers from claim for cleaner embedding
            clean_claim = re.sub(r"\[\d+\]", "", claim).strip()

            # Get embeddings
            response = self.client.embeddings.create(
                input=[clean_claim, source_text], model=self.embedding_model
            )

            # Extract embedding vectors
            claim_embedding = np.array(response.data[0].embedding)
            source_embedding = np.array(response.data[1].embedding)

            # Calculate cosine similarity
            similarity = np.dot(claim_embedding, source_embedding) / (
                np.linalg.norm(claim_embedding) * np.linalg.norm(source_embedding)
            )

            return float(similarity)

        except Exception as e:
            return 0.0

    def _find_best_passage(self, claim: str, source_text: str) -> str:
        """
        Find the passage in source that best matches the claim using embeddings.

        Args:
            claim: Claim text
            source_text: Source document text

        Returns:
            Best matching passage (up to 300 chars)
        """
        try:
            # Remove citation markers from claim
            clean_claim = re.sub(r"\[\d+\]", "", claim).strip()

            # Split source into sentences
            sentences = re.split(r"(?<=[.!?])\s+", source_text[:20000])

            # Filter substantial sentences (at least 50 chars)
            substantial_sentences = [s for s in sentences if len(s.strip()) >= 50]

            if not substantial_sentences:
                return ""

            # Limit to processing first 50 sentences for performance
            sentences_to_check = substantial_sentences[:50]

            # Get embeddings for claim and all sentences
            texts_to_embed = [clean_claim] + sentences_to_check
            response = self.client.embeddings.create(
                input=texts_to_embed, model=self.embedding_model
            )

            # Extract embeddings
            claim_embedding = np.array(response.data[0].embedding)
            sentence_embeddings = [
                np.array(response.data[i].embedding)
                for i in range(1, len(response.data))
            ]

            # Calculate similarity for each sentence
            best_similarity = 0.0
            best_sentence = sentences_to_check[0]

            for sentence, sentence_emb in zip(sentences_to_check, sentence_embeddings):
                similarity = np.dot(claim_embedding, sentence_emb) / (
                    np.linalg.norm(claim_embedding) * np.linalg.norm(sentence_emb)
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_sentence = sentence

            # Truncate if too long
            if len(best_sentence) > 300:
                return best_sentence[:297] + "..."

            return best_sentence.strip()

        except Exception as e:
            # Fallback to first substantial sentence
            sentences = re.split(r"(?<=[.!?])\s+", source_text[:10000])
            for sentence in sentences:
                if len(sentence) > 50:
                    return (
                        (sentence[:297] + "...")
                        if len(sentence) > 300
                        else sentence.strip()
                    )
            return ""

    def _calculate_match_distribution(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Calculate distribution of match quality levels."""
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNVERIFIABLE": 0}

        for result in results:
            quality = result.get("match_quality", "UNVERIFIABLE")
            distribution[quality] += 1

        return distribution

        return distribution
