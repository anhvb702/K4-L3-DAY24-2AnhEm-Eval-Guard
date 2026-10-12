"""Source-grounded chunk enrichment. Only context plus original text is indexed."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from config import OPENAI_API_KEY

MODEL = "gpt-4o-mini"
PROMPT_VERSION = "combined-source-v1"
SYSTEM_PROMPT = (
    "Return one compact JSON object with keys summary (one short Vietnamese sentence), "
    "questions (up to 3 short Vietnamese questions), context (one short sentence identifying "
    "the source and topic), metadata (object with topic, entities, category, language). "
    "Use only supplied source facts. If a fact is absent, omit it. Do not invent benefits, "
    "figures, effective dates, replacement rules, or calculations. A newer-looking filename "
    "does not establish that another policy is superseded. Do not copy source identity into metadata."
)
SAFE_META = {"topic", "entities", "category", "language"}
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / ".venv/cache/enrichment"
_last_usage = None


@dataclass
class EnrichedChunk:
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str
    status: str = "fallback"
    reason: str | None = None
    llm_metadata: dict = field(default_factory=dict)


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    return OpenAI(api_key=OPENAI_API_KEY, timeout=25, max_retries=1)


def _validate(value: object) -> dict:
    if not isinstance(value, dict):
        raise TypeError("Enrichment JSON must be an object")
    if not all(key in value for key in ("summary", "questions", "context", "metadata")):
        raise ValueError("Enrichment JSON missing required keys")
    if not isinstance(value["summary"], str) or not isinstance(value["context"], str):
        raise TypeError("summary/context must be strings")
    if (not isinstance(value["questions"], list)
            or not all(isinstance(q, str) for q in value["questions"])):
        raise ValueError("questions must be strings")
    meta = value["metadata"]
    if not isinstance(meta, dict):
        raise TypeError("metadata must be an object")
    if "entities" in meta and (not isinstance(meta["entities"], list)
                               or not all(isinstance(e, str) for e in meta["entities"])):
        raise ValueError("entities must be strings")
    if any(not isinstance(v, str) for k, v in meta.items() if k != "entities"):
        raise ValueError("metadata values must be strings")
    return {
        "summary": value["summary"].strip(),
        "questions": [q.strip() for q in value["questions"][:3] if q.strip()],
        "context": value["context"].strip(),
        "metadata": {k: v for k, v in meta.items() if k in SAFE_META},
    }


def _enrich_single_call(text: str, source: str, document_context: str = "") -> dict:
    """One logical completion; SDK may retry a transport failure once."""
    global _last_usage
    _last_usage = None
    response = _client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        max_tokens=300,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Source: {source}\nDocument context (verbatim excerpt): {document_context}\n"
                f"Child text (verbatim): {text}"
            )},
        ],
    )
    usage = getattr(response, "usage", None)
    _last_usage = usage.model_dump() if usage is not None else None
    return _validate(json.loads(response.choices[0].message.content))


def _key(text: str, source: str, context: str) -> str:
    payload = json.dumps({
        "text": text, "source": source, "context": context, "model": MODEL,
        "prompt": SYSTEM_PROMPT, "version": PROMPT_VERSION, "schema": "json_object",
        "max_tokens": 300, "temperature": 0,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _standalone(text: str, source: str = "") -> dict:
    if not text.strip() or not OPENAI_API_KEY:
        return {}
    try:
        return _enrich_single_call(text, source)
    except Exception:  # noqa: BLE001 - standalone helper retains offline fallback
        return {}


def summarize_chunk(text: str) -> str:
    return _standalone(text).get("summary", text)


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    if n_questions <= 0:
        return []
    return _standalone(text).get("questions", [])[:n_questions]


def contextual_prepend(text: str, document_title: str = "") -> str:
    context = _standalone(text, document_title).get("context", "")
    return f"{context}\n\n{text}" if context else text


def extract_metadata(text: str) -> dict:
    return _standalone(text).get("metadata", {})


def enrich_chunks(
    chunks: list[dict], methods: list[str] | None = None,
    document_contexts: dict[str, str] | None = None,
    cache_dir: str | Path = DEFAULT_CACHE,
    stats: dict | None = None,
) -> list[EnrichedChunk]:
    methods = ["combined"] if methods is None else methods
    allowed = {"combined", "summary", "hyqa", "contextual", "metadata"}
    if not methods or set(methods) - allowed or ("combined" in methods and len(methods) != 1):
        raise ValueError(f"Invalid enrichment methods: {methods}")
    counts = {"logical_calls": 0, "cache_hits": 0, "failures": 0,
              "fallbacks": 0, "api_successes": 0, "sdk_max_retries_per_call": 1,
              "actual_transport_retries": None, "prompt_tokens": 0, "completion_tokens": 0}
    output = []
    cache_root = Path(cache_dir)
    disabled_reason = None
    consecutive_failures = 0
    for index, chunk in enumerate(chunks, start=1):
        text = chunk["text"]
        trusted = dict(chunk.get("metadata") or {})
        source = str(trusted.get("source", ""))
        context = (document_contexts or {}).get(trusted.get("parent_id"), "")
        status, reason, result = "fallback", None, {}
        if not text.strip():
            reason = "empty input"
        elif "combined" in methods:
            path = cache_root / f"{_key(text, source, context)}.json"
            if path.exists():
                try:
                    result = _validate(json.loads(path.read_text(encoding="utf-8")))
                    status = "cache_hit"
                    counts["cache_hits"] += 1
                except (ValueError, TypeError, OSError, json.JSONDecodeError):
                    result = {}
            if status != "cache_hit":
                if not OPENAI_API_KEY:
                    reason = "OPENAI_API_KEY unavailable"
                elif disabled_reason:
                    reason = disabled_reason
                else:
                    counts["logical_calls"] += 1
                    try:
                        result = _enrich_single_call(text, source, context)
                        if not result["context"] or result["context"].strip() == text.strip():
                            raise ValueError("No useful contextual enrichment")
                        status = "api_success"
                        counts["api_successes"] += 1
                        consecutive_failures = 0
                        if _last_usage:
                            counts["prompt_tokens"] += _last_usage.get("prompt_tokens", 0)
                            counts["completion_tokens"] += _last_usage.get("completion_tokens", 0)
                        cache_root.mkdir(parents=True, exist_ok=True)
                        temporary = path.with_suffix(".tmp")
                        temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                        os.replace(temporary, path)
                    except Exception as error:  # noqa: BLE001 - API failures become explicit fallback
                        reason = f"{type(error).__name__}: {error}"
                        counts["failures"] += 1
                        consecutive_failures += 1
                        if (getattr(error, "status_code", None) in (401, 403, 429)
                                or type(error).__name__ in ("AuthenticationError", "RateLimitError")):
                            disabled_reason = reason
                        elif consecutive_failures >= 3:
                            disabled_reason = f"Stopped after 3 consecutive failures: {reason}"
        else:
            # Educational modes use the same validated completion where requested.
            result = _standalone(text, source)
            status = "api_success" if result else "fallback"
            reason = None if result else "API unavailable or invalid response"
        if status == "fallback":
            counts["fallbacks"] += 1
        summary = result.get("summary", "") if "combined" in methods or "summary" in methods else ""
        questions = result.get("questions", []) if "combined" in methods or "hyqa" in methods else []
        context_line = result.get("context", "") if "combined" in methods or "contextual" in methods else ""
        llm_meta = result.get("metadata", {}) if "combined" in methods or "metadata" in methods else {}
        output.append(EnrichedChunk(
            original_text=text,
            enriched_text=f"{context_line}\n\n{text}" if context_line else text,
            summary=summary, hypothesis_questions=questions,
            auto_metadata={**trusted, "llm": llm_meta} if llm_meta else trusted,
            method="+".join(methods), status=status, reason=reason, llm_metadata=llm_meta,
        ))
        if index % 10 == 0 or index == len(chunks):
            print(f"  M5 {index}/{len(chunks)}: calls={counts['logical_calls']} "
                  f"cache={counts['cache_hits']} fallback={counts['fallbacks']}", flush=True)
    if stats is not None:
        stats.update(counts)
    return output
