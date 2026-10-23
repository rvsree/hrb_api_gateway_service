"""Phase 4 - duplicated (not imported) request-shape copies of hrb_chatbot_v2's
RagQueryRequest/AgenticRagRequest/MultiAgenticRagRequest, as of 2026-10-21
(post Phase 244's guardrails_model field) - see ROADMAP.md's own Context note
for why these are duplicated rather than a real cross-repo import. Enum-
constrained fields (search_strategy, vector_db, llm_provider) are plain str
here, deliberately - see ROADMAP.md's Out of scope note."""

from pydantic import BaseModel, ConfigDict, Field

from gateway.models import UserProfile


class SearchOptions(BaseModel):
    top_k: int | None = Field(None, ge=1, le=20)
    vector_db: str | None = None
    search_strategy: str | None = None
    lambda_mult: float | None = Field(None, ge=0.0, le=1.0)
    use_multi_query: bool = False
    use_self_query: bool = False
    llm_provider: str | None = None
    enable_corrective_retry: bool = False


class GenerationOptions(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str | None = Field(None, max_length=100)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1)


class EvalOptions(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    judge_model: str | None = Field(None, max_length=100)
    eval_score_threshold: float | None = Field(None, ge=0.0, le=1.0)


class ClassificationOptions(BaseModel):
    decompose_model: str | None = Field(None, max_length=100)
    planner_model: str | None = Field(None, max_length=100)


class RagQueryRequest(BaseModel):
    user_profile: UserProfile | None = None
    query: str = Field(..., min_length=1, max_length=2000)
    search_options: SearchOptions | None = None
    generation_options: GenerationOptions | None = None
    eval_options: EvalOptions | None = None
    classification_options: ClassificationOptions | None = None
    guardrails_model: str | None = Field(None, max_length=100)
    enable_conversation_memory: bool = False
    conversation_id: str | None = None


class AgenticRagRequest(BaseModel):
    user_profile: UserProfile | None = None
    query: str = Field(..., min_length=1, max_length=2000)
    max_iterations: int | None = Field(None, ge=1, le=10)
    search_strategy: str | None = None
    eval_options: EvalOptions | None = None
    guardrails_model: str | None = Field(None, max_length=100)
    enable_conversation_memory: bool = False
    conversation_id: str | None = None


class MultiAgenticRagRequest(BaseModel):
    user_profile: UserProfile | None = None
    query: str = Field(..., min_length=1, max_length=2000)
    search_strategy: str | None = None
    eval_options: EvalOptions | None = None
    classification_options: ClassificationOptions | None = None
    guardrails_model: str | None = Field(None, max_length=100)
    enable_conversation_memory: bool = False
    conversation_id: str | None = None


# Phase 4 - scoped to the 3 real query endpoints only, not this backend's
# full surface (ingestion/auth/feedback/conversations/admin/...) - see
# ROADMAP.md's Out of scope note.
PATH_TO_MODEL: dict[str, type[BaseModel]] = {
    "/v1/genai-rag-retrieval/query": RagQueryRequest,
    "/v1/single-agentic-rag-retrieval/query": AgenticRagRequest,
    "/v1/multi-agentic-rag-retrieval/query": MultiAgenticRagRequest,
}


def validate_contract(path: str, body: bytes) -> None:
    """No-op for any path not in PATH_TO_MODEL - today's unvalidated forwarding
    behavior, unchanged. Raises pydantic.ValidationError for a known path with
    an invalid body - caller (main.py) turns that into a 422."""
    model = PATH_TO_MODEL.get(path)
    if model is None:
        return
    model.model_validate_json(body)
