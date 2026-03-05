"""
Citation Accuracy Metric Module

This module provides the citation accuracy verification metric,
which validates citations in literature survey reports.

Components:
- metric.py: Main CitationAccuracyMetric implementation
- trusted_domains.py: Configuration of trusted academic/medical sources
- example_output.json: Sample output for reference
"""

from app.verification.citation_accuracy.metric import CitationAccuracyMetric

__all__ = ['CitationAccuracyMetric']
