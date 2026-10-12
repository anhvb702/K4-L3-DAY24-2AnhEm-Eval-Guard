"""Offline adapter checks; these do not prove live models, APIs or Qdrant readiness."""
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest

pytestmark = pytest.mark.support


def test_chunk_enrichment_preserves_order_and_parent_metadata(monkeypatch, tmp_path):
    from src import m1_chunking as m1, m5_enrichment as m5
    monkeypatch.setattr(m5, "OPENAI_API_KEY", "")
    parents, children = m1.chunk_hierarchical("First policy. Second policy.",
                                            parent_size=20, child_size=10,
                                            metadata={"source": "policy.md"})
    chunks = [{"text": c.text, "metadata": {**c.metadata, "parent_id": c.parent_id}}
              for c in children]
    enriched = m5.enrich_chunks(chunks, cache_dir=tmp_path)
    assert len(enriched) == len(children)
    assert [e.original_text for e in enriched] == [c.text for c in children]
    assert all(e.auto_metadata == c["metadata"] for e, c in zip(enriched, chunks))
    assert all(c.parent_id in {p.parent_id for p in parents} for c in children)


def test_dense_uses_qdrant_19_search_and_preserves_payload():
    import numpy as np
    from src.m2_search import DenseSearch
    from config import EMBEDDING_DIM
    dense = DenseSearch.__new__(DenseSearch)
    payload = {"text": "policy", "source": "policy.md", "parent_id": "parent_1"}
    def search(*, collection_name, query_vector, limit, with_payload):
        assert len(query_vector) == EMBEDDING_DIM and with_payload
        return [SimpleNamespace(payload=payload, score=.9)]
    dense.client = SimpleNamespace(collection_exists=lambda _: True, search=search)
    dense._encoder = SimpleNamespace(encode=lambda _: np.ones(EMBEDDING_DIM))
    result = dense.search("question")[0]
    assert result.text == "policy" and result.score == .9
    assert result.metadata == payload


def test_reranker_preserves_selected_metadata_and_validates_count(monkeypatch):
    from src.m3_rerank import CrossEncoderReranker
    reranker = CrossEncoderReranker()
    prediction = Mock(return_value=[.2, .9])
    monkeypatch.setattr(reranker, "_load_model", lambda: SimpleNamespace(predict=prediction))
    docs = [{"text": str(i), "score": .1, "metadata": {"parent_id": str(i)}} for i in range(2)]
    result = reranker.rerank("Q", docs, top_k=1)
    assert result[0].text == "1" and result[0].metadata == docs[1]["metadata"]
    prediction.return_value = [.1]
    with pytest.raises(ValueError, match="scores"):
        reranker.rerank("Q", docs)


def test_evaluator_reports_instantiated_models_and_row_order(monkeypatch):
    from src import m4_eval as m4
    calls = {}
    def llm(**kwargs):
        calls["llm"] = kwargs
        return SimpleNamespace(model_name="instantiated-evaluator")
    def embeddings(**kwargs):
        calls["embedding"] = kwargs
        return SimpleNamespace(model="instantiated-embedding")
    scores = [{name: value for name in m4.METRICS} for value in (.2, .8)]
    frame = SimpleNamespace(iterrows=lambda: iter(enumerate(scores)))
    class Frame:
        def __len__(self):
            return 2
        def iterrows(self):
            return frame.iterrows()
    evaluate = Mock(return_value=SimpleNamespace(to_pandas=lambda: Frame()))
    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(
        Dataset=SimpleNamespace(from_dict=lambda data: data)))
    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(
        ChatOpenAI=llm, OpenAIEmbeddings=embeddings))
    monkeypatch.setitem(sys.modules, "ragas", SimpleNamespace(evaluate=evaluate))
    monkeypatch.setitem(sys.modules, "ragas.metrics", SimpleNamespace(
        **{name: object() for name in m4.METRICS}))
    monkeypatch.setitem(sys.modules, "ragas.run_config", SimpleNamespace(RunConfig=lambda **kw: kw))
    monkeypatch.setattr(m4, "version", lambda _: "0.1.22")
    result = m4.evaluate_ragas(["Q1", "Q2"], ["A1", "A2"], [["C1"], ["C2"]], ["G1", "G2"])
    assert result["status"] == "success"
    assert [r.question for r in result["per_question"]] == ["Q1", "Q2"]
    assert [r.faithfulness for r in result["per_question"]] == [.2, .8]
    assert result["metadata"]["evaluator_models"] == ["instantiated-embedding", "instantiated-evaluator"]
    assert calls["llm"]["model"] == m4.EVALUATOR_LLM_MODEL
    assert calls["embedding"]["model"] == m4.EVALUATOR_EMBEDDING_MODEL
    assert m4._score(float("nan")) is None and m4._score(1.1) is None
    with pytest.raises(ValueError, match="equal lengths"):
        m4.evaluate_ragas(["Q"], [], [], [])
    scores[0]["question"], scores[1]["question"] = "Q2", "Q1"
    failed = m4.evaluate_ragas(["Q1", "Q2"], ["A1", "A2"], [["C1"], ["C2"]], ["G1", "G2"])
    assert failed["status"] == "failed" and failed["per_question"] == []
    assert all(failed[name] is None for name in m4.METRICS)
    scores[0]["question"], scores[1]["question"] = "Q1", "Q2"
    scores[0]["faithfulness"] = float("nan")
    failed = m4.evaluate_ragas(["Q1", "Q2"], ["A1", "A2"], [["C1"], ["C2"]], ["G1", "G2"])
    assert failed["status"] == "failed" and failed["per_question"] == []
    assert all(failed[name] is None for name in m4.METRICS)


