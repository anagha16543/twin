"""
AI-NBA Readiness System — Backend
app/business_rules/readiness_rules.py

Shared utilities for the NBA deterministic evaluation framework.

Design contract
---------------
* All rule functions receive a context dict containing structured backend data.
* All rule functions return an EvaluationResult.
* status is always set by deterministic Python logic — never by an LLM.
* Missing data yields WARNING (not PASS) unless applicability explicitly
  established as NOT_APPLICABLE.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


import enum


# ---------------------------------------------------------------------------
# RequirementStatus re-exported here for convenience in rule modules
# ---------------------------------------------------------------------------

class RequirementStatus(str, enum.Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_RULE_CLARIFICATION = "NEEDS_RULE_CLARIFICATION"


# ---------------------------------------------------------------------------
# EvaluationResult — value object returned by every rule function
# ---------------------------------------------------------------------------

@dataclass
class EvaluationResult:
    """
    Immutable result of a deterministic rule evaluation.

    Attributes
    ----------
    status               : One of RequirementStatus string values.
    score_attained       : Numeric score earned (0 <= score <= max_score).
    max_score            : Maximum possible score for this requirement.
    deterministic_metrics: Dict of all calculated values used for the decision.
    limitations          : List of reasons data was incomplete or ambiguous.
    """
    status: str
    score_attained: float
    max_score: float
    deterministic_metrics: dict = field(default_factory=dict)
    limitations: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper: produce a WARNING when required context data is missing
# ---------------------------------------------------------------------------

def _missing_data_warning(
    rule: str,
    missing: List[str],
    max_score: float = 0.0,
) -> EvaluationResult:
    """Return a WARNING result when required context keys are absent."""
    return EvaluationResult(
        status=RequirementStatus.WARNING,
        score_attained=0.0,
        max_score=max_score,
        deterministic_metrics={},
        limitations=[
            f"Rule '{rule}' could not evaluate: missing context keys: {missing}. "
            "Supply the required data or mark the requirement as NOT_APPLICABLE."
        ],
    )


def _needs_clarification(
    rule: str,
    reason: str,
    max_score: float = 0.0,
    metrics: dict = None,
) -> EvaluationResult:
    """Return NEEDS_RULE_CLARIFICATION when boundary/policy is ambiguous."""
    return EvaluationResult(
        status=RequirementStatus.NEEDS_RULE_CLARIFICATION,
        score_attained=0.0,
        max_score=max_score,
        deterministic_metrics=metrics or {},
        limitations=[
            f"Rule '{rule}' requires institutional clarification: {reason}"
        ],
    )


# ---------------------------------------------------------------------------
# Rule Registry — global mapping of rule_key -> callable
# ---------------------------------------------------------------------------

_RULE_REGISTRY: Dict[str, Callable[[dict], EvaluationResult]] = {}


def register_rule(key: str, fn: Callable[[dict], EvaluationResult]) -> None:
    """Register a deterministic rule function under the given key."""
    _RULE_REGISTRY[key] = fn


def evaluate_requirement(rule_key: str, context: dict) -> EvaluationResult:
    """
    Look up and execute the deterministic rule for the given key.

    If the key is not registered, returns WARNING with an explanatory message
    rather than raising or returning PASS.  PASS must never be the default.
    """
    fn = _RULE_REGISTRY.get(rule_key)
    if fn is None:
        return EvaluationResult(
            status=RequirementStatus.WARNING,
            score_attained=0.0,
            max_score=0.0,
            deterministic_metrics={},
            limitations=[
                f"No evaluation rule is registered for key '{rule_key}'. "
                "Register the rule in the appropriate criterion module."
            ],
        )
    return fn(context)


def load_all_rules() -> None:
    """
    Import every criterion module to trigger rule registration.
    Call this once at application startup or before the first evaluation.
    """
    from app.business_rules import (  # noqa: F401
        criterion3_rules,
        criterion4_rules,
        criterion5_rules,
        criterion6_rules,
    )
    # Register all rules from each criterion module
    for module, registry_attr in [
        (criterion3_rules, "CRITERION3_RULES"),
        (criterion4_rules, "CRITERION4_RULES"),
        (criterion5_rules, "CRITERION5_RULES"),
        (criterion6_rules, "CRITERION6_RULES"),
    ]:
        registry = getattr(module, registry_attr, {})
        for key, fn in registry.items():
            register_rule(key, fn)
