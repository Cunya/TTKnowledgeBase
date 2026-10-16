import pytest
from pydantic import ValidationError

from processors.models import ConceptCandidate, ConceptEvidence, SourceSpan, TranscriptTrack


@pytest.mark.parametrize("generated, origin", [(True, "youtube_generated"), (False, "youtube_manual")])
def test_legacy_origin_uses_stored_provider_flag_without_changing_input(generated, origin):
    raw = {"video_id": "video123456", "language": "English", "language_code": "en",
           "is_generated": generated, "acquisition_method": "youtube-transcript-api", "segments": []}
    assert TranscriptTrack.model_validate(raw).transcript_origin == origin
    assert "transcript_origin" not in raw
    raw["transcript_origin"] = "supplied"
    assert TranscriptTrack.model_validate(raw).transcript_origin == "supplied"


def test_source_range_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            video_id="video123456",
            start_ms=1000,
            end_ms=1000,
            url="https://example.com",
            segment_ids=["video123456:00001"],
        )


def test_spoken_context_cannot_end_before_source() -> None:
    with pytest.raises(ValidationError):
        ConceptEvidence(
            id="evidence-1",
            evidence_type="explanation",
            excerpt="Supported explanation.",
            reason="Test fixture.",
            confidence=1,
            source=SourceSpan(
                video_id="video123456",
                start_ms=1000,
                end_ms=3000,
                url="https://example.com",
                segment_ids=["video123456:00001"],
            ),
            spoken_context_end_ms=2000,
        )


@pytest.mark.parametrize(
    ("resolution", "matched_concept_id"),
    [("match", None), ("new", "concept-existing"), ("ambiguous", "concept-existing")],
)
def test_candidate_resolution_and_target_must_be_consistent(
    resolution: str, matched_concept_id: str | None
) -> None:
    with pytest.raises(ValidationError):
        ConceptCandidate.model_validate(
            {
                "candidate_id": "candidate-1",
                "canonical_label": "Ready position",
                "aliases": [],
                "definition": "A balanced stance used before and after each stroke.",
                "concept_type": "technique",
                "facets": [],
                "difficulty": None,
                "resolution": resolution,
                "matched_concept_id": matched_concept_id,
                "confidence": 0.9,
                "evidence": [
                    {
                        "evidence_type": "explanation",
                        "segment_ids": ["video123456:00001"],
                        "reason": "The row defines the stance.",
                        "confidence": 0.9,
                        "visual_status": "not_visual",
                    }
                ],
                "relations": [],
                "uncertainty": [],
            }
        )
