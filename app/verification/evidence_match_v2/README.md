# Evidence Match Quality V2 - Embeddings-Based

## Overview

This is a simplified, more accurate version of Evidence Match Quality that uses **OpenAI embeddings** for semantic similarity instead of TF-IDF and keyword matching.

## Why Embeddings?

**Advantages over TF-IDF:**

- ✅ Better semantic understanding (understands synonyms, paraphrasing)
- ✅ Simpler implementation (no complex multi-factor scoring)
- ✅ More accurate matching (captures meaning, not just words)
- ✅ Handles technical jargon better (medical terminology)

**Trade-offs:**

- ⚠️ Requires OpenAI API key (costs ~$0.0001 per claim)
- ⚠️ Slightly slower (API calls vs local computation)
- ⚠️ Requires internet connection

## Methodology

### Simple 3-Step Process

1. **Fetch Source Content**
   - Extract clean text from cited URL
   - Use browser-like headers to avoid blocking

2. **Generate Embeddings**
   - Use `text-embedding-3-small` model
   - Embed claim text (without citation markers)
   - Embed source text (first 30k chars ~8k tokens)

3. **Calculate Similarity**
   - Compute cosine similarity between embeddings
   - Score range: 0.0 to 1.0

### Match Quality Classification

- **HIGH** (≥0.8): Strong semantic alignment - source clearly supports claim
- **MEDIUM** (0.6-0.79): Moderate alignment - source discusses related topics
- **LOW** (<0.6): Weak alignment - source doesn't support claim well

## Usage

```python
from app.verification.evidence_match_v2 import EvidenceMatchV2Metric
import os

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "sk-..."

# Initialize metric
metric = EvidenceMatchV2Metric()

# Or pass API key directly
metric = EvidenceMatchV2Metric(openai_api_key="sk-...")

# Calculate for a report
result = await metric.calculate("workspace/my_report.md")

# Access results
print(f"Score: {result.score:.2%}")
print(f"High matches: {result.details['match_distribution']['HIGH']}")

# Examine specific claims
for claim_result in result.details['claim_verification_details']:
    if claim_result['match_quality'] == 'HIGH':
        print(f"✅ {claim_result['claim'][:80]}...")
        print(f"   Similarity: {claim_result['similarity_score']:.3f}")
```

## Output Format

```json
{
  "metric_name": "evidence_match_quality_v2",
  "score": 0.82,
  "passed_checks": 15,
  "total_checks": 18,
  "details": {
    "summary": "15/16 claims have high semantic match (82.3% avg)",
    "total_claims_analyzed": 18,
    "verifiable_claims": 16,
    "unverifiable_claims": 2,
    "average_similarity_score": 82.3,
    "match_distribution": {
      "HIGH": 15,
      "MEDIUM": 1,
      "LOW": 0,
      "UNVERIFIABLE": 2
    },
    "claim_verification_details": [
      {
        "claim": "Semaglutide reduced HbA1c by 1.5% in STEP trial [1].",
        "citations": ["1"],
        "urls": ["https://nejm.org/..."],
        "similarity_score": 0.876,
        "match_quality": "HIGH",
        "best_passage": "At week 68, mean HbA1c reduction was 1.5%...",
        "source_url": "https://nejm.org/..."
      }
    ]
  }
}
```

## API Costs

Using `text-embedding-3-small`:

- **Cost**: $0.00002 per 1,000 tokens
- **Average claim**: ~50 tokens = $0.000001
- **Average source**: ~8,000 tokens = $0.00016
- **Per claim**: ~$0.0002 total
- **100 claims**: ~$0.02

Very affordable for verification purposes.

## Comparison with V1

| Feature                    | V1 (TF-IDF)      | V2 (Embeddings) |
| -------------------------- | ---------------- | --------------- |
| **Accuracy**               | Good             | Excellent       |
| **Semantic Understanding** | Limited          | Strong          |
| **Speed**                  | Fast (local)     | Moderate (API)  |
| **Cost**                   | Free             | ~$0.0002/claim  |
| **Dependencies**           | scikit-learn     | OpenAI API      |
| **Complexity**             | High (3 factors) | Low (1 score)   |
| **Offline Support**        | Yes              | No              |

## Configuration

### Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional (if using Azure OpenAI)
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."
```

### Integration with Verification Runner

```python
# In run_verification.py
from app.verification.evidence_match_v2 import EvidenceMatchV2Metric

class VerificationRunner:
    def __init__(self):
        self.metrics = [
            CitationAccuracyMetric(),
            ClaimSupportMetric(),
            EvidenceMatchV2Metric(),  # Use V2 instead of V1
        ]
```

## Limitations

1. **API Dependency**: Requires valid OpenAI API key and internet connection
2. **Rate Limits**: OpenAI has rate limits (typically 3,000 RPM for embeddings)
3. **Paywalled Content**: Still can't access sources behind paywalls (same as V1)
4. **Context Window**: Limited to ~8k tokens (~30k chars) of source text

## Best Practices

1. **Batch Processing**: If verifying many reports, consider batching to manage costs
2. **Cache Results**: Store verification results to avoid re-embedding same content
3. **Monitor Costs**: Track API usage in OpenAI dashboard
4. **Fallback**: Keep V1 available as offline fallback option

## Future Enhancements

- [ ] Support for local embedding models (sentence-transformers)
- [ ] Caching layer for embeddings
- [ ] Batch embedding requests for efficiency
- [ ] Azure OpenAI support
- [ ] Passage-level chunking for better accuracy
