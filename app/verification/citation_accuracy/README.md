# Citation Accuracy Metric

Validates the quality and credibility of citations in literature survey reports.

## Overview

This metric performs comprehensive validation of citations by checking multiple factors:

- **URL Accessibility**: Whether cited URLs are reachable
- **Source Credibility**: Whether citations are from trusted academic/medical sources
- **Duplicate Detection**: Identifies repeated URLs
- **Suspicious Patterns**: Flags fake/placeholder citations (e.g., example.com)

## Scoring System

Multi-factor scoring (0.0 to 1.0):

| Component      | Weight | Description                             |
| -------------- | ------ | --------------------------------------- |
| Accessibility  | 40%    | Citations are accessible (HTTP 200-399) |
| Credibility    | 30%    | Citations from trusted sources          |
| Uniqueness     | 20%    | No excessive duplicate URLs             |
| Non-suspicious | 10%    | No fake/placeholder URLs                |

### Individual Citation Credibility

Each citation receives a credibility score (0.0 to 1.0):

- **Suspicious URL** (example.com, localhost): 0.0
- **Accessible only**: 0.5
- **Trusted domain**: 0.9-1.0
- **Not accessible**: Reduced score

A citation is marked "valid" if:

- Credibility score >= 0.5
- Not flagged as suspicious
- Accessible (if accessibility check enabled)

## Usage

```python
from app.verification import CitationAccuracyMetric

metric = CitationAccuracyMetric()

# Calculate with URL accessibility checks (default)
result = await metric.calculate("path/to/report.md")

# Skip accessibility checks (faster, less thorough)
result = await metric.calculate(
    "path/to/report.md",
    check_accessibility=False
)

# Custom timeout for URL checks
result = await metric.calculate(
    "path/to/report.md",
    timeout=30  # seconds
)
```

## Output

Returns a `VerificationResult` with:

```python
{
    "metric_name": "Citation Accuracy",
    "score": 0.75,  # Overall score (0.0 to 1.0)
    "passed_checks": 8,  # Number of valid citations
    "total_checks": 10,  # Total citations
    "accuracy_percentage": 75.0,

    "details": {
        "total_citations": 10,
        "valid_citations": 8,
        "invalid_citations": 2,
        "trusted_sources": 6,  # From trusted domains
        "suspicious_citations": 1,  # Fake URLs
        "duplicate_urls": 0,
        "unique_urls": 10,

        "score_breakdown": {
            "accessibility_score": 0.32,  # 40% weight
            "credibility_score": 0.24,    # 30% weight
            "uniqueness_score": 0.20,     # 20% weight
            "non_suspicious_score": 0.09  # 10% weight
        },

        "citation_details": [
            {
                "index": 1,
                "title": "Study Title",
                "url": "https://pubmed.ncbi.nlm.nih.gov/...",
                "is_accessible": true,
                "is_trusted_source": true,
                "is_suspicious": false,
                "credibility_score": 0.9,
                "is_valid": true,
                "http_status": 200,
                "page_title": "PubMed - Study Title"
            },
            // ... more citations
        ],

        "warnings": [
            "Suspicious URL detected: http://example.com"
        ]
    },

    "errors": [],
    "timestamp": "2026-03-04T10:30:00"
}
```

## Configuration

### Trusted Domains

Trusted sources are configured in [`trusted_domains.py`](trusted_domains.py).

Categories include:

- Medical databases (PubMed, Cochrane, ClinicalTrials.gov)
- Academic publishers (Nature, Science, NEJM, Lancet)
- Government health agencies (FDA, CDC, WHO, NHS)
- Research repositories (bioRxiv, medRxiv)
- Medical organizations (AHA, ADA, AMA)

To customize:

```python
from app.verification.citation_accuracy.trusted_domains import (
    get_trusted_domains,
    get_trust_level
)

# Get all trusted domains
domains = get_trusted_domains(include_universities=True)

# Check trust level
level = get_trust_level("pubmed.ncbi.nlm.nih.gov")  # Returns 'high'
```

### Suspicious Patterns

Patterns that indicate fake citations:

- `example.com`, `example.org`, `test.com`
- `localhost`, `127.0.0.1`
- `placeholder`, `dummy`, `fake`

## Examples

### High-Quality Report (90%+ score)

```markdown
## References

1. [Diabetes Management Guidelines](https://www.nejm.org/doi/full/10.1056/NEJMoa...)
2. [Meta-analysis of GLP-1 Agonists](https://www.thelancet.com/journals/lancet/article/...)
3. [Clinical Trial Results](https://clinicaltrials.gov/ct2/show/NCT...)
```

**Result:**

- Total citations: 3
- Valid: 3
- Trusted sources: 3
- **Score: 1.0 (100%)**

### Low-Quality Report (<50% score)

```markdown
## References

1. [Study](http://example.com)
2. [Research](http://example.com)
3. [Guidelines](http://test.com/article)
```

**Result:**

- Total citations: 3
- Valid: 0
- Suspicious: 3
- Duplicates: 1
- **Score: 0.0 (0%)**

### Mixed-Quality Report (~60% score)

```markdown
## References

1. [NEJM Study](https://www.nejm.org/doi/...) # ✓ Trusted
2. [Random Blog](https://myblog.com/health) # ✗ Not trusted
3. [PubMed Article](https://pubmed.ncbi.nlm.nih.gov/...) # ✓ Trusted
4. [Broken Link](https://journal.fake/404) # ✗ Not accessible
```

**Result:**

- Total citations: 4
- Valid: 2 (trusted + accessible)
- Trusted sources: 2
- **Score: ~0.60 (60%)**

## Design Decisions

### Why Multi-Factor Scoring?

Simple binary validation (pass/fail) doesn't capture nuance:

- A report with accessible but non-trusted sources is better than fake URLs
- A report with trusted sources that happen to be temporarily down shouldn't fail completely

### Why These Trust Levels?

Based on academic standards:

- **High trust**: Peer-reviewed journals, government agencies, major databases
- **Medium trust**: Preprint servers, open access publishers, universities
- **Unknown**: General websites (not automatically bad, but needs scrutiny)

### Why Penalize Duplicates?

Citing the same source multiple times suggests:

- Low-quality research (limited source diversity)
- Padding citations artificially
- Potential copy-paste errors

## Limitations

1. **Domain-based trust**: Doesn't verify actual content quality
2. **No retraction checking**: Can't detect retracted papers
3. **Accessibility**: URL might be down temporarily
4. **Paywalls**: Some valid sources might block automated access
5. **Trust list maintenance**: Requires periodic updates

## Future Improvements

- [ ] Add retraction database checking (RetractionWatch API)
- [ ] Implement trust tiers (high/medium/low) instead of binary
- [ ] Cache URL accessibility results
- [ ] Support for DOI resolution
- [ ] Citation format validation (APA, MLA, etc.)
- [ ] Content relevance checking (match citation to claim)

## Files

- **`metric.py`**: Main implementation
- **`trusted_domains.py`**: Domain configuration
- **`example_output.json`**: Sample output for reference
- **`README.md`**: This file
