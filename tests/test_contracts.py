import json

import pytest

from gateway.contracts import validate_contract


def test_unknown_path_is_a_no_op_even_with_garbage_body():
    validate_contract("/v1/some-unscoped-endpoint", b"not even json")


def test_known_path_valid_body_passes():
    body = json.dumps({"query": "What's the dental plan?"}).encode()
    validate_contract("/v1/genai-rag-retrieval/query", body)


def test_known_path_missing_required_field_raises():
    body = json.dumps({}).encode()
    with pytest.raises(Exception):
        validate_contract("/v1/genai-rag-retrieval/query", body)


def test_known_path_wrong_type_raises():
    body = json.dumps({"query": "ok", "search_options": {"top_k": "not a number"}}).encode()
    with pytest.raises(Exception):
        validate_contract("/v1/genai-rag-retrieval/query", body)


def test_agentic_rag_path_validated_independently():
    body = json.dumps({"query": "ok", "max_iterations": 3}).encode()
    validate_contract("/v1/single-agentic-rag-retrieval/query", body)


def test_multi_agentic_rag_path_validated_independently():
    body = json.dumps({"query": "ok", "classification_options": {"planner_model": "gpt-4.1-nano"}}).encode()
    validate_contract("/v1/multi-agentic-rag-retrieval/query", body)


def test_guardrails_model_field_accepted_on_all_three():
    body = json.dumps({"query": "ok", "guardrails_model": "gpt-4.1-mini"}).encode()
    validate_contract("/v1/genai-rag-retrieval/query", body)
    validate_contract("/v1/single-agentic-rag-retrieval/query", body)
    validate_contract("/v1/multi-agentic-rag-retrieval/query", body)
