# Evidence Match Quality Metric

## Overview

The **Evidence Match Quality** metric evaluates whether the sources cited in a report actually support the claims being made. This is critical for ensuring factual accuracy and preventing hallucinations or misrepresentation of sources.

## Purpose

While Citation Accuracy checks if sources are accessible and credible, and Claim Support Rate checks if claims have citations, Evidence Match Quality answers the question: **"Do the cited sources actually say what the claim states?"**

## Methodology

The metric uses a multi-factor approach to measure how well source content matches claims:

### 1. **TF-IDF Similarity (50% weight)**

- Calculates term frequency-inverse document frequency vectors for claim and source
- Uses cosine similarity to measure semantic alignment
- Handles synonyms and related terminology
- **Why it matters**: Detects if the source discusses similar concepts, even with different wording

### 2. **Keyword Matching (30% weight)**

- Extracts significant keywords from claim (≥4 chars, excluding stop words)
- Checks what percentage appear in source content
- Tracks found vs. missing keywords
- **Why it matters**: Ensures specific terms and entities mentioned in claims appear in sources

### 3. **Best Passage Similarity (20% weight)**

- Finds the most relevant sentence in the source
- Calculates TF-IDF similarity at sentence level
- Identifies the exact supporting evidence
- **Why it matters**: Pinpoints where in the source the claim is supported

## Composite Scoring

Final score = `(TF-IDF × 0.5) + (Keyword Match × 0.3) + (Best Passage × 0.2)`

**Match Quality Classification:**

- **HIGH** (≥0.7): Strong evidence match - source clearly supports claim
- **MEDIUM** (0.4-0.69): Partial match - source discusses topic but support is weak
- **LOW** (<0.4): Poor match - source doesn't adequately support claim
- **UNVERIFIABLE**: Unable to fetch or process source content

## Implementation Details

### Text Extraction

- Uses BeautifulSoup4 to extract clean text from HTML
- Focuses on main content (article, main tags)
- Removes navigation, scripts, styles, footers
- Handles paywalls and 403 errors gracefully

### Performance Optimizations

- Limits source text to first 10,000 characters
- 15-second timeout per URL fetch
- Processes claims in parallel where possible
- Takes best match when claims cite multiple sources

### Technical Stack

- **aiohttp**: Async HTTP client for fetching sources
- **BeautifulSoup4**: HTML parsing and text extraction
- **scikit-learn**: TF-IDF vectorization and cosine similarity
- **lxml**: Enhanced HTML parsing

## Output Format

```json
{
  "metric_name": "evidence_match_quality",
  "score": 0.75,
  "passed_checks": 12,
  "total_checks": 18,
  "details": {
    "summary": "12/18 claims have high evidence match (75.3% avg)",
    "total_claims_analyzed": 18,
    "verifiable_claims": 16,
    "unverifiable_claims": 2,
    "average_match_score": 75.3,
    "match_distribution": {
      "HIGH": 12,
      "MEDIUM": 3,
      "LOW": 1,
      "UNVERIFIABLE": 2
    },
    "claim_verification_details": [
      {
        "claim": "GLP-1 receptor agonists reduce HbA1c by 1.0-1.5%...",
        "citations": ["1", "3"],
        "urls": ["https://pubmed.ncbi.nlm.nih.gov/..."],
        "composite_score": 0.83,
        "match_quality": "HIGH",
        "tfidf_similarity": 0.78,
        "keyword_match_rate": 0.92,
        "best_passage": "GLP-1 agonists demonstrated HbA1c reductions of 1.2%...",
        "passage_similarity": 0.81,
        "found_keywords": ["receptor", "agonists", "reduce", "HbA1c"],
        "missing_keywords": [],
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/..."
      }
    ]
  }
}
```

## Usage

```python
from app.verification.evidence_match import EvidenceMatchMetric

# Initialize metric
metric = EvidenceMatchMetric()

# Calculate for a report
result = await metric.calculate("workspace/my_report.md")

# Access results
print(f"Score: {result.score}")
print(f"High quality matches: {result.details['match_distribution']['HIGH']}")

# Examine specific claims
for claim_result in result.details['claim_verification_details']:
    if claim_result['match_quality'] == 'LOW':
        print(f"Poorly supported claim: {claim_result['claim']}")
        print(f"Missing keywords: {claim_result['missing_keywords']}")
```

## Integration with Other Metrics

Evidence Match Quality complements other verification metrics:

| Metric                 | What It Checks                        | Relationship                                      |
| ---------------------- | ------------------------------------- | ------------------------------------------------- |
| **Citation Accuracy**  | Are URLs accessible and credible?     | EMQ requires accessible sources                   |
| **Claim Support Rate** | Do claims have inline citations?      | EMQ verifies the cited sources                    |
| **Hallucination Rate** | Are claims unsupported or fabricated? | EMQ provides evidence for hallucination detection |

## Limitations

1. **Paywalled Content**: Cannot verify claims citing sources behind paywalls
2. **PDF Sources**: Current implementation focuses on HTML; PDFs not processed
3. **Technical Jargon**: TF-IDF may miss domain-specific synonym matches
4. **Context**: Measures textual similarity, not semantic correctness
5. **Sample Size**: Only analyzes first 10,000 characters of source for performance

## Best Practices

1. **Use with Citation Accuracy**: First verify sources are accessible before checking match quality
2. **Review LOW matches**: Manually inspect claims with low evidence match scores
3. **Check UNVERIFIABLE claims**: Investigate why sources couldn't be processed
4. **Monitor keyword mismatches**: Missing keywords may indicate misquoting or overgeneralization
5. **Compare with Claim Support**: Claims without citations won't be analyzed by EMQ

## Future Enhancements

- [ ] Support PDF source extraction
- [ ] Add semantic similarity using embeddings
- [ ] Implement quote extraction and verification
- [ ] Add support for image/figure citations
- [ ] Domain-specific keyword weighting for medical terms
- [ ] Citation context analysis (surrounding sentences)
