"""What-if counterfactual analysis (Phase 12)."""

from sqlalchemy.orm import Session

from tools.counterfactual_analysis import CounterfactualAnalysis


class WhatIfService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._tool = CounterfactualAnalysis()

    def analyze(self, investigation_id: int, parameters: dict) -> dict:
        raise NotImplementedError("WhatIfService will be implemented in Phase 12.")
