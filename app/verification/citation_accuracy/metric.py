"""
Citation Accuracy Metric

Verifies that citations in the report are valid and accessible.
"""

import asyncio
import re
from collections import Counter
from typing import Any, Dict, List
from urllib.parse import urlparse

import aiohttp

from app.logger import logger
from app.verification.base import VerificationMetric, VerificationResult
from app.verification.report_parser import Citation, ReportParser


class CitationAccuracyMetric(VerificationMetric):
    """
    Measures the accuracy and validity of citations in a report.

    Checks:
    1. URL Accessibility: Whether cited URLs are reachable (HTTP 200)
    2. URL Format: Whether URLs are properly formatted
    3. Source Credibility: Whether URLs are from reputable academic/medical sources
    4. Content Relevance: Whether page content matches citation
    5. Duplicate Detection: Flags citations pointing to the same URL

    Score calculation:
    - Multi-factor scoring system considering:
        * URL format and accessibility (40%)
        * Source credibility (30%)
        * Content validation (20%)
        * Uniqueness penalty for duplicates (10%)
    """

    # Reputable academic and medical domains
    TRUSTED_DOMAINS = {
        # Medical/Health databases
        'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov',
        'nih.gov', 'cdc.gov', 'who.int',
        'clinicaltrials.gov',  # Clinical trial registry
        'cochrane.org', 'cochranelibrary.com',  # Systematic reviews
        'uptodate.com',  # Clinical decision support

        # Academic publishers & journals
        'springer.com', 'link.springer.com',
        'sciencedirect.com', 'elsevier.com',
        'nature.com', 'science.org', 'cell.com',
        'wiley.com', 'onlinelibrary.wiley.com',
        'tandfonline.com', 'sagepub.com',
        'oxford.com', 'academic.oup.com',
        'cambridge.org',
        'plos.org', 'plosone.org',
        'bmj.com', 'thelancet.com', 'nejm.org',
        'jamanetwork.com', 'annals.org',
        'frontiersin.org',  # Open access publisher
        'mdpi.com',  # Multidisciplinary Digital Publishing Institute
        'karger.com',  # Medical and scientific publisher

        # Medical organizations & societies
        'aasm.org', 'ama-assn.org', 'acc.org',
        'heart.org', 'mayoclinic.org', 'clevelandclinic.org',
        'diabetes.org',  # American Diabetes Association
        'cancer.org', 'cancer.gov',  # Cancer research
        'stroke.org',  # American Stroke Association

        # Research repositories & databases
        'arxiv.org', 'biorxiv.org', 'medrxiv.org',
        'researchgate.net', 'scholar.google.com',
        'europepmc.org',  # Europe PubMed Central
        'semanticscholar.org',  # AI-powered research tool

        # Government health agencies (US)
        'fda.gov', 'hhs.gov', 'cms.gov',

        # International health agencies
        'nhs.uk',  # UK National Health Service
        'health.gov.au',  # Australia
        'canada.ca',  # Health Canada
        'ema.europa.eu',  # European Medicines Agency

        # University & institutional repositories
        'harvard.edu', 'stanford.edu', 'mit.edu',
        'jhu.edu',  # Johns Hopkins
        'mayo.edu',  # Mayo Clinic
    }

    # Suspicious patterns that indicate fake citations
    SUSPICIOUS_PATTERNS = [
        'example.com', 'example.org', 'test.com',
        'localhost', '127.0.0.1',
        'placeholder', 'dummy', 'fake'
    ]

    def __init__(self):
        super().__init__("Citation Accuracy")
        self.timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout per URL

    async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
        """
        Calculate citation accuracy for a report.

        Args:
            report_path: Path to the report markdown file
            **kwargs: Optional parameters
                - check_accessibility: Whether to check URL accessibility (default: True)
                - timeout: Request timeout in seconds (default: 10)

        Returns:
            VerificationResult with citation accuracy score
        """
        check_accessibility = kwargs.get('check_accessibility', True)
        custom_timeout = kwargs.get('timeout', 10)
        self.timeout = aiohttp.ClientTimeout(total=custom_timeout)

        try:
            # Parse the report
            parser = ReportParser(report_path)
            parser.parse()
            citations = parser.get_citations()

            if not citations:
                logger.warning(f"No citations found in report: {report_path}")
                return self._create_result(
                    score=0.0,
                    passed=0,
                    total=0,
                    details={"message": "No citations found in report"},
                    errors=["No citations found"]
                )

            # Check each citation
            citation_results = await self._check_citations(citations, check_accessibility)

            # Detect duplicate URLs and suspicious patterns
            url_analysis = self._analyze_urls(citations)

            # Calculate multi-factor score
            score_data = self._calculate_comprehensive_score(citation_results, url_analysis)

            valid_count = score_data['valid_count']
            total_count = len(citation_results)
            score = score_data['overall_score']

            # Prepare detailed results
            details = {
                "total_citations": total_count,
                "valid_citations": valid_count,
                "invalid_citations": total_count - valid_count,
                "citations_with_urls": sum(1 for r in citation_results if r['has_url']),
                "accessible_urls": sum(1 for r in citation_results if r['is_accessible']),
                "trusted_sources": sum(1 for r in citation_results if r.get('is_trusted_source', False)),
                "suspicious_citations": sum(1 for r in citation_results if r.get('is_suspicious', False)),
                "duplicate_urls": url_analysis['duplicate_count'],
                "unique_urls": url_analysis['unique_count'],
                "score_breakdown": score_data['breakdown'],
                "citation_details": citation_results,
                "warnings": url_analysis['warnings'],
            }

            # Collect errors and warnings
            errors = [r['error'] for r in citation_results if r.get('error')]
            errors.extend(url_analysis['warnings'])

            logger.info(
                f"Citation Accuracy: {score:.2%} "
                f"({valid_count}/{total_count} high-quality citations) "
                f"[Trusted: {details['trusted_sources']}, Suspicious: {details['suspicious_citations']}, "
                f"Duplicates: {details['duplicate_urls']}]"
            )

            return self._create_result(
                score=score,
                passed=valid_count,
                total=total_count,
                details=details,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Error calculating citation accuracy: {e}")
            return self._create_result(
                score=0.0,
                passed=0,
                total=0,
                details={},
                errors=[str(e)]
            )

    async def _check_citations(
        self,
        citations: List[Citation],
        check_accessibility: bool
    ) -> List[Dict[str, Any]]:
        """
        Check validity of all citations.

        Args:
            citations: List of Citation objects
            check_accessibility: Whether to check URL accessibility

        Returns:
            List of dictionaries with check results
        """
        results = []

        # Check URLs in parallel using asyncio
        if check_accessibility:
            accessibility_tasks = [
                self._check_url_accessibility(citation.url)
                for citation in citations
            ]
            accessibility_results = await asyncio.gather(*accessibility_tasks)
        else:
            accessibility_results = [None] * len(citations)

        for citation, accessibility in zip(citations, accessibility_results):
            result = {
                "index": citation.index,
                "title": citation.title,
                "url": citation.url,
                "has_url": citation.url is not None and citation.url != "",
                "is_valid_format": self._is_valid_url_format(citation.url) if citation.url else False,
                "is_accessible": False,
                "http_status": None,
                "error": None,
                "is_valid": False,
                "is_trusted_source": False,
                "is_suspicious": False,
                "credibility_score": 0.0,
                "page_title": None,
            }

            if accessibility:
                result["is_accessible"] = accessibility["accessible"]
                result["http_status"] = accessibility["status_code"]
                result["error"] = accessibility.get("error")
                result["page_title"] = accessibility.get("page_title")

            # Check if domain is trusted
            if citation.url:
                result["is_trusted_source"] = self._is_trusted_domain(citation.url)
                result["is_suspicious"] = self._is_suspicious_url(citation.url)
                result["credibility_score"] = self._calculate_credibility_score(
                    citation.url,
                    result["is_accessible"],
                    result["is_trusted_source"],
                    result["is_suspicious"]
                )

            # A citation is valid if it passes multiple checks
            if result["has_url"] and result["is_valid_format"]:
                if check_accessibility:
                    # More stringent validation
                    result["is_valid"] = (
                        result["is_accessible"] and
                        not result["is_suspicious"] and
                        result["credibility_score"] >= 0.5
                    )
                else:
                    result["is_valid"] = not result["is_suspicious"]

            results.append(result)

        return results

    def _is_valid_url_format(self, url: str) -> bool:
        """
        Check if URL is properly formatted.

        Args:
            url: URL string to validate

        Returns:
            True if URL has valid format
        """
        if not url:
            return False

        try:
            result = urlparse(url)
            # Must have scheme (http/https) and network location (domain)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False

    async def _check_url_accessibility(self, url: str) -> Dict[str, Any]:
        """
        Check if a URL is accessible and fetch page title.

        Args:
            url: URL to check

        Returns:
            Dictionary with accessibility information
        """
        if not url or not self._is_valid_url_format(url):
            return {
                "accessible": False,
                "status_code": None,
                "error": "Invalid or missing URL",
                "page_title": None
            }

        # Browser-like headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Try HEAD request first (faster)
                try:
                    async with session.head(
                        url,
                        headers=headers,
                        allow_redirects=True,
                        ssl=False  # Don't verify SSL to avoid certificate issues
                    ) as response:
                        accessible = 200 <= response.status < 400

                        # If accessible, try to get page title with GET request
                        page_title = None
                        if accessible:
                            try:
                                async with session.get(url, headers=headers, allow_redirects=True, ssl=False) as get_response:
                                    if get_response.status == 200:
                                        content = await get_response.text()
                                        page_title = self._extract_title(content)
                            except:
                                pass  # Title extraction is optional

                        return {
                            "accessible": accessible,
                            "status_code": response.status,
                            "error": None if accessible else f"HTTP {response.status}",
                            "page_title": page_title
                        }
                except aiohttp.ClientError:
                    # If HEAD fails, try GET request
                    async with session.get(
                        url,
                        headers=headers,
                        allow_redirects=True,
                        ssl=False
                    ) as response:
                        accessible = 200 <= response.status < 400
                        page_title = None
                        if accessible:
                            content = await response.text()
                            page_title = self._extract_title(content)

                        return {
                            "accessible": accessible,
                            "status_code": response.status,
                            "error": None if accessible else f"HTTP {response.status}",
                            "page_title": page_title
                        }
        except asyncio.TimeoutError:
            return {
                "accessible": False,
                "status_code": None,
                "error": "Request timeout",
                "page_title": None
            }
        except aiohttp.ClientError as e:
            return {
                "accessible": False,
                "status_code": None,
                "error": f"Connection error: {str(e)}",
                "page_title": None
            }
        except Exception as e:
            return {
                "accessible": False,
                "status_code": None,
                "error": f"Unknown error: {str(e)}",
                "page_title": None
            }

    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML content."""
        try:
            # Simple regex to extract title tag
            match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up the title
                title = re.sub(r'\s+', ' ', title)
                return title[:200]  # Limit length
        except:
            pass
        return None

    def _is_trusted_domain(self, url: str) -> bool:
        """Check if URL is from a trusted academic/medical source."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check exact match
            if domain in self.TRUSTED_DOMAINS:
                return True

            # Check if it's a subdomain of a trusted domain
            for trusted in self.TRUSTED_DOMAINS:
                if domain.endswith('.' + trusted) or domain == trusted:
                    return True

            return False
        except:
            return False

    def _is_suspicious_url(self, url: str) -> bool:
        """Check if URL matches suspicious patterns."""
        url_lower = url.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in url_lower:
                return True
        return False

    def _calculate_credibility_score(
        self,
        url: str,
        is_accessible: bool,
        is_trusted: bool,
        is_suspicious: bool
    ) -> float:
        """
        Calculate a credibility score for a citation (0.0 to 1.0).

        Scoring:
        - Accessible: +0.4
        - Trusted domain: +0.5
        - Not suspicious: +0.1
        - Suspicious: -1.0 (override to 0)
        """
        if is_suspicious:
            return 0.0

        score = 0.0

        if is_accessible:
            score += 0.4

        if is_trusted:
            score += 0.5
        else:
            # Even non-trusted sources get some credit if accessible
            score += 0.1

        return min(1.0, score)

    def _analyze_urls(self, citations: List[Citation]) -> Dict[str, Any]:
        """
        Analyze URL patterns to detect duplicates and issues.

        Returns:
            Dictionary with analysis results
        """
        urls = [c.url for c in citations if c.url]
        url_counts = Counter(urls)

        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        unique_count = len(url_counts)
        duplicate_count = sum(count - 1 for count in duplicates.values())

        warnings = []

        # Warn about duplicate URLs
        for url, count in duplicates.items():
            warnings.append(
                f"Duplicate URL found {count} times: {url}"
            )

        # Warn if all citations point to the same domain
        if unique_count == 1 and len(citations) > 1:
            warnings.append(
                f"All {len(citations)} citations point to the same URL - highly suspicious"
            )

        # Warn about suspicious patterns
        for citation in citations:
            if citation.url and self._is_suspicious_url(citation.url):
                warnings.append(
                    f"Suspicious URL detected: {citation.url}"
                )

        return {
            'unique_count': unique_count,
            'duplicate_count': duplicate_count,
            'duplicates': duplicates,
            'warnings': warnings
        }

    def _calculate_comprehensive_score(
        self,
        citation_results: List[Dict[str, Any]],
        url_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive score using multi-factor analysis.

        Scoring breakdown:
        - Accessibility (40%): Citations are accessible
        - Credibility (30%): Citations from trusted sources
        - Uniqueness (20%): No excessive duplicate URLs
        - Non-suspicious (10%): No fake/placeholder URLs
        """
        total = len(citation_results)
        if total == 0:
            return {
                'overall_score': 0.0,
                'valid_count': 0,
                'breakdown': {}
            }

        # Accessibility score (40%)
        accessible_count = sum(1 for r in citation_results if r['is_accessible'])
        accessibility_score = (accessible_count / total) * 0.4

        # Credibility score (30%) - average of individual credibility scores
        avg_credibility = sum(r['credibility_score'] for r in citation_results) / total
        credibility_score = avg_credibility * 0.3

        # Uniqueness score (20%) - penalize duplicates
        if url_analysis['duplicate_count'] > 0:
            # Penalty for duplicates
            duplicate_ratio = url_analysis['duplicate_count'] / total
            uniqueness_score = max(0, 0.2 - (duplicate_ratio * 0.2))
        else:
            uniqueness_score = 0.2

        # Non-suspicious score (10%)
        suspicious_count = sum(1 for r in citation_results if r['is_suspicious'])
        non_suspicious_score = ((total - suspicious_count) / total) * 0.1

        # Overall score
        overall_score = (
            accessibility_score +
            credibility_score +
            uniqueness_score +
            non_suspicious_score
        )

        # Count as valid if credibility score >= 0.5 and not suspicious
        valid_count = sum(
            1 for r in citation_results
            if r['credibility_score'] >= 0.5 and not r['is_suspicious']
        )

        return {
            'overall_score': overall_score,
            'valid_count': valid_count,
            'breakdown': {
                'accessibility_score': round(accessibility_score, 3),
                'credibility_score': round(credibility_score, 3),
                'uniqueness_score': round(uniqueness_score, 3),
                'non_suspicious_score': round(non_suspicious_score, 3),
                'accessible_citations': accessible_count,
                'trusted_sources': sum(1 for r in citation_results if r['is_trusted_source']),
                'suspicious_citations': suspicious_count,
                'duplicate_citations': url_analysis['duplicate_count'],
            }
        }
        }
