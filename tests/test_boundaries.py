from processors.boundaries import (
    assess_boundary,
    build_boundary_report,
    build_boundary_review_set,
    derive_caption_units,
    render_boundary_review_set_markdown,
    validate_boundary_review_set,
)
from processors.models import Concept, ConceptEvidence, Segment, SourceSpan, TranscriptTrack, Video


def make_video(segments: list[Segment], duration_ms: int = 60_000) -> Video:
    return Video(
        id="boundary-video",
        title="Boundary test",
        canonical_url="https://www.youtube.com/watch?v=boundary-video",
        duration_ms=duration_ms,
        transcript=TranscriptTrack(
            video_id="boundary-video",
            language="English",
            language_code="en",
            is_generated=True,
            acquisition_method="fixture",
            segments=segments,
        ),
    )


def test_caption_units_merge_non_terminal_cues_and_keep_ids() -> None:
    segments = [
        Segment(
            id="s1", video_id="boundary-video", text="Keep the swing", normalized_text="Keep the swing", start_ms=0, duration_ms=1_000
        ),
        Segment(
            id="s2", video_id="boundary-video", text="compact and relaxed.", normalized_text="compact and relaxed.", start_ms=1_000, duration_ms=2_000
        ),
        Segment(
            id="s3", video_id="boundary-video", text="Then recover.", normalized_text="Then recover.", start_ms=3_000, duration_ms=2_000
        ),
    ]
    units = derive_caption_units(segments)
    assert [unit.segment_ids for unit in units] == [("s1", "s2"), ("s3",)]


def test_assessment_flags_partial_and_short_citation_with_snapped_bounds() -> None:
    segments = [
        Segment(
            id="s1", video_id="boundary-video", text="Keep the swing", normalized_text="Keep the swing", start_ms=0, duration_ms=1_500
        ),
        Segment(
            id="s2", video_id="boundary-video", text="compact and relaxed.", normalized_text="compact and relaxed.", start_ms=1_500, duration_ms=2_500
        ),
    ]
    assessment = assess_boundary(make_video(segments), ["s2"])
    assert assessment is not None
    assert assessment.segment_ids == ("s2",)
    assert assessment.start_ms == 1_500
    assert assessment.snapped_start_ms == 0
    assert "starts_mid_sentence" in assessment.flags
    assert "too_short" in assessment.flags
    assert assessment.needs_context


def test_complete_longer_citation_is_not_flagged() -> None:
    segments = [
        Segment(
            id="s1", video_id="boundary-video", text="Keep the swing", normalized_text="Keep the swing", start_ms=0, duration_ms=2_000
        ),
        Segment(
            id="s2", video_id="boundary-video", text="compact and relaxed.", normalized_text="compact and relaxed.", start_ms=2_000, duration_ms=3_000
        ),
    ]
    assessment = assess_boundary(make_video(segments), ["s1", "s2"])
    assert assessment is not None
    assert assessment.flags == ()
    assert assessment.snapped_start_ms == assessment.start_ms == 0
    assert assessment.snapped_end_ms == assessment.end_ms == 5_000


def test_report_counts_missing_transcripts_and_boundary_flags() -> None:
    segments = [
        Segment(
            id="s1", video_id="boundary-video", text="Keep the swing", normalized_text="Keep the swing", start_ms=0, duration_ms=1_500
        ),
        Segment(
            id="s2", video_id="boundary-video", text="compact and relaxed.", normalized_text="compact and relaxed.", start_ms=1_500, duration_ms=2_500
        ),
    ]
    video = make_video(segments)
    evidence = ConceptEvidence(
        id="e1",
        evidence_type="explanation",
        excerpt="A compact swing.",
        reason="fixture",
        confidence=0.9,
        source=SourceSpan(
            video_id=video.id,
            start_ms=1_500,
            end_ms=4_000,
            url="https://www.youtube.com/watch?v=boundary-video&t=2s",
            segment_ids=["s2"],
        ),
    )
    concept = Concept(
        id="concept-boundary",
        slug="concept-boundary",
        label="Boundary",
        short_definition="Boundary test.",
        concept_type="technique",
        evidence=[evidence],
    )
    report = build_boundary_report([concept], [video], "test")
    assert report["evaluated_count"] == 1
    assert report["rates"]["needs_context"] == 1.0
    assert report["flagged_samples"][0]["flags"]


def test_boundary_review_set_is_stratified_and_undecided() -> None:
    segments = [
        Segment(
            id="s1", video_id="boundary-video", text="Keep the swing", normalized_text="Keep the swing", start_ms=0, duration_ms=1_500
        ),
        Segment(
            id="s2", video_id="boundary-video", text="compact and relaxed.", normalized_text="compact and relaxed.", start_ms=1_500, duration_ms=2_500
        ),
        Segment(
            id="s3", video_id="boundary-video", text="A separate cue.", normalized_text="A separate cue.", start_ms=3_000, duration_ms=1_000
        ),
    ]
    video = make_video(segments)
    evidence = ConceptEvidence(
        id="boundary-review-evidence",
        evidence_type="explanation",
        excerpt="Keep the swing compact.",
        reason="Boundary review fixture.",
        confidence=0.9,
        source=SourceSpan(
            video_id=video.id,
            start_ms=1_500,
            end_ms=4_000,
            url="https://www.youtube.com/watch?v=boundary-video&t=2s",
            segment_ids=["s2"],
        ),
    )
    concept = Concept(
        id="concept-boundary-review",
        slug="concept-boundary-review",
        label="Boundary review",
        short_definition="Boundary review fixture.",
        concept_type="technique",
        evidence=[evidence],
    )
    first = build_boundary_review_set([concept], [video], "test", sample_size=4)
    second = build_boundary_review_set([concept], [video], "test", sample_size=4)
    assert first["items"] == second["items"]
    assert first["items"][0]["review_action"] is None
    assert first["review_actions"] == ["keep", "merge", "split", "defer"]
    assert "pending" in render_boundary_review_set_markdown(first, "Test")
    assert validate_boundary_review_set(first, [video]) == []
