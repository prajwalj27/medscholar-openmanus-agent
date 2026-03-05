"""
Verification Layer for MedScholar Agent

This module provides metrics and tools to verify the factual reliability
of generated literature survey reports.

Metrics implemented:
- Citation Accuracy: Verify that cited sources are accessible and valid
- Claim Support Rate: Measure percentage of claims with inline citations
- Evidence Match Quality: Measure alignment between claims and cited sources
  - V1: TF-IDF + keyword matching (offline, no API required)
  - V2: OpenAI embeddings (better accuracy, requires API key)
- Hallucination Rate: Identify unsupported or fabricated claims (planned)

Structure:
- base.py: Base classes for all metrics
- report_parser.py: Parse markdown reports to extract citations/claims
- citation_accuracy/: Citation accuracy metric implementation
- claim_support/: Claim support rate metric implementation
- evidence_match/: Evidence match quality V1 (TF-IDF) implementation
- evidence_match_v2/: Evidence match quality V2 (embeddings) implementation
"""

from app.verification.base import VerificationMetric, VerificationResult
from app.verification.citation_accuracy import CitationAccuracyMetric
from app.verification.claim_support import ClaimSupportMetric
from app.verification.evidence_match import EvidenceMatchMetric
from app.verification.evidence_match_v2 import EvidenceMatchV2Metric
from app.verification.report_parser import ReportParser

__all__ = [
    "VerificationMetric",
    "VerificationResult",
    "CitationAccuracyMetric",
    "ClaimSupportMetric",
    "EvidenceMatchMetric",
    "EvidenceMatchV2Metric",
    "ReportParser",
]
