"""Fact checking module for video scripts and narrations."""

from .checker import FactChecker, FactCheckError, run_fact_check
from .models import (
    FactCheckIssue,
    FactCheckReport,
    FactCheckSummary,
    IssueCategory,
    IssueSeverity,
)

__all__ = [
    "FactChecker",
    "FactCheckError",
    "run_fact_check",
    "FactCheckIssue",
    "FactCheckReport",
    "FactCheckSummary",
    "IssueCategory",
    "IssueSeverity",
]
