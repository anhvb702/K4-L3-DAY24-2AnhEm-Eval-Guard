from __future__ import annotations

"""Phase A: RAGAS Production Evaluation — 50q, 3 distributions, cluster analysis."""

import json
import math
import os
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH, ANSWERS_PATH, ARTIFACTS_DIR
from src.experiment_support import write_json

Distribution = str  # "factual" | "multi_hop" | "adversarial"

DIAGNOSTIC_TREE = {
    "faithfulness":      ("LLM hallucinating", "Tighten system prompt, lower temperature"),
    "context_recall":    ("Missing relevant chunks", "Improve chunking or add BM25"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
    "answer_relevancy":  ("Answer doesn't match question", "Improve prompt template"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (self.faithfulness + self.answer_relevancy +
                self.context_precision + self.context_recall) / 4

    @property
    def worst_metric(self) -> str:
        scores = {
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
        }
        return min(scores, key=scores.get)


# ─── Đã implement sẵn ────────────────────────────────────────────────────────

@dataclass
class RagasEvaluation:
    """Task 2 output: measured rows plus model identifiers reported by m4."""
    results: list[RagasResult]
    evaluator_models: list[str]

def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    """Load 50q test set với 3 distributions."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    """Load pre-generated answers từ setup_answers.py."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json không tìm thấy tại {path}\n"
            "→ Chạy trước: python scripts/setup_answers.py --live"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict]) -> dict:
    """Provided exporter: preserve the student-produced Task 3 rows verbatim."""
    per_dist: dict[str, dict] = {}
    for dist in ["factual", "multi_hop", "adversarial"]:
        subset = [r for r in results if r.distribution == dist]
        if subset:
            per_dist[dist] = {
                "count": len(subset),
                "faithfulness":      sum(r.faithfulness for r in subset) / len(subset),
                "answer_relevancy":  sum(r.answer_relevancy for r in subset) / len(subset),
                "context_precision": sum(r.context_precision for r in subset) / len(subset),
                "context_recall":    sum(r.context_recall for r in subset) / len(subset),
                "avg_score":         sum(r.avg_score for r in subset) / len(subset),
            }

    report = {
        "total_questions": len(results),
        "per_question": [asdict(r) for r in results],
        "per_distribution": per_dist,
        "failure_clusters": clusters,
        "bottom_10": bottom,
    }
    return report


def save_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict],
                        path: str = os.path.join(ARTIFACTS_DIR, "ragas_50q.json")) -> None:
    write_json(path, build_phase_a_report(results, clusters, bottom))



# ─── Tasks 1-4: Sinh viên implement ──────────────────────────────────────────

def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    """Task 1: Nhóm 50 câu hỏi theo 3 distributions.

    Returns:
        {"factual": [...], "multi_hop": [...], "adversarial": [...]}
    """
    groups = {"factual": [], "multi_hop": [], "adversarial": []}
    for item in test_set:
        groups[item["distribution"]].append(item)
    return groups


def run_ragas_50q(answers: list[dict]) -> RagasEvaluation:
    """Evaluate saved answers without changing their source order or provenance."""
    from src.m4_eval import evaluate_ragas
    from src.experiment_support import model_ids

    if not answers:
        raise ValueError("Cannot evaluate an empty answers list")
    raw = evaluate_ragas(
        [a["question"] for a in answers], [a["answer"] for a in answers],
        [a["contexts"] for a in answers], [a["ground_truth"] for a in answers],
    )
    rows = raw.get("per_question", [])
    if len(rows) != len(answers):
        raise ValueError("Evaluator must return one metric row per answer")
    models = raw.get("metadata", {}).get("evaluator_models")
    if not model_ids(models, "evaluator models"):
        raise ValueError("Missing actual evaluator model IDs from m4")
    results = []
    for answer, row in zip(answers, rows):
        scores = {}
        for metric in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
            value = row[metric] if isinstance(row, dict) else getattr(row, metric)
            if isinstance(value, bool):
                raise ValueError(f"Question {answer['id']}: invalid {metric}")
            value = float(value)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"Question {answer['id']}: invalid {metric}")
            scores[metric] = value
        results.append(RagasResult(
            question_id=answer["id"], distribution=answer["distribution"],
            question=answer["question"], answer=answer["answer"],
            contexts=answer["contexts"], ground_truth=answer["ground_truth"], **scores,
        ))
    return RagasEvaluation(results, models)


def bottom_10(results: list[RagasResult]) -> list[dict]:
    """Rank the weakest rows; metric-based diagnoses are hypotheses to inspect."""
    output = []
    for rank, result in enumerate(sorted(results, key=lambda r: r.avg_score)[:10], 1):
        diagnosis, fix = DIAGNOSTIC_TREE[result.worst_metric]
        output.append({
            "rank": rank, "question_id": result.question_id,
            "distribution": result.distribution, "question": result.question,
            "avg_score": result.avg_score, "worst_metric": result.worst_metric,
            "diagnosis": (f"Giả thuyết cần đối chiếu answer/contexts/reference: {diagnosis}; "
                          f"{result.worst_metric}={getattr(result, result.worst_metric):.4f}."),
            "suggested_fix": f"{fix}; kiểm tra bằng chứng câu {result.question_id} trước khi sửa và đánh giá lại.",
        })
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    """Count all rows by worst metric; select weakest distribution by mean."""
    if not results:
        raise ValueError("Cannot analyze empty results")
    groups = {d: [] for d in ("factual", "multi_hop", "adversarial")}
    matrix = {m: dict.fromkeys(groups, 0) for m in
              ("faithfulness", "answer_relevancy", "context_precision", "context_recall")}
    for result in results:
        matrix[result.worst_metric][result.distribution] += 1
        groups[result.distribution].append(result.avg_score)
    means = {d: sum(values) / len(values) for d, values in groups.items() if values}
    weakest = min(means, key=means.get)
    metric = max(matrix, key=lambda m: sum(matrix[m].values()))
    return {
        "matrix": matrix, "distribution_avg_scores": means,
        "dominant_failure_distribution": weakest, "dominant_failure_metric": metric,
        "insight": (f"{weakest} có mean thấp nhất ({means[weakest]:.4f}); {metric} là metric "
                    f"thấp nhất của {sum(matrix[metric].values())}/{len(results)} câu. "
                    "Matrix đếm mọi câu, không phải số failures; cần đọc nguồn để xác định nguyên nhân."),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "a", *sys.argv[1:]]))
