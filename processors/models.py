from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReviewStatus = Literal["unreviewed", "approved", "rejected"]
EvidenceType = Literal[
    "definition", "explanation", "demonstration", "example", "mistake", "correction", "drill"
]


class SourceSpan(BaseModel):
    video_id: str = Field(min_length=3)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    url: str
    segment_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_range(self) -> SourceSpan:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class VisualSpan(BaseModel):
    video_id: str = Field(min_length=3)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    url: str
    selection_method: Literal["nearby_visual_inference", "manual_review"]
    note: str

    @model_validator(mode="after")
    def valid_range(self) -> VisualSpan:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class Segment(BaseModel):
    id: str
    video_id: str
    text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


class TranscriptTrack(BaseModel):
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    acquisition_method: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    segments: list[Segment]


class Video(BaseModel):
    id: str
    title: str
    canonical_url: str
    channel_id: str = ""
    channel_name: str = ""
    duration_ms: int = Field(ge=0)
    published_at: str | None = None
    thumbnail_url: str | None = None
    language: str | None = None
    availability: str = "available_online"
    transcript: TranscriptTrack | None = None


class GeneratedBy(BaseModel):
    processor: str
    version: str
    input_hash: str
    model: str | None = None
    reasoning_effort: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceCandidate(StrictModel):
    evidence_type: EvidenceType
    segment_ids: list[str] = Field(min_length=1)
    reason: str
    confidence: float = Field(ge=0, le=1)
    visual_status: Literal["not_visual", "transcript_inferred", "verified_visual_demo"]


class RelationCandidate(StrictModel):
    relation_type: Literal[
        "prerequisite_of",
        "part_of",
        "variation_of",
        "contrasts_with",
        "used_with",
        "causes",
        "corrects",
    ]
    target_label: str
    segment_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class FacetCandidate(StrictModel):
    name: str
    values: list[str]


class ConceptCandidate(StrictModel):
    candidate_id: str
    canonical_label: str
    aliases: list[str]
    definition: str
    concept_type: str
    facets: list[FacetCandidate]
    difficulty: str | None
    resolution: Literal["new", "match", "ambiguous"]
    matched_concept_id: str | None
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceCandidate] = Field(min_length=1)
    relations: list[RelationCandidate]
    uncertainty: list[str]


class ExtractionResponse(StrictModel):
    concepts: list[ConceptCandidate]
    batch_notes: list[str]


class ExcerptRewriteResponse(StrictModel):
    """A concise editorial summary for a source-backed evidence excerpt."""

    excerpt: str = Field(min_length=1, max_length=420)


class EvidenceSummaryResponse(StrictModel):
    """A coherent editorial synthesis of reviewed evidence reasons."""

    summary: str = Field(min_length=120, max_length=1800)


class EvidenceSummaryItem(StrictModel):
    concept_id: str = Field(min_length=1)
    summary: str = Field(min_length=120, max_length=1800)


class EvidenceSummaryBatchResponse(StrictModel):
    summaries: list[EvidenceSummaryItem] = Field(min_length=1)


class ConceptEvidence(BaseModel):
    id: str
    evidence_type: EvidenceType
    excerpt: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    visual_status: Literal["not_visual", "transcript_inferred", "verified_visual_demo"] = (
        "not_visual"
    )
    source: SourceSpan
    spoken_context_end_ms: int | None = Field(default=None, gt=0)
    visual_source: VisualSpan | None = None
    review_status: ReviewStatus = "approved"

    @model_validator(mode="after")
    def valid_spoken_context(self) -> ConceptEvidence:
        if self.spoken_context_end_ms is not None and self.spoken_context_end_ms < self.source.end_ms:
            raise ValueError("spoken_context_end_ms cannot end before the cited source")
        return self


class ConceptRelation(BaseModel):
    relation_type: str
    target_concept_id: str
    sources: list[SourceSpan]
    confidence: float = Field(ge=0, le=1)
    review_status: ReviewStatus = "approved"


class Concept(BaseModel):
    id: str
    slug: str
    label: str
    aliases: list[str] = []
    short_definition: str
    detailed_definition: str | None = None
    evidence_summary: str | None = None
    evidence_summary_source_hash: str | None = None
    evidence_summary_generator: str | None = None
    concept_type: str
    facets: dict[str, list[str]] = {}
    difficulty: str | None = None
    evidence: list[ConceptEvidence] = Field(min_length=1)
    relations: list[ConceptRelation] = []
    review_status: ReviewStatus = "approved"
    generated_by: GeneratedBy | None = None


class TopicNode(BaseModel):
    id: str
    label: str
    description: str | None = None
    concept_ids: list[str] = []
    children: list[TopicNode] = []


class KnowledgeNavigation(BaseModel):
    title: str
    introduction: str
    sections: list[TopicNode]


class PublishCorpus(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    knowledge_base: dict[str, str]
    concepts: list[Concept]
    videos: list[Video]
    navigation: KnowledgeNavigation | None = None
