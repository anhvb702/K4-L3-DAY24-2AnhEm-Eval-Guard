from __future__ import annotations

"""Module 4: RAGAS evaluation and failure analysis."""

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, is_dataclass
from importlib.metadata import version
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH

METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
EVALUATOR_LLM_MODEL = "gpt-4o-mini"
EVALUATOR_EMBEDDING_MODEL = "text-embedding-3-small"
GENERATION_MODEL = "gpt-4o-mini"
GENERATION_SYSTEM_PROMPT = (
    "Chỉ trả lời dựa trên context; trả lời mọi phần có bằng chứng và nêu rõ phần "
    "còn thiếu. Chỉ nói không có thông tin khi context không có bằng chứng liên quan. "
    "Nếu nguồn mâu thuẫn, dùng phiên bản/ngày hiệu lực/quy tắc thay thế được ghi rõ; "
    "với câu hỏi lịch sử, dùng phiên bản tương ứng, nếu không xác định được thì nêu mâu thuẫn. "
    "Với phép tính, phân biệt lỗi số học với thiếu quy tắc: nếu context đủ quy tắc, "
    "xác định mức gốc, chu kỳ, số chu kỳ đủ điều kiện và phần cộng/nhân; tính theo "
    "quy tắc đó, tự kiểm tra phép tính và nêu biểu thức ngắn khi hữu ích. "
    "Không tự thêm cách quy đổi, làm tròn, tính trọn kỳ hay tính kỳ lẻ. "
    "Nếu quy tắc cho kỳ lẻ/đơn vị quy đổi còn thiếu, nêu đúng quy tắc cần bổ sung "
    "và mức/kỳ có căn cứ; nói số tiền cho khoảng đó chưa xác định từ nguồn. "
    "Không suy ra rằng chưa đủ một kỳ thì không phát sinh phí."
)


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None
    error: str | None = None


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def input_fingerprint(documents: list[dict], test_set: list[dict], configuration: dict) -> str:
    """Invalidate generated-answer cache if corpus, questions or run settings change."""
    content = json.dumps({"documents": documents, "test_set": test_set,
                          "configuration": configuration}, sort_keys=True,
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def implementation_digest(*paths: str) -> str:
    """Bind generation cache to retrieval, ranking and context assembly code."""
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for relative_path in paths:
        digest.update(relative_path.encode("utf-8"))
        digest.update((root / relative_path).read_bytes())
    return digest.hexdigest()


def evaluator_configuration() -> dict:
    return {
        "llm_model": EVALUATOR_LLM_MODEL,
        "embedding_model": EVALUATOR_EMBEDDING_MODEL,
        "ragas_version": version("ragas"),
        "metrics": list(METRICS),
        "judge_temperature": 0,
        "judge_max_tokens": 1024,
        "timeout": 45,
        "embedding_timeout": 45,
        "max_retries": 1,
        "max_wait": 2,
        "max_workers": 2,
        "raise_exceptions": False,
    }


def evaluation_fingerprint(questions: list[str], answers: list[str],
                           contexts: list[list[str]], ground_truths: list[str]) -> str:
    content = json.dumps({
        "questions": questions, "answers": answers, "contexts": contexts,
        "ground_truths": ground_truths, "evaluator": evaluator_configuration(),
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def collect_inputs(test_set: list[dict], retrieve, cache_path: str,
                   fingerprint: str, client) -> list[dict]:
    """Generate once per question, checkpointing answers and contexts as they arrive."""
    path = Path(cache_path)
    entries = []
    if path.exists():
        with path.open(encoding="utf-8") as file:
            cached = json.load(file)
        if cached.get("fingerprint") == fingerprint:
            for index, entry in enumerate(cached.get("entries", [])):
                if (index >= len(test_set) or entry.get("question") != test_set[index]["question"]
                        or entry.get("ground_truth") != test_set[index]["ground_truth"]
                        or entry.get("generation_status") != "success"):
                    break
                reused = dict(entry)
                reused["historical_timings"] = entry.get(
                    "historical_timings", entry.get("timings", {})
                )
                reused["timings"] = {"retrieval_s": 0.0, "rerank_s": 0.0,
                                     "generation_s": 0.0, "query_total_s": 0.0}
                reused["cache_hit"] = True
                entries.append(reused)
    if entries:
        print(
            f"  Reused {len(entries)} generated answers/contexts from {path}; "
            f"fingerprint={fingerprint}", flush=True,
        )

    for index in range(len(entries), len(test_set)):
        question = test_set[index]["question"]
        started = time.perf_counter()
        contexts, retrieval_timings = retrieve(question)
        retrieval_timings = dict(retrieval_timings)
        context_trace = retrieval_timings.pop("context_trace", [])
        generation_started = time.perf_counter()
        status = "success"
        error = None
        answer = None
        if not client:
            status, error = "fallback", "OPENAI_API_KEY unavailable"
        elif not contexts:
            status, error = "fallback", "No retrieved contexts"
        else:
            try:
                context_str = "\n\n".join(contexts)
                response = client.chat.completions.create(
                    model=GENERATION_MODEL,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                        {"role": "user", "content":
                         f"Context:\n{context_str}\n\nCâu hỏi: {question}"},
                    ],
                )
                answer = response.choices[0].message.content
                if not answer or not answer.strip():
                    raise ValueError("Empty generated answer")
            except Exception as failure:  # noqa: BLE001 - preserve error status and stop paid calls
                status = "fallback"
                error = f"{type(failure).__name__}: {failure}"
        if status != "success":
            answer = contexts[0] if contexts else "Không tìm thấy thông tin."
        entries.append({
            "question": question, "answer": answer, "contexts": contexts,
            "ground_truth": test_set[index]["ground_truth"],
            "context_trace": context_trace, "cache_hit": False,
            "generation_status": status, "generation_error": error,
            "timings": {**retrieval_timings,
                        "generation_s": time.perf_counter() - generation_started,
                        "query_total_s": time.perf_counter() - started},
        })
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump({"fingerprint": fingerprint, "entries": entries}, file,
                      ensure_ascii=False, indent=2, allow_nan=False)
        print(f"  [{index + 1}/{len(test_set)}] {question[:50]}: {status}", flush=True)
        if status != "success":
            break
    return entries


def _failed_result(count: int, error: str) -> dict:
    return {
        **dict.fromkeys(METRICS, None), "per_question": [], "status": "failed",
        "error": error, "num_questions": count, "valid_count": 0,
        "failed_count": count, "metric_counts": dict.fromkeys(METRICS, 0),
        "errors": [],
        "evaluator": evaluator_configuration(),
    }


def _score(value: object) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if math.isfinite(score) and 0 <= score <= 1 else None


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Evaluate four RAGAS 0.1 metrics and expose invalid samples explicitly."""
    if len({len(questions), len(answers), len(contexts), len(ground_truths)}) != 1:
        raise ValueError("questions, answers, contexts and ground_truths must have equal lengths")
    count = len(questions)
    if not count:
        return _failed_result(0, "No evaluation samples")
    for index, context_list in enumerate(contexts):
        if not isinstance(context_list, list) or not context_list or not all(
            isinstance(context, str) and context.strip() for context in context_list
        ):
            raise ValueError(f"contexts[{index}] must be a non-empty list of non-empty strings")
    for name, values in (("questions", questions), ("answers", answers),
                         ("ground_truths", ground_truths)):
        if not all(isinstance(value, str) for value in values):
            raise ValueError(f"{name} must contain strings")

    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
        from ragas.run_config import RunConfig

        dataset = Dataset.from_dict({
            "question": questions, "answer": answers,
            "contexts": contexts, "ground_truth": ground_truths,
        })
        llm = ChatOpenAI(model=EVALUATOR_LLM_MODEL, temperature=0, timeout=45,
                         max_retries=1, max_tokens=1024)
        embeddings = OpenAIEmbeddings(model=EVALUATOR_EMBEDDING_MODEL,
                                      timeout=45, max_retries=1)
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm, embeddings=embeddings,
            run_config=RunConfig(timeout=45, max_retries=1, max_wait=2, max_workers=2),
            raise_exceptions=False,
        )
        frame = result.to_pandas()
        if len(frame) != count:
            raise ValueError(f"RAGAS returned {len(frame)} rows for {count} questions")

        per_question = []
        errors = []
        metric_values = {metric: [] for metric in METRICS}
        for index, (_, row) in enumerate(frame.iterrows()):
            if row.get("question", questions[index]) != questions[index]:
                raise ValueError("RAGAS returned questions out of order")
            scores = {metric: _score(row.get(metric)) for metric in METRICS}
            invalid = [metric for metric, value in scores.items() if value is None]
            if invalid:
                raise ValueError(f"Question {index}: invalid metrics: {', '.join(invalid)}")
            for metric, value in scores.items():
                if value is not None:
                    metric_values[metric].append(value)
            error = f"Invalid or missing metrics: {', '.join(invalid)}" if invalid else None
            if error:
                errors.append({"index": index, "question": questions[index], "error": error})
            per_question.append(EvalResult(
                question=questions[index], answer=answers[index],
                contexts=list(contexts[index]), ground_truth=ground_truths[index],
                **scores, error=error,
            ))

        valid_count = count - len(errors)
        return {
            **{metric: (sum(values) / len(values) if values else None)
               for metric, values in metric_values.items()},
            "per_question": per_question,
            "status": "success" if valid_count == count else ("partial" if valid_count else "failed"),
            "error": None if not errors else f"{len(errors)} questions have invalid metrics",
            "num_questions": count, "valid_count": valid_count,
            "failed_count": len(errors),
            "metric_counts": {metric: len(values) for metric, values in metric_values.items()},
            "errors": errors,
            "evaluator": evaluator_configuration(),
            "metadata": {"evaluator_models": sorted({llm.model_name, embeddings.model})},
        }
    except Exception as error:  # noqa: BLE001 - preserve scaffold's API-error fallback
        print(f"  ⚠️  RAGAS evaluation failed: {type(error).__name__}: {error}", flush=True)
        return _failed_result(count, f"{type(error).__name__}: {error}")


def evaluate_with_cache(questions: list[str], answers: list[str],
                        contexts: list[list[str]], ground_truths: list[str],
                        report_path: str) -> dict:
    """Reuse only a complete successful report for exactly matching evaluation inputs."""
    fingerprint = evaluation_fingerprint(questions, answers, contexts, ground_truths)
    path = Path(report_path)
    if path.exists():
        with path.open(encoding="utf-8") as file:
            prior = json.load(file)
        rows = prior.get("per_question", [])
        count = len(questions)
        matching_rows = len(rows) == count and all(
            row.get("question") == questions[index]
            and row.get("answer") == answers[index]
            and row.get("contexts") == contexts[index]
            and row.get("ground_truth") == ground_truths[index]
            and all(_score(row.get(metric)) is not None for metric in METRICS)
            for index, row in enumerate(rows)
        )
        models = prior.get("metadata", {}).get("evaluator_models")
        if (
            isinstance(models, list) and bool(models)
            and all(isinstance(model, str) and model.strip() for model in models)
            and prior.get("status") == "success"
            and prior.get("evaluation_fingerprint") == fingerprint
            and prior.get("evaluator") == evaluator_configuration()
            and prior.get("num_questions") == prior.get("valid_count") == count
            and prior.get("failed_count") == 0
            and all(prior.get("metric_counts", {}).get(metric) == count for metric in METRICS)
            and all(_score(prior.get("aggregate", {}).get(metric)) is not None for metric in METRICS)
            and matching_rows
        ):
            print(f"  Reused successful RAGAS result from {path}; fingerprint={fingerprint}", flush=True)
            return {
                **{metric: float(prior["aggregate"][metric]) for metric in METRICS},
                "per_question": [EvalResult(**{key: row.get(key) for key in
                                                ("question", "answer", "contexts", "ground_truth",
                                                 *METRICS, "error")}) for row in rows],
                "status": "success", "error": None, "num_questions": count,
                "valid_count": count, "failed_count": 0,
                "metric_counts": dict.fromkeys(METRICS, count), "errors": [],
                "evaluator": evaluator_configuration(),
                "metadata": prior["metadata"],
                "evaluation_fingerprint": fingerprint,
                "evaluation_cache_hit": True,
                "cached_evaluation_s": prior.get("timings", {}).get("evaluation_s"),
            }

    result = evaluate_ragas(questions, answers, contexts, ground_truths)
    result["evaluation_fingerprint"] = fingerprint
    result["evaluation_cache_hit"] = False
    return result


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Rank complete measurements and attach diagnostic hypotheses."""
    if bottom_n <= 0:
        return []
    diagnostic_tree = {
        "faithfulness": ("Answer may contain unsupported claims",
                         "Constrain generation to retrieved evidence and inspect citations"),
        "context_recall": ("Relevant evidence may be missing",
                           "Inspect retrieval and chunk boundaries"),
        "context_precision": ("Retrieved context may include irrelevant chunks",
                              "Inspect ranking, version metadata and reranking"),
        "answer_relevancy": ("Answer may not address the question",
                             "Inspect generation prompt and chosen contexts"),
    }
    complete = []
    for result in eval_results:
        scores = {metric: _score(getattr(result, metric)) for metric in METRICS}
        if any(value is None for value in scores.values()):
            continue
        complete.append((sum(scores.values()) / len(METRICS), result, scores))
    complete.sort(key=lambda item: item[0])

    failures = []
    for average, result, scores in complete[:bottom_n]:
        worst_metric = min(scores, key=scores.get)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        failures.append({
            "question": result.question, "answer": result.answer,
            "expected": result.ground_truth, "ground_truth": result.ground_truth,
            "contexts": list(result.contexts), "worst_metric": worst_metric,
            "score": average, "metric_scores": scores, "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
            "error_tree": f"Output correct? → Context contains evidence? → Retrieval/rerank? → {worst_metric}",
            "diagnosis_status": "hypothesis from metric; verify against answer and contexts",
        })
    return failures


def _json_safe(value):
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save full evidence without replacing a successful report with a failed run."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "aggregate": {metric: results.get(metric) for metric in METRICS},
        "num_questions": results.get("num_questions", len(results.get("per_question", []))),
        "failures": failures, "per_question": results.get("per_question", []),
        **{key: value for key, value in results.items()
           if key not in (*METRICS, "per_question", "num_questions")},
    }
    if destination.exists() and report.get("status") != "success":
        destination = destination.with_name(destination.stem + ".failed.json")

    with destination.open("w", encoding="utf-8") as file:
        json.dump(_json_safe(report), file, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Report saved to {destination}", flush=True)
    return str(destination)


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
