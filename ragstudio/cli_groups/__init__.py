"""CLI command groups: one file per group, each exposing `register(groups)`."""
from __future__ import annotations

from . import (
    compare_cmd,
    config_cmd,
    corpus_cmd,
    db_cmd,
    evaluate_cmd,
    experiments_cmd,
    index_cmd,
    questions_cmd,
    reference_cmd,
    reports_cmd,
    techniques_cmd,
)

GROUPS = (db_cmd, config_cmd, corpus_cmd, index_cmd, techniques_cmd, questions_cmd, experiments_cmd, evaluate_cmd,
          compare_cmd, reports_cmd, reference_cmd)
