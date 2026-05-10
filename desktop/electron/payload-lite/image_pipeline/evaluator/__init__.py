"""
image_pipeline.evaluator — 8-dimension evaluation framework.

Modules:
    scorer           — LLM-as-judge scoring engine (Qwen2.5-VL / GPT-4o)
    correction       — Post-evaluation auto-correction loop
    experiment_log   — Structured benchmark recording + A/B comparison
    benchmark_runner — CLI/programmatic benchmark executor
"""

from .scorer import Scorer
from .correction import CorrectionLoop, CorrectionResult
from .experiment_log import ExperimentLog, RunSummary, CaseRecord, CategorySummary

__all__ = [
    "Scorer",
    "CorrectionLoop",
    "CorrectionResult",
    "ExperimentLog",
    "RunSummary",
    "CaseRecord",
    "CategorySummary",
]
