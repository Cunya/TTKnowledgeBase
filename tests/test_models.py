import pytest
from pydantic import ValidationError

from processors.models import ConceptEvidence, SourceSpan


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
