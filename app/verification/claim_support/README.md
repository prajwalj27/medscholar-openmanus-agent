# Claim Support Rate Metric

## Overview

The **Claim Support Rate** metric measures the percentage of factual claims in a literature survey report that are properly supported by inline citations (e.g., [1], [2], [3]).

This is a critical metric for scientific credibility because every factual statement should be traceable to its source through inline citations.

## Formula

```
Claim Support Rate = (Claims with Citations / Total Claims) × 100
Score (0.0 to 1.0) = Claims with Citations / Total Claims
```

## What It Measures

### Supported Claims

A claim is considered **supported** if it contains at least one inline citation marker:

- ✅ "Metformin reduces HbA1c levels by 1-2% [1]."
- ✅ "Studies show cardiovascular benefits [2][3]."
- ✅ "The incidence rate is approximately 5% [4]."

### Unsupported Claims

A claim is **unsupported** if it lacks inline citation markers:

- ❌ "Metformin is the first-line therapy for diabetes."
- ❌ "Recent studies have shown positive outcomes."
- ❌ "The treatment is well-tolerated by most patients."

## Score Interpretation

| Score Range | Interpretation                | Action Needed                    |
| ----------- | ----------------------------- | -------------------------------- |
| 0.90 - 1.00 | Excellent citation coverage   | None - maintain quality          |
| 0.70 - 0.89 | Good coverage with minor gaps | Review unsupported claims        |
| 0.50 - 0.69 | Moderate coverage             | Significant improvement needed   |
| 0.30 - 0.49 | Poor coverage                 | Major revision required          |
| 0.00 - 0.29 | Very poor coverage            | Complete citation audit required |

## Implementation Details

### Claim Extraction

The metric extracts claims using the following criteria:

- Sentences containing medical/scientific terms
- Sentences with statistics or percentages
- Sentences with factual assertions (using verbs like "is", "shows", "indicates")
- Minimum sentence length of 20 characters
- Excludes headings, questions, and the References section

### Citation Detection

Inline citations are detected using the pattern: `[1]`, `[2]`, `[3]`, etc.

- Supports multiple citations per claim: `[1][2]` or `[1], [2]`
- Counts claims with at least one citation as supported

### Analysis Provided

The metric provides:

- Total number of claims
- Number of supported claims
- Number of unsupported claims
- Support rate percentage
- Examples of supported and unsupported claims
- Claims breakdown by section
- Citation usage patterns (multiple citations, averages)

## Usage

```python
from app.verification import ClaimSupportMetric

# Initialize the metric
metric = ClaimSupportMetric()

# Calculate for a report
with open("workspace/my_survey.md", "r") as f:
    report_content = f.read()

result = await metric.calculate(report_content)

print(f"Score: {result.score}")
print(f"Message: {result.message}")
print(f"Supported: {result.details['supported_claims']}/{result.details['total_claims']}")
```

## Example Output

```json
{
  "metric_name": "claim_support_rate",
  "score": 0.85,
  "message": "17/20 claims have inline citations (85.0%)",
  "details": {
    "total_claims": 20,
    "supported_claims": 17,
    "unsupported_claims": 3,
    "support_rate_percentage": 85.0,
    "supported_examples": [
      {
        "claim": "Metformin reduces HbA1c levels by 1-2% [1].",
        "citations": ["[1]"],
        "citation_count": 1
      }
    ],
    "unsupported_examples": [
      {
        "claim": "The treatment is generally well-tolerated.",
        "reason": "No inline citation marker found"
      }
    ],
    "analysis": {
      "claims_by_section": {
        "Introduction": 3,
        "Key Findings": 12,
        "Conclusion": 5
      },
      "citation_pattern": {
        "total_inline_citations": 22,
        "claims_with_multiple_citations": 5,
        "max_citations_per_claim": 3,
        "avg_citations_per_supported_claim": 1.29
      }
    }
  }
}
```

## Relationship to Other Metrics

- **Citation Accuracy**: Verifies that the URLs/sources are valid and accessible
- **Claim Support Rate**: Verifies that claims have inline citations pointing to sources
- **Evidence Match Quality**: Verifies that the cited sources actually support the claims
- **Hallucination Rate**: Identifies claims that are fabricated or unsupported by literature

All four metrics work together to ensure comprehensive factual reliability.

## Limitations

1. **Claim Detection**: Uses heuristics to identify claims; may miss some edge cases
2. **Citation Format**: Only detects numbered citations [1], [2], etc. (not author-year style)
3. **Quality vs Quantity**: A claim with a citation isn't necessarily accurate (see Citation Accuracy metric)
4. **Context**: Doesn't verify that the citation actually supports the specific claim (see Evidence Match Quality)

## Best Practices

1. **Target Score**: Aim for ≥ 0.90 (90%+ claims with citations)
2. **Review Unsupported Claims**: Check if they're truly factual claims or general statements
3. **Section Analysis**: Use the section breakdown to identify areas needing more citations
4. **Combine Metrics**: Use alongside Citation Accuracy for complete validation
5. **Iterative Improvement**: Update agent prompts based on common gaps

## Future Enhancements

- Support for author-year citation format
- More sophisticated claim detection using NLP
- Claim classification by type (statistical, methodological, clinical)
- Integration with Evidence Match Quality for end-to-end verification