@pytest.mark.parametrize("content", [None, "", "  "])
def test_empty_generation_becomes_explicit_fallback(content):
    from scripts import setup_answers
    search = SimpleNamespace(search=lambda q: [SimpleNamespace(text="retrieved", score=.8, metadata={})])
    reranker = SimpleNamespace(rerank=lambda *args, **kwargs: [])
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    assert setup_answers.run_query("Q", search, reranker, 3, client) == (
        "retrieved", ["retrieved"], "extractive_fallback", None)


@pytest.mark.parametrize("mode", ["count", "order", "identity"])
def test_setup_rejects_misaligned_enrichment_before_indexing(monkeypatch, mode):
    from scripts import setup_answers
    from src import m1_chunking as m1, m2_search as m2, m5_enrichment as m5
    children = [SimpleNamespace(text=str(i), metadata={"source": "policy.md"}, parent_id=str(i))
                for i in range(2)]
    monkeypatch.setattr(m1, "load_documents", lambda: [{"text": "doc", "metadata": {}}])
    monkeypatch.setattr(m1, "chunk_hierarchical", lambda *args, **kw: ([], children))
    search = Mock()
    monkeypatch.setattr(m2, "HybridSearch", search)
    def enrich(chunks):
        output = [SimpleNamespace(original_text=c["text"], enriched_text=c["text"],
                                  auto_metadata=dict(c["metadata"])) for c in chunks]
        if mode == "count":
            return output[:1]
        if mode == "order":
            return output[::-1]
        output[0].auto_metadata["parent_id"] = "wrong-parent"
        return output
    monkeypatch.setattr(m5, "enrich_chunks", enrich)
    with pytest.raises(ValueError, match="enrich_chunks"):
        setup_answers.build_pipeline()
    search.assert_not_called()


def test_reranker_default_matches_config():
    from config import RERANK_MODEL, RERANK_TOP_K
    from src.m3_rerank import CrossEncoderReranker
    import inspect
    assert CrossEncoderReranker().model_name == RERANK_MODEL
    assert inspect.signature(CrossEncoderReranker.rerank).parameters["top_k"].default == RERANK_TOP_K


@pytest.mark.parametrize("models", [None, [], ["measured-llm", "measured-embedding"]])
def test_evaluation_cache_requires_recorded_model_provenance(monkeypatch, tmp_path, models):
    from dataclasses import asdict
    import json
    from src import m4_eval as m4
    inputs = (["Q"], ["A"], [["C"]], ["G"])
    row = m4.EvalResult("Q", "A", ["C"], "G", .5, .5, .5, .5)
    prior = {"status": "success", "evaluator": m4.evaluator_configuration(),
             "evaluation_fingerprint": m4.evaluation_fingerprint(*inputs),
             "num_questions": 1, "valid_count": 1, "failed_count": 0,
             "per_question": [asdict(row)],
             "metric_counts": dict.fromkeys(m4.METRICS, 1),
             "aggregate": dict.fromkeys(m4.METRICS, .5)}
    if models is not None:
        prior["metadata"] = {"evaluator_models": models}
    path = tmp_path / "cache.json"
    path.write_text(json.dumps(prior), encoding="utf-8")
    fresh = Mock(return_value={"status": "failed"})
    monkeypatch.setattr(m4, "evaluate_ragas", fresh)
    result = m4.evaluate_with_cache(*inputs, str(path))
    if models:
        fresh.assert_not_called()
        assert result["metadata"]["evaluator_models"] == models
    else:
        fresh.assert_called_once_with(*inputs)
        assert result["evaluation_cache_hit"] is False


def test_failed_evaluation_report_does_not_fabricate_zero_metrics(tmp_path):
    import json
    from src import m4_eval as m4
    failed = m4._failed_result(1, "evaluation unavailable")
    path = m4.save_report(failed, [], str(tmp_path / "failed.json"))
    saved = json.loads(__import__("pathlib").Path(path).read_text(encoding="utf-8"))
    assert saved["status"] == "failed" and saved["per_question"] == []
    assert all(value is None for value in saved["aggregate"].values())
