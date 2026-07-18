"""Run the system evaluation suite and write a final report.

Usage:
    cd backend && PYTHONPATH=. python -m scripts.run_evaluation
"""

from __future__ import annotations
from database.session import SessionLocal, init_db
from evals.system import EVAL_OUTPUT_DIR, evaluate_system, persist_evaluation_result


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_system(db)
        json_path, md_path = persist_evaluation_result(result, EVAL_OUTPUT_DIR)
        print(md_path.read_text(encoding="utf-8"))
        print()
        print(f"Saved evaluation JSON: {json_path}")
        print(f"Saved evaluation markdown: {md_path}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
