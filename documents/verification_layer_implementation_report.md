# Verification Layer Implementation Report

**Date**: March 3, 2026
**Project**: OpenManus MedScholar Agent

---

## Work Timeline

### Phase 1: Research and Design

- Researched scoring methodologies for AI-generated medical reports
- Identified 4 verification metrics: Citation Accuracy, Claim Support Rate, Evidence Match Quality, and Hallucination Rate (planned)

### Phase 2: MedScholar Agent Improvements

- Implemented inline citation system [1][2] within claim text
- Enhanced markdown formatting and reference structure for readability

### Phase 3: Metric Implementation

- Developed dual evidence matching approaches: V1 (TF-IDF, offline) and V2 (embeddings, high-accuracy)
- Tested on 6 medical reports with JSON output format

---

## Implementation Details

### MedScholar Agent Enhancements

#### System Prompt Updates

- Updated system prompts to enforce better formatting standards
- Added structured section requirements for literature surveys
- Implemented markdown formatting guidelines for consistency

#### Report Output Improvements

- **Markdown Format**: Reports now generated as detailed .md files for user readability
- **Inline Citations**: Added inline citation markers [1][2] within claim text (previously absent)
- **References Section**: Improved reference formatting with:
  - Numbered citations [1], [2], etc.
  - Full URLs for source accessibility
  - Consistent formatting across all reports

#### Example Format

```markdown
The gut-brain axis is a complex communication network [1][2].

## References

[1] Full citation with URL
[2] Full citation with URL
```

---

### Implementing the Agent Scoring Metrics for Verification Layer

#### 1. Citation Accuracy (Enhanced)

- **Purpose**: Validates citation quality and source credibility
- **Scoring**: 4-factor composite (40/30/20/10 weighting)
  - URL accessibility (HTTP status checks)
  - Source credibility (trusted domains: .gov, .edu, PubMed, Nature, etc.)
  - Citation uniqueness (deduplication)
  - Non-suspicious patterns
- **Enhancement**: Added browser-like headers to bypass 403 paywalls
- **Output**: Per-citation analysis with HTTP status, credibility scores

**Example Output**:

```json
{
  "score": 0.762,
  "total_citations": 5,
  "accessible_urls": 3,
  "trusted_sources": 5,
  "citation_details": [
    {
      "index": 2,
      "url": "https://link.springer.com/article/...",
      "is_accessible": true,
      "http_status": 200,
      "is_trusted_source": true,
      "credibility_score": 0.9,
      "page_title": "The gut–brain axis in depression..."
    }
  ]
}
```

#### 2. Claim Support Rate

- **Purpose**: Measures what percentage of claims have inline citations
- **Method**: Parses report sections, identifies claims, checks for citation markers [1][2]
- **Output**: Section-by-section breakdown, supported vs unsupported claims
- **Enhancement**: Removed claim truncation to preserve full context

**Example Output**:

```json
{
  "score": 0.636,
  "total_claims": 11,
  "supported_claims": 7,
  "support_rate_percentage": 63.64,
  "supported_examples": [
    {
      "claim": "Semaglutide significantly reduces body weight [3].",
      "section": "Key Findings",
      "citations": ["[3]"],
      "citation_count": 1
    }
  ],
  "unsupported_examples": [
    {
      "claim": "Additional studies could explore comparative effectiveness.",
      "section": "Key Findings",
      "reason": "No inline citation marker found"
    }
  ]
}
```

#### 3. Evidence Match Quality V1 (TF-IDF)

- **Purpose**: Offline semantic matching between claims and cited sources
- **Method**: Multi-factor composite scoring
  - TF-IDF vectorization (50% weight)
  - Keyword matching (30% weight)
  - Best passage similarity (20% weight)
- **Match Levels**: HIGH (≥60%), MEDIUM (40-59%), LOW (<40%)
- **Advantage**: No API costs, runs completely offline
- **Limitation**: Less semantically accurate than embeddings

**Example Output**:

```json
{
  "score": 0.402,
  "verifiable_claims": 4,
  "average_match_score": 40.25,
  "claim_verification_details": [
    {
      "claim": "Wegovy is administered at higher doses than Ozempic [2].",
      "composite_score": 0.491,
      "match_quality": "MEDIUM",
      "tfidf_similarity": 0.306,
      "keyword_match_rate": 0.842,
      "best_passage": "Because Wegovy is administered at higher doses...",
      "found_keywords": ["weight", "higher", "doses", "side"],
      "missing_keywords": ["leading", "contains"]
    }
  ]
}
```

#### 4. Evidence Match Quality V2 (Embeddings) (better way)

