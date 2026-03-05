# Verification Metrics - Module Structure

This directory contains verification metrics for assessing the quality and reliability of generated literature survey reports.

## Structure

```
verification/
├── __init__.py                     # Main module exports
├── base.py                         # Base classes (VerificationMetric, VerificationResult)
├── report_parser.py                # Report parsing utilities
├── README.md                       # Main documentation
│
├── citation_accuracy/              # Citation Accuracy Metric
│   ├── __init__.py
│   ├── metric.py                   # CitationAccuracyMetric implementation
│   ├── trusted_domains.py          # Configuration of trusted sources
│   ├── README.md                   # Metric documentation
│   └── example_output.json         # Sample output
│
├── claim_support/                  # Claim Support Rate Metric
│   ├── __init__.py
│   ├── metric.py                   # ClaimSupportMetric implementation
│   ├── README.md                   # Metric documentation
│   └── example_output.json         # Sample output
│
├── evidence_match/                 # Evidence Match Quality Metric
│   ├── __init__.py
│   ├── metric.py                   # EvidenceMatchMetric implementation
│   ├── README.md                   # Metric documentation
│   └── example_output.json         # Sample output
│
└── hallucination_detection/        # (Future) Hallucination Detection Metric
    ├── __init__.py
    ├── metric.py
    └── example_output.json
```

## Current Metrics

### ✅ Citation Accuracy (Implemented)

**Location:** `citation_accuracy/`

Validates citations by checking:

- URL format and accessibility
- Source credibility (trusted domains)
- Duplicate detection
- Suspicious pattern identification

**Import:**

```python
from app.verification import CitationAccuracyMetric
```

**Usage:**

```python
metric = CitationAccuracyMetric()
result = await metric.calculate("path/to/report.md")
```

### ✅ Claim Support Rate (Implemented)

**Location:** `claim_support/`

Measures the percentage of factual claims that have inline citation markers.

Analyzes:

- Factual claim extraction
- Inline citation detection [1], [2], [3]
- Support rate calculation
- Citation pattern analysis

**Import:**

```python
from app.verification import ClaimSupportMetric
```

**Usage:**

```python
metric = ClaimSupportMetric()
result = await metric.calculate("path/to/report.md")
```

### ✅ Evidence Match Quality (Implemented)

**Location:** `evidence_match/`

Verifies whether cited sources actually support the claims made.

Analyzes:

- TF-IDF similarity between claims and source content
- Keyword matching and extraction
- Best matching passage identification
- Composite match scoring

**Import:**

```python
from app.verification import EvidenceMatchMetric
```

**Usage:**

```python
metric = EvidenceMatchMetric()
result = await metric.calculate("path/to/report.md")
```

## Future Metrics

### 🔜 Hallucination Detection

**Location:** `hallucination_detection/` (to be created)

Will identify claims not grounded in any retrieved document.

## Adding a New Metric

1. **Create subdirectory:**

   ```bash
   mkdir app/verification/my_metric
   ```

2. **Create `metric.py`:**

   ```python
   from app.verification.base import VerificationMetric, VerificationResult

   class MyMetric(VerificationMetric):
       def __init__(self):
           super().__init__("My Metric Name")

       async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
           # Implementation
           pass
   ```

3. **Create `__init__.py`:**

   ```python
   from app.verification.my_metric.metric import MyMetric
   __all__ = ['MyMetric']
   ```

4. **Update main `__init__.py`:**

   ```python
   from app.verification.my_metric import MyMetric
   ```

5. **Add to runner:**
   ```python
   # In run_verification.py
   self.metrics = [
       CitationAccuracyMetric(),
       MyMetric(),  # Add here
   ]
   ```

## Design Principles

- **Modularity**: Each metric is self-contained in its own directory
- **Consistency**: All metrics extend `VerificationMetric` base class
- **Async-first**: All metrics use async/await for I/O operations
- **Comprehensive output**: Return detailed `VerificationResult` objects
- **Configurability**: Support kwargs for customization

## Running Metrics

See main [README.md](README.md) for usage instructions.
