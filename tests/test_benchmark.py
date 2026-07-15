from processors.benchmark import render_benchmark_markdown, score_response
from processors.models import (
    Concept,
    ConceptCandidate,
    ConceptEvidence,
    EvidenceCandidate,
    ExtractionResponse,
    Segment,
    SourceSpan,
    TranscriptTrack,
    Video,
)


def benchmark_video() -> Video:
    return Video(
        id="vid123",
        title="Forehand loop basics",
        canonical_url="https://www.youtube.com/watch?v=vid123",
        duration_ms=20_000,
        transcript=TranscriptTrack(
            video_id="vid123",
            language="English",
            language_code="en",
            is_generated=False,
            acquisition_method="test",
            segments=[
                Segment(
                    id="vid123:00001",
                    video_id="vid123",
                    text="Brush the ball with a relaxed forehand loop.",
                    normalized_text="Brush the ball with a relaxed forehand loop.",
                    start_ms=1_000,
                    duration_ms=2_000,
                ),
                Segment(
                    id="vid123:00002",
                    video_id="vid123",
                    text="Recover to ready position.",
                    normalized_text="Recover to ready position.",
                    start_ms=3_000,
                    duration_ms=2_000,
                ),
            ],
        ),
    )


def reviewed_forehand_loop() -> Concept:
    return Concept(
        id="concept-1",
        slug="forehand-loop",
        label="Forehand loop",
        aliases=["FH loop"],
        short_definition="A topspin forehand stroke.",
        concept_type="shot",
        evidence=[
            ConceptEvidence(
                id="evidence-1",
                evidence_type="explanation",
                excerpt="Brush the ball with a relaxed forehand loop.",
                reason="The speaker describes the stroke.",
                confidence=0.9,
                source=SourceSpan(
                    video_id="vid123",
                    start_ms=1_000,
                    end_ms=3_000,
                    url="https://youtu.be/vid123?t=1",
                    segment_ids=["vid123:00001"],
                ),
            )
        ],
    )


def test_score_response_checks_real_citations_and_reviewed_support() -> None:
    response = ExtractionResponse(
        concepts=[
            ConceptCandidate(
                candidate_id="candidate-1",
                canonical_label="Forehand loop",
                aliases=[],
                definition="A relaxed topspin forehand stroke.",
                concept_type="shot",
                facets=[],
                difficulty=None,
                resolution="match",
                matched_concept_id="concept-1",
                confidence=0.9,
                evidence=[
                    EvidenceCandidate(
                        evidence_type="explanation",
                        segment_ids=["vid123:00001", "vid123:not-real"],
                        reason="The segment explains the stroke.",
                        confidence=0.9,
                        visual_status="not_visual",
                    )
                ],
                relations=[],
                uncertainty=[],
            )
        ],
        batch_notes=[],
    )

    metrics = score_response(response, benchmark_video(), [reviewed_forehand_loop()])

    assert metrics["candidate_count"] == 1
    assert metrics["valid_citation_rate"] == 0.5
    assert metrics["overlap_support_rate"] == 1.0
    assert metrics["concept_recall_proxy"] == 1.0


def test_benchmark_markdown_explains_screening_signals() -> None:
    report = {
        "generated_at": "2026-07-15T00:00:00+00:00",
        "video_ids": ["vid123"],
        "summary": [
            {
                "model": "gpt-5.4-nano",
                "availability": "available",
                "failure_reasons": [],
                "run_count": 1,
                "schema_valid_rate": 1.0,
                "valid_citation_rate": 1.0,
                "overlap_support_rate": 1.0,
                "concept_recall_proxy": 1.0,
                "candidate_count": 1.0,
                "input_tokens": 10,
                "output_tokens": 5,
            }
        ],
        "runs": [
            {
                "model": "gpt-5.4-nano",
                "video_id": "vid123",
                "status": "ok",
                "metrics": {
                    "candidate_count": 1,
                    "valid_citation_rate": 1.0,
                    "overlap_support_rate": 1.0,
                },
            }
        ],
        "method": {"warning": "Not an editorial approval."},
    }

    markdown = render_benchmark_markdown(report, "Table Tennis")

    assert "# Table Tennis Codex extraction quality benchmark" in markdown
    assert "not a billing estimate" in markdown
