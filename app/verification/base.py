"""
Base classes for verification metrics
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VerificationResult:
    """
    Result of a verification metric calculation.
    
    Attributes:
        metric_name: Name of the metric
        score: Numerical score (0.0 to 1.0 typically)
        details: Additional details about the verification
        passed_checks: Number of checks that passed
        total_checks: Total number of checks performed
        timestamp: When the verification was performed
        errors: Any errors encountered during verification
    """
    metric_name: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    passed_checks: int = 0
    total_checks: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metric_name": self.metric_name,
            "score": self.score,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "accuracy_percentage": round(self.score * 100, 2),
            "details": self.details,
            "timestamp": self.timestamp,
            "errors": self.errors,
        }


class VerificationMetric(ABC):
    """
    Abstract base class for verification metrics.
    
    Each metric should implement the calculate() method to perform
    its specific verification logic.
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def calculate(self, report_path: str, **kwargs) -> VerificationResult:
        """
        Calculate the metric for a given report.
        
        Args:
            report_path: Path to the report file to verify
            **kwargs: Additional parameters specific to the metric
            
        Returns:
            VerificationResult containing the metric score and details
        """
        pass
    
    def _create_result(
        self,
        score: float,
        passed: int,
        total: int,
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None
    ) -> VerificationResult:
        """Helper method to create a VerificationResult."""
        return VerificationResult(
            metric_name=self.name,
            score=score,
            passed_checks=passed,
            total_checks=total,
            details=details or {},
            errors=errors or [],
        )
