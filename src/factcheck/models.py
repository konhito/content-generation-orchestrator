"""Data models for fact checking."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueSeverity(Enum):
    """Severity level of a fact check issue."""

    CRITICAL = "critical"  # Factually incorrect, must fix
    HIGH = "high"  # Misleading or significantly inaccurate
    MEDIUM = "medium"  # Minor inaccuracy or needs clarification
    LOW = "low"  # Suggestion for improvement, not an error
    INFO = "info"  # General observation or note


class IssueCategory(Enum):
    """Category of a fact check issue."""

    FACTUAL_ERROR = "factual_error"  # Incorrect fact
    OUTDATED_INFO = "outdated_info"  # Information that's no longer current
    MISSING_CONTEXT = "missing_context"  # Important context omitted
    OVERSIMPLIFICATION = "oversimplification"  # Concept oversimplified to the point of inaccuracy
    MISLEADING = "misleading"  # Technically true but misleading
    UNSUPPORTED_CLAIM = "unsupported_claim"  # Claim not backed by source material
    TERMINOLOGY = "terminology"  # Incorrect or imprecise terminology
    ATTRIBUTION = "attribution"  # Missing or incorrect attribution
    NUMERICAL = "numerical"  # Incorrect numbers, statistics, or calculations
    LOGICAL = "logical"  # Logical fallacy or inconsistency
    IMPROVEMENT = "improvement"  # General suggestion for improvement


@dataclass
class FactCheckIssue:
    """A single fact check issue found in the content."""

    id: str
    severity: IssueSeverity
    category: IssueCategory
    location: str  # Where in the script/narration (scene_id or section)
    original_text: str  # The problematic text
    issue_description: str  # What's wrong
    correction: str  # Suggested correction
    source_reference: str  # Reference to source material or web source
    confidence: float  # How confident the checker is (0-1)
    verified_via_web: bool = False  # Whether web search was used to verify

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "location": self.location,
            "original_text": self.original_text,
            "issue_description": self.issue_description,
            "correction": self.correction,
            "source_reference": self.source_reference,
            "confidence": self.confidence,
            "verified_via_web": self.verified_via_web,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FactCheckIssue":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            severity=IssueSeverity(data["severity"]),
            category=IssueCategory(data["category"]),
            location=data["location"],
            original_text=data["original_text"],
            issue_description=data["issue_description"],
            correction=data["correction"],
            source_reference=data["source_reference"],
            confidence=data.get("confidence", 0.8),
            verified_via_web=data.get("verified_via_web", False),
        )


@dataclass
class FactCheckSummary:
    """Summary statistics for a fact check report."""

    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    scenes_with_issues: list[str] = field(default_factory=list)
    overall_accuracy_score: float = 1.0  # 0-1, where 1 is perfect
    web_verified_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "scenes_with_issues": self.scenes_with_issues,
            "overall_accuracy_score": self.overall_accuracy_score,
            "web_verified_count": self.web_verified_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FactCheckSummary":
        """Create from dictionary."""
        return cls(
            total_issues=data.get("total_issues", 0),
            critical_count=data.get("critical_count", 0),
            high_count=data.get("high_count", 0),
            medium_count=data.get("medium_count", 0),
            low_count=data.get("low_count", 0),
            info_count=data.get("info_count", 0),
            scenes_with_issues=data.get("scenes_with_issues", []),
            overall_accuracy_score=data.get("overall_accuracy_score", 1.0),
            web_verified_count=data.get("web_verified_count", 0),
        )


@dataclass
class FactCheckReport:
    """Complete fact check report for a project."""

    project_id: str
    script_title: str
    issues: list[FactCheckIssue] = field(default_factory=list)
    summary: FactCheckSummary = field(default_factory=FactCheckSummary)
    source_documents: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_analysis: str = ""  # Full LLM analysis text

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "script_title": self.script_title,
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": self.summary.to_dict(),
            "source_documents": self.source_documents,
            "recommendations": self.recommendations,
            "raw_analysis": self.raw_analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FactCheckReport":
        """Create from dictionary."""
        issues = [FactCheckIssue.from_dict(i) for i in data.get("issues", [])]
        summary = FactCheckSummary.from_dict(data.get("summary", {}))
        return cls(
            project_id=data["project_id"],
            script_title=data.get("script_title", ""),
            issues=issues,
            summary=summary,
            source_documents=data.get("source_documents", []),
            recommendations=data.get("recommendations", []),
            raw_analysis=data.get("raw_analysis", ""),
        )

    def get_issues_by_severity(self, severity: IssueSeverity) -> list[FactCheckIssue]:
        """Get all issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]

    def get_issues_by_category(self, category: IssueCategory) -> list[FactCheckIssue]:
        """Get all issues of a specific category."""
        return [i for i in self.issues if i.category == category]

    def get_issues_for_scene(self, scene_id: str) -> list[FactCheckIssue]:
        """Get all issues for a specific scene."""
        return [i for i in self.issues if i.location == scene_id]

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return self.summary.critical_count > 0

    def is_accurate(self, threshold: float = 0.8) -> bool:
        """Check if the script meets accuracy threshold."""
        return self.summary.overall_accuracy_score >= threshold