- **Purpose**: High-accuracy semantic matching using AI embeddings
- **Method**: OpenAI text-embedding-3-small for cosine similarity
- **Features**:
  - Simple single-score approach (vs V1's multi-factor)
  - Embedding-based best passage extraction (finds actual matching text)
  - Match Levels: HIGH (≥80%), MEDIUM (60-79%), LOW (<60%)
- **Limitation**: Uses an external llm call to run (OpenAI APIs)
- **Advantage**: Significantly more accurate semantic understanding

**Example Output**:

```json
{
  "score": 0.629,
  "verifiable_claims": 6,
  "average_similarity_score": 62.9,
  "claim_verification_details": [
    {
      "claim": "Microbial metabolites modulate brain function [2][5].",
      "similarity_score": 0.629,
      "match_quality": "MEDIUM",
      "best_passage": "The gut microbiota can modulate gut-brain communication through the production of neuroactive metabolites...",
      "source_url": "https://www.nature.com/articles/..."
    }
  ]
}
```

---

## Results and Discussion

### Overview

Tested on 6 healthcare literature surveys analyzing **28 citations** and **67 factual claims** across mental health, metabolic disorders, COVID-19, cardiovascular disease, and gene therapy domains.

**Quality Scores**: Range 37.2%-55.9% (avg 49.3%) | Best: Gut-brain axis (55.9%) | Lowest: Vitamin D (37.2%)


### Key Findings

#### 1. Citation Accessibility Crisis

- **Citation accessibility ranges 25-100%** across reports (avg ~57%)
- **Worst performers**: Vitamin D (25%), Long COVID (40%)
- **Best performer**: Statin therapy (100% accessible)
- **40-75% of citations blocked** by paywalls (PubMed Central, Lancet, Nature)
- **Result**: 30-50% claims marked "UNVERIFIABLE" due to inaccessible sources, not quality issues

#### 2. Claim Support Patterns

- **Claim support rate: 30.77%-63.64%** (avg ~49.8%)
- **4-9 unsupported claims per report** (out of 11-15 total claims)
- **Pattern identified**: "Key Findings" sections well-cited (63-100%), "Research Gaps" sections lack citations (0%)
- Agent systematically undercites general statements and future directions

#### 3. Evidence Match Quality

- **V2 outperforms V1 by 69-228%** on accessible sources
- **V1 scores**: 14.72%-33.59% | **V2 scores**: 43.02%-56.87%
- **Improvement examples**: Vitamin D (+228%), Statin therapy (+107%), Gut-brain (+69%)
- **Zero claims achieved HIGH match (≥80%)** across all reports—indicates agent paraphrasing/synthesis behavior
- **V2 advantages**: Semantic understanding, handles medical terminology and paraphrasing better than keyword-based V1


### Successes

- **Multi-dimensional scoring** identifies weak citations, unsupported claims, and semantic alignment issues
- **V2 embeddings** achieve 69-228% better accuracy than keyword-based V1
- **Section-level analysis** reveals agent patterns (strong on findings, weak on gaps/directions)
- **Best passage extraction** returns actual matching text via embedding similarity


### Limitations

- **Paywalls**: 40-75% citations inaccessible (PubMed Central, Lancet, Nature) despite browser headers
- **Language barriers**: Chinese sources (statin report) cause 20.77% V1 match, 0/5 trusted sources
- **No HIGH matches**: Zero claims ≥80% similarity—thresholds may be too strict for synthesized content
- **V1 keyword weakness**: Misses synonyms ("gut microbiome" vs "intestinal microbiota"), poor rephrasing detection
- **Cost/API dependency** (V2): ~$0.0015 per report, requires connectivity


### Statistical Summary

- **Average Scores**: Citation Accuracy 68.2% | Claim Support 49.8% | Evidence V1 27.4% | Evidence V2 49.3%
- **Correlations**: Citation accessibility strongly predicts evidence match (r≈0.82) | V2 consistently 16-33 points higher than V1
- **Verifiability**: Only 68% of claims fully verifiable due to paywalls

---

## Future Work

### Priority Improvements

**1. Rigorous Testing and Comparative Evaluation** (**MAX PRIORITY**)

- **Extensive prompt variation testing**: Test same agent with diverse prompts to measure verification consistency
- **Cross-agent benchmarking**: Compare verification results across multiple AI systems (GPT-4, Perplexity, Elicit, Consensus)
- **Large-scale validation**: Run verification on 50+ reports to establish statistical significance
- **Performance baseline establishment**: Create comparative datasets showing verification improvement over time
- **Metric sensitivity analysis**: Test how prompt changes affect Citation Accuracy, Claim Support, and Evidence Match scores
- **Expected outcome**: Quantify verification system reliability and identify best practices for consistent high-quality outputs

**2. Constrain Agent to Trusted Domains**

- Implement domain whitelist prioritizing open-access sources (.gov, PubMed Central, PLOS, Frontiers, BMC)
- Configure search to prioritize "free full text" filtering
- Expected impact: increase citation accessibility from 40-60% → 85-95%, reduce unverifiable claims to <10%

**3. Implement Hallucination Rate Metric**

- Cross-metric synthesis: `Hallucination Score = 1 - (CA × 0.3 + CSR × 0.3 + EMQ × 0.4)`
- Fact-checking layer for numerical claims (percentages, dates, statistics)
- Consistency checking across sections to detect internal contradictions

**4. Enhance Evidence Match Quality**

- Calibrate thresholds using ground truth dataset (currently no claims achieve HIGH ≥80%)
- Implement multi-passage matching and contextual expansion (±1 surrounding sentences)
- Add claim classification to distinguish factual claims from methodology/discussion
- Expected: increase HIGH match rate from 0% → 20-30%

**5. Integrate Verification into Agent Workflow**

- Real-time verification-in-the-loop during report generation
- Quality gates: Citation Accuracy ≥75%, Claim Support ≥80%, Evidence Match ≥60%
- Agent self-corrects low-scoring claims before finalizing output
- Expected: raise overall quality from 49.3% → 75%+, though generation time may increase 2-3x

**6. Enforce English-Only Research**

- Add language filter (`lang:en`) to search configuration and system prompts
- Implement language detection in verification to flag non-English citations
- Eliminate cross-language verification failures (currently affecting statin report: 20.77% V1 match)
