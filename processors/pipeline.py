from __future__ import annotations

import os
import re
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

import networkx as nx
from rapidfuzz.fuzz import token_set_ratio
from ruamel.yaml import YAML

from .boundaries import (
    MAX_CITED_SEGMENT_GAP_MS,
    MAX_SOURCE_DURATION_MS,
    BoundaryAssessment,
    assess_boundary,
    caption_duration_conflicts,
)
from .codex_engine import (
    CodexError,
    CodexResponseError,
    CodexTimeoutError,
    adjudicate_candidate_with_codex,
    extract_with_codex,
    rephrase_excerpt_with_codex,
)
from .llm_budget import LLMBudgetExceeded
from .models import (
    CandidateAdjudicationResponse,
    Concept,
    ExtractionResponse,
    KnowledgeNavigation,
    PublishCorpus,
    Segment,
    SourceSpan,
    Video,
)
from .published_repair import verify_article_with_codex
from .utils import (
    read_json,
    read_yaml,
    replace_with_retry,
    sha256_json,
    slugify,
    write_json,
    youtube_url,
)
from .workspace import processing_is_paused

MAX_SPOKEN_SOURCE_MS = MAX_SOURCE_DURATION_MS
ADJUDICATION_CHECKPOINT_SIZE = 10
DEFAULT_REPHRASE_MIN_WORDS = 8
DEFAULT_REPHRASE_MIN_RATIO = 0.75
MOJIBAKE_MARKERS = ("\ufffd", "Â", "â€", "â†", "ðŸ")

roundtrip_yaml = YAML()
roundtrip_yaml.preserve_quotes = True
roundtrip_yaml.indent(mapping=2, sequence=4, offset=2)


roundtrip_yaml.width = 4096


def load_videos(directory: Path) -> list[Video]:
    videos = []
    for path in sorted(directory.glob("*.json")):
        video = Video.model_validate(read_json(path))
        if video.ingested_at is None:
            video = video.model_copy(
                update={"ingested_at": datetime.fromtimestamp(path.stat().st_mtime, UTC)}
            )
        videos.append(video)
    return videos


def load_reviewed_concepts(directory: Path) -> list[Concept]:
    concepts: list[Concept] = []
    for path in sorted(directory.glob("*.yaml")):
        data = read_yaml(path)
        if data:
            concepts.append(Concept.model_validate(data))
    return concepts


def _overlap_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def longest_contiguous_overlap(excerpt: str, transcript_text: str) -> int:
    """Return the longest contiguous word run shared by excerpt and transcript context."""
    excerpt_words = _overlap_words(excerpt)
    transcript_words = _overlap_words(transcript_text)
    longest = 0
    for start in range(len(excerpt_words)):
        for end in range(start + longest + 1, len(excerpt_words) + 1):
            candidate = excerpt_words[start:end]
            if any(
                transcript_words[index : index + len(candidate)] == candidate
                for index in range(len(transcript_words) - len(candidate) + 1)
            ):
                longest = end - start
    return longest


def find_high_overlap_excerpts(
    concepts: list[Concept],
    videos: list[Video],
    *,
    min_words: int = DEFAULT_REPHRASE_MIN_WORDS,
    min_ratio: float = DEFAULT_REPHRASE_MIN_RATIO,
) -> list[dict]:
    """Find public excerpts whose wording is too close to their cited transcript."""
    segments = {
        video.id: {
            segment.id: segment.normalized_text
            for segment in (video.transcript.segments if video.transcript else [])
        }
        for video in videos
    }
    findings: list[dict] = []
    for concept in concepts:
        for evidence in concept.evidence:
            source_segments = segments.get(evidence.source.video_id, {})
            transcript_text = " ".join(
                source_segments[segment_id]
                for segment_id in evidence.source.segment_ids
                if segment_id in source_segments
            )
            if not transcript_text:
                continue
            excerpt_words = _overlap_words(evidence.excerpt)
            longest = longest_contiguous_overlap(evidence.excerpt, transcript_text)
            ratio = longest / len(excerpt_words) if excerpt_words else 0.0
            transcript_words = _overlap_words(transcript_text)
            complete_match = any(
                transcript_words[index : index + len(excerpt_words)] == excerpt_words
                for index in range(len(transcript_words) - len(excerpt_words) + 1)
            )
            if longest < min_words or (not complete_match and ratio < min_ratio):
                continue
            findings.append(
                {
                    "concept_id": concept.id,
                    "evidence_id": evidence.id,
                    "excerpt": evidence.excerpt,
                    "transcript_text": transcript_text,
                    "longest_matching_words": longest,
                    "overlap_ratio": round(ratio, 4),
                    "complete_match": complete_match,
                }
            )
    return findings


def rephrase_high_overlap_excerpts(
    concept_dir: Path,
    concepts: list[Concept],
    videos: list[Video],
    config_path: Path,
    audit_dir: Path,
    *,
    budget_path: Path | None = None,
    model_override: str | None = None,
    taxonomy: dict | None = None,
    min_words: int = DEFAULT_REPHRASE_MIN_WORDS,
    min_ratio: float = DEFAULT_REPHRASE_MIN_RATIO,
    max_chars: int = 420,
    rephrase: Callable[[str, str, int], tuple[str, dict]] | None = None,
    persist: bool = True,
) -> tuple[list[Concept], list[dict]]:
    """Rephrase flagged excerpts and optionally persist only those excerpt fields."""
    findings = find_high_overlap_excerpts(
        concepts, videos, min_words=min_words, min_ratio=min_ratio
    )
    if not findings:
        return concepts, []
    rewrite = rephrase or (
        lambda excerpt, transcript, limit: rephrase_excerpt_with_codex(
            excerpt,
            transcript,
            config_path,
            audit_dir,
            model_override=model_override,
            max_chars=limit,
            budget_path=budget_path,
        )
    )
    updates: dict[tuple[str, str], str] = {}
    for finding in findings:
        rewritten, provenance = rewrite(
            finding["excerpt"], finding["transcript_text"], max_chars
        )
        rewritten = rewritten.strip()
        if not rewritten or len(rewritten) > max_chars:
            raise ValueError(
                f"{finding['concept_id']}/{finding['evidence_id']}: invalid rephrased excerpt"
            )
        if any(marker in rewritten for marker in ('"', "“", "”")):
            raise ValueError(
                f"{finding['concept_id']}/{finding['evidence_id']}: rephrase contains quotation marks"
            )
        remaining = longest_contiguous_overlap(rewritten, finding["transcript_text"])
        rewritten_words = _overlap_words(rewritten)
        remaining_ratio = remaining / len(rewritten_words) if rewritten_words else 0.0
        remaining_transcript_words = _overlap_words(finding["transcript_text"])
        remaining_complete = any(
            remaining_transcript_words[index : index + len(rewritten_words)] == rewritten_words
            for index in range(len(remaining_transcript_words) - len(rewritten_words) + 1)
        )
        if remaining_complete or (remaining >= min_words and remaining_ratio >= min_ratio):
            raise ValueError(
                f"{finding['concept_id']}/{finding['evidence_id']}: rephrase still has high overlap"
            )
        if rewritten == finding["excerpt"]:
            raise ValueError(
                f"{finding['concept_id']}/{finding['evidence_id']}: rephrase did not change excerpt"
            )
        concept = next(item for item in concepts if item.id == finding["concept_id"])
        evidence = next(item for item in concept.evidence if item.id == finding["evidence_id"])
        video = next(item for item in videos if item.id == evidence.source.video_id)
        rows = {segment.id: segment.model_dump(mode="json") for segment in video.transcript.segments}
        owned = evidence.source.segment_ids
        if any(sid not in rows for sid in owned):
            raise ValueError("Rephrase source proof is incomplete")
        verification, verification_provenance = verify_article_with_codex({
            "article": {"id": concept.id, "label": concept.label},
            "units": {"evidence:0:rewrite": {
                "value": {"excerpt": rewritten, "reason": evidence.reason},
                "allowed_segment_ids": list(owned),
            }},
            "selected_rows": [rows[sid] for sid in owned], "context_rows": [],
        }, config_path, audit_dir, budget_path)
        if any(unit["status"] != "supported" for unit in verification["units"]):
            raise ValueError("Rephrased excerpt failed independent source verification")
        provenance = {**provenance, "support_verification": verification_provenance}
        updates[(finding["concept_id"], finding["evidence_id"])] = rewritten
        finding["new_excerpt"] = rewritten
        finding["remaining_matching_words"] = remaining
        finding["remaining_overlap_ratio"] = round(remaining_ratio, 4)
        finding["remaining_complete_match"] = remaining_complete
        finding["provenance"] = provenance

    updated_concepts: list[Concept] = []
    for concept in concepts:
        evidence = [
            item.model_copy(
                update={"excerpt": updates.get((concept.id, item.id), item.excerpt)}
            )
            for item in concept.evidence
        ]
        updated_concepts.append(concept.model_copy(update={"evidence": evidence}))

    if persist:
        _persist_excerpt_updates(concept_dir, updates, updated_concepts)
    return updated_concepts, findings


def _persist_excerpt_updates(
    concept_dir: Path, updates: dict[tuple[str, str], str], concepts: list[Concept]
) -> None:
    """Apply excerpt-only changes to canonical YAML while retaining reviewed structure."""
    by_slug = {concept.id: concept.slug for concept in concepts}
    for (concept_id, evidence_id), excerpt in updates.items():
        path = concept_dir / f"{by_slug[concept_id]}.yaml"
        document = roundtrip_yaml.load(path.read_text(encoding="utf-8"))
        evidence_items = document.get("evidence", [])
        matches = [item for item in evidence_items if item.get("id") == evidence_id]
        if len(matches) != 1:
            raise ValueError(f"{concept_id}/{evidence_id}: canonical YAML evidence ID is not unique")
        matches[0]["excerpt"] = excerpt
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            roundtrip_yaml.dump(document, handle)
        temporary.replace(path)


def extract_video(
    video: Video,
    taxonomy: dict,
    known_concepts: list[dict],
    processors_config: Path,
    output_dir: Path,
    audit_dir: Path,
    model_override: str | None = None,
    *,
    budget_path: Path | None = None,
    task: str = "extraction",
) -> Path:
    if not video.transcript:
        raise ValueError(f"Video {video.id} has no transcript")
    config = read_yaml(processors_config)["codex"]
    max_segments = int(config.get("max_segments_per_job", 80))
    overlap_segments = int(config.get("overlap_segments", 8))
    if max_segments < 1 or overlap_segments < 0 or overlap_segments >= max_segments:
        raise ValueError("Codex segment batching requires 0 <= overlap < max_segments_per_job")
    step = max_segments - overlap_segments
    segments = video.transcript.segments
    batches = [segments[start : start + max_segments] for start in range(0, len(segments), step)]
    responses: list[ExtractionResponse] = []
    provenances: list[dict] = []
    for batch in batches:
        response, provenance = extract_with_codex(
            batch,
            taxonomy,
            known_concepts,
            processors_config,
            audit_dir,
            model_override=model_override,
            budget_path=budget_path,
            task=task,
        )
        responses.append(response)
        provenances.append(provenance)
    concepts = []
    seen: set[str] = set()
    for batch_index, response in enumerate(responses):
        for candidate in response.concepts:
            fingerprint = sha256_json(
                {
                    "label": candidate.canonical_label.strip().lower(),
                    "definition": candidate.definition.strip().lower(),
                    "segments": sorted(
                        segment_id
                        for evidence in candidate.evidence
                        for segment_id in evidence.segment_ids
                    ),
                }
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            if len(batches) > 1:
                candidate = candidate.model_copy(
                    update={"candidate_id": f"b{batch_index + 1:03d}-{candidate.candidate_id}"}
                )
            concepts.append(candidate)
    response = ExtractionResponse(
        concepts=concepts,
        batch_notes=[
            f"batch {index + 1}/{len(responses)}: {note}"
            for index, item in enumerate(responses)
            for note in item.batch_notes
        ],
    )
    provenance = {
        "processor": "bounded_overlapping_codex_extraction",
        "batch_count": len(batches),
        "max_segments_per_job": max_segments,
        "overlap_segments": overlap_segments,
        "batches": provenances,
        "input_hash": sha256_json([item.get("input_hash") for item in provenances]),
    }
    payload = {
        "video_id": video.id,
        "response": response.model_dump(mode="json"),
        "provenance": provenance,
    }
    path = output_dir / f"{video.id}.candidates.json"
    write_json(path, payload)
    return path


def _normalize_legacy_candidate_resolution(candidate: dict) -> dict:
    """Make pre-validator candidate artifacts safe without guessing their intended target."""
    normalized = dict(candidate)
    uncertainty = [str(value) for value in normalized.get("uncertainty", [])]
    resolution = normalized.get("resolution")
    matched = normalized.get("matched_concept_id")
    if resolution == "match" and not matched:
        normalized["resolution"] = "ambiguous"
        uncertainty.append("Legacy match resolution had no target and requires Codex adjudication.")
    elif resolution != "match" and matched is not None:
        normalized["matched_concept_id"] = None
        uncertainty.append(
            "Legacy candidate supplied a target for a non-match resolution; the target was cleared."
        )
    normalized["uncertainty"] = list(dict.fromkeys(uncertainty))
    return normalized


def build_review_queue(
    derived_dir: Path, queue_path: Path, reviewed_concepts: list[Concept] | None = None
) -> int:
    queue: list[dict] = []
    reviewed_concepts = reviewed_concepts or []
    existing_items: dict[tuple[str, str, str], dict] = {}
    existing_ids: set[tuple[str, str]] = set()
    if queue_path.exists():
        existing_queue = read_yaml(queue_path) or {}
        for item in existing_queue.get("items", []):
            identity = (item.get("video_id", ""), item.get("candidate", {}).get("candidate_id", ""))
            if not all(identity):
                continue
            existing_hash = item.get("candidate_hash")
            if isinstance(existing_hash, dict):
                existing_hash = existing_hash.get("sha256")
            if not isinstance(existing_hash, str) or not existing_hash:
                existing_hash = sha256_json(item.get("candidate", {}))
            existing_items[(*identity, existing_hash.removeprefix("sha256:"))] = item
            existing_ids.add(identity)
    for path in sorted(derived_dir.glob("*.candidates.json")):
        payload = read_json(path)
        response_payload = dict(payload["response"])
        response_payload["concepts"] = [
            _normalize_legacy_candidate_resolution(candidate)
            for candidate in response_payload.get("concepts", [])
        ]
        response = ExtractionResponse.model_validate(response_payload)
        for concept in response.concepts:
            candidate_payload = concept.model_dump(mode="json")
            candidate_hash = sha256_json(candidate_payload).removeprefix("sha256:")
            item = {
                "video_id": payload["video_id"],
                "candidate": candidate_payload,
                "candidate_hash": candidate_hash,
                "decision": "pending",
                "canonical_concept_id": None,
                "review_notes": "",
            }
            identity = (payload["video_id"], concept.candidate_id)
            existing = existing_items.get((*identity, candidate_hash))
            if existing:
                item["candidate"] = existing.get("candidate", candidate_payload)
                item["candidate_hash"] = existing.get("candidate_hash", candidate_hash)
                item.update(
                    decision=existing.get("decision", item["decision"]),
                    canonical_concept_id=existing.get(
                        "canonical_concept_id", item["canonical_concept_id"]
                    ),
                    review_notes=existing.get("review_notes", ""),
                )
                for key in (
                    "adjudication_attempts",
                    "adjudication_method",
                    "adjudication_reason",
                    "adjudication_provenance",
                    "adjudicated_segment_ids",
                    "last_adjudicated_at",
                    "manual_review_history",
                ):
                    if key in existing:
                        item[key] = existing[key]
            elif identity in existing_ids:
                item["review_notes"] = "Candidate content changed; previous decision requires review."
            queue.append(item)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8") as handle:
        roundtrip_yaml.dump({"items": queue}, handle)
    return len(queue)


def _candidate_source_span(
    video: Video, segment_ids: list[str]
) -> BoundaryAssessment | None:
    """Assess a proposed span while reporting, never hiding, discarded clusters."""
    return assess_boundary(video, segment_ids)


def _candidate_context_segments(
    video: Video, candidate: dict, *, context_rows: int = 2
) -> list[Segment]:
    if not video.transcript:
        return []
    cited_ids = {
        str(segment_id)
        for evidence in candidate.get("evidence", [])
        for segment_id in evidence.get("segment_ids", [])
    }
    indices = [
        index
        for index, segment in enumerate(video.transcript.segments)
        if segment.id in cited_ids
    ]
    selected: set[int] = set()
    for index in indices:
        selected.update(
            range(
                max(0, index - context_rows),
                min(len(video.transcript.segments), index + context_rows + 1),
            )
        )
    return [video.transcript.segments[index] for index in sorted(selected)]


def _candidate_concept_options(
    candidate: dict, concepts: list[Concept], *, limit: int = 20
) -> list[dict]:
    label = str(candidate.get("canonical_label") or "")
    ranked = sorted(
        concepts,
        key=lambda concept: max(
            token_set_ratio(label, name) for name in [concept.label, *concept.aliases]
        ),
        reverse=True,
    )
    matched = str(candidate.get("matched_concept_id") or "")
    selected = ranked[:limit]
    if matched:
        explicit = next((concept for concept in concepts if concept.id == matched), None)
        if explicit and explicit not in selected:
            selected = [explicit, *selected[: max(0, limit - 1)]]
    return [
        {
            "id": concept.id,
            "label": concept.label,
            "aliases": concept.aliases,
            "definition": concept.short_definition,
            "concept_type": concept.concept_type,
        }
        for concept in selected
    ]


def process_pending_candidates(
    queue_path: Path,
    concept_dir: Path,
    normalized_dir: Path,
    concepts: list[Concept],
    *,
    min_confidence: float = 0.85,
    retry_deferred: bool = False,
    max_adjudication_attempts: int = 2,
    max_candidates: int | None = None,
    video_ids: set[str] | None = None,
    processors_config: Path | None = None,
    audit_dir: Path | None = None,
    budget_path: Path | None = None,
    model_override: str | None = None,
    taxonomy: dict | None = None,
    adjudicator: Callable[
        [dict, list[Segment], list[dict]],
        tuple[CandidateAdjudicationResponse, dict],
    ]
    | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, int]:
    """Use Codex semantic adjudication plus deterministic publication invariants."""
    if budget_path and processing_is_paused(budget_path.parent):
        raise RuntimeError("Processing is paused for the published-content audit")
    def report_progress(event: str, **details: str | int | float | None) -> None:
        if progress_callback is None:
            return
        payload: dict[str, Any] = {
            "event": event,
            "at": datetime.now(UTC).isoformat(),
            **details,
        }
        try:
            progress_callback(payload)
        except Exception:
            # Observability must never change the processing result.
            pass

    current_progress: dict[str, Any] | None = None
    current_started = 0.0
    full_backlog_total = 0

    def count_full_backlog() -> int:
        retryable_decisions = (
            {None, "pending", "deferred", "human_review"}
            if retry_deferred
            else {None, "pending"}
        )
        return sum(
            item.get("decision") in retryable_decisions
            for item in queue.get("items", [])
        )

    def finish_progress(outcome: str) -> None:
        nonlocal current_progress
        if current_progress is None:
            return
        full_backlog_remaining = count_full_backlog()
        finished_progress = {
            **current_progress,
            "full_backlog_remaining": full_backlog_remaining,
        }
        report_progress(
            "candidate_finished",
            **finished_progress,
            outcome=outcome,
            elapsed_seconds=round(monotonic() - current_started, 1),
        )
        current_progress = None
        if counts["considered"] % ADJUDICATION_CHECKPOINT_SIZE == 0:
            persist_checkpoint()
            report_progress(
                "checkpoint",
                index=counts["considered"],
                total=total_selected,
                batch=(counts["considered"] // ADJUDICATION_CHECKPOINT_SIZE),
                batch_total=(
                    (total_selected + ADJUDICATION_CHECKPOINT_SIZE - 1)
                    // ADJUDICATION_CHECKPOINT_SIZE
                ),
                backlog_total=total_available,
                backlog_remaining=max(0, total_available - counts["considered"]),
                full_backlog_total=full_backlog_total,
                full_backlog_remaining=count_full_backlog(),
            )

    if adjudicator is None:
        if processors_config is None or audit_dir is None:
            raise ValueError("Codex adjudication requires processors_config and audit_dir")

        def adjudicator(
            candidate: dict, segments: list[Segment], options: list[dict]
        ) -> tuple[CandidateAdjudicationResponse, dict]:
            return adjudicate_candidate_with_codex(
                candidate,
                segments,
                options,
                taxonomy or {},
                processors_config,
                audit_dir,
                model_override=model_override,
                budget_path=budget_path,
                heartbeat_callback=lambda: report_progress(
                    "candidate_heartbeat",
                    index=(current_progress or {}).get("index"),
                    total=(current_progress or {}).get("total"),
                    backlog_total=(current_progress or {}).get("backlog_total"),
                    backlog_remaining=(current_progress or {}).get("backlog_remaining"),
                    full_backlog_total=(current_progress or {}).get("full_backlog_total"),
                    full_backlog_remaining=(current_progress or {}).get("full_backlog_remaining"),
                    video_id=str((current_progress or {}).get("video_id") or candidate.get("video_id") or "unknown"),
                    candidate_id=str(candidate.get("candidate_id") or "unknown"),
                    elapsed_seconds=round(monotonic() - current_started, 1),
                    status="waiting_for_codex",
                ),
            )

    queue = read_yaml(queue_path) or {"items": []}
    full_backlog_total = count_full_backlog()
    videos = {video.id: video for video in load_videos(normalized_dir)}
    concept_by_id = {concept.id: concept for concept in concepts}
    documents = {
        concept.id: roundtrip_yaml.load(
            (concept_dir / f"{concept.slug}.yaml").read_text(encoding="utf-8")
        )
        for concept in concepts
    }
    existing_evidence_ids = {
        evidence.id for concept in concepts for evidence in concept.evidence
    }
    existing_citations = {
        (concept.id, evidence.source.video_id, tuple(sorted(evidence.source.segment_ids)))
        for concept in concepts for evidence in concept.evidence
        if evidence.review_status == "approved"
    }
    dirty_concept_ids: set[str] = set()
    counts = {
        "accepted": 0,
        "deferred": 0,
        "human_review": 0,
        "rejected": 0,
        "evidence_added": 0,
        "concepts_added": 0,
        "concepts_restored": 0,
        "considered": 0,
    }

    def persist_checkpoint() -> None:
        for concept_id in dirty_concept_ids:
            document = documents[concept_id]
            temporary = concept_dir / f".{concept_by_id[concept_id].slug}.{os.getpid()}.yaml.tmp"
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                roundtrip_yaml.dump(document, handle)
            replace_with_retry(temporary, concept_dir / f"{concept_by_id[concept_id].slug}.yaml")
        queue_temporary = queue_path.with_name(f".{queue_path.name}.{os.getpid()}.tmp")
        with queue_temporary.open("w", encoding="utf-8", newline="") as handle:
            roundtrip_yaml.dump(queue, handle)
        replace_with_retry(queue_temporary, queue_path)
        dirty_concept_ids.clear()

    def defer(item: dict, reason: str, provenance: dict | None = None) -> None:
        attempts = int(item.get("adjudication_attempts") or 0)
        item["decision"] = "deferred"
        item["canonical_concept_id"] = None
        item["adjudication_method"] = "codex_cli_semantic_review_v1"
        item["adjudication_reason"] = reason
        item["last_adjudicated_at"] = datetime.now(UTC).isoformat()
        if provenance:
            item["adjudication_provenance"] = provenance
        suffix = (
            f" after {attempts} Codex checks" if attempts >= max_adjudication_attempts else ""
        )
        item["review_notes"] = f"Codex deferred{suffix}: {reason}"
        counts["deferred"] += 1
        finish_progress("deferred")

    def reject(item: dict, reason: str, provenance: dict | None = None) -> None:
        item["decision"] = "rejected"
        item["canonical_concept_id"] = None
        item["adjudication_method"] = (
            "codex_cli_semantic_review_v1" if provenance else "deterministic_precheck_v3"
        )
        item["adjudication_reason"] = reason
        item["last_adjudicated_at"] = datetime.now(UTC).isoformat()
        if provenance:
            item["adjudication_provenance"] = provenance
        item["review_notes"] = f"Rejected by source-grounded adjudication: {reason}"
        counts["rejected"] += 1
        finish_progress("rejected")

    eligible_items = []
    for item in queue.get("items", []):
        if video_ids is not None and str(item.get("video_id") or "") not in video_ids:
            continue
        if item.get("decision") != "pending" and not (
            retry_deferred and item.get("decision") in {"deferred", "human_review"}
        ):
            continue
        eligible_items.append(item)

    total_available = len(eligible_items)
    eligible_items.sort(key=lambda item: (
        int(item.get("adjudication_attempts") or 0),
        item.get("last_adjudicated_at") or "",
    ))
    selected_items = (
        eligible_items if max_candidates is None else eligible_items[:max_candidates]
    )
    total_selected = len(selected_items)
    for position, item in enumerate(selected_items, start=1):
        counts["considered"] += 1
        item["adjudication_attempts"] = int(item.get("adjudication_attempts") or 0) + 1
        candidate = dict(item.get("candidate") or {})
        if item.get("manual_review_history") and item.get("review_notes"):
            candidate["editorial_advice"] = item["review_notes"]
        video_id = item.get("video_id")
        candidate_id = str(candidate.get("candidate_id") or "unknown")
        current_started = monotonic()
        current_progress = {
            "index": position,
            "total": total_selected,
            "backlog_total": total_available,
            "backlog_remaining": max(0, total_available - position),
            "full_backlog_total": full_backlog_total,
            "full_backlog_remaining": count_full_backlog(),
            "video_id": str(video_id or "unknown"),
            "candidate_id": candidate_id,
            "attempt": item["adjudication_attempts"],
        }
        report_progress("candidate_started", **current_progress, status="preparing")
        video = videos.get(video_id)
        if not video:
            reject(item, "The candidate has no normalized source video.")
            continue
        context_segments = _candidate_context_segments(video, candidate)
        if not context_segments:
            reject(item, "The candidate cites no valid normalized transcript rows.")
            continue
        options = _candidate_concept_options(candidate, concepts)
        try:
            decision, provenance = adjudicator(candidate, context_segments, options)
        except CodexResponseError as error:
            defer(
                item,
                "Codex returned a response that failed schema validation; retryable: "
                + str(error),
                error.provenance,
            )
            continue
        except CodexTimeoutError as error:
            defer(
                item,
                f"Codex adjudication timed out after {error.timeout_seconds} seconds; retryable.",
                error.provenance,
            )
            continue
        except Exception as error:
            report_progress(
                "candidate_error",
                **current_progress,
                error_type=type(error).__name__,
                elapsed_seconds=round(monotonic() - current_started, 1),
            )
            raise
        if decision.decision == "reject":
            reject(item, decision.reason, provenance)
            continue
        if decision.decision == "defer":
            defer(item, decision.reason, provenance)
            continue
        if decision.confidence < min_confidence:
            defer(
                item,
                f"Codex confidence {decision.confidence:.2f} is below {min_confidence:.2f}: "
                f"{decision.reason}",
                provenance,
            )
            continue
        allowed_ids = {segment.id for segment in context_segments}
        if any(segment_id not in allowed_ids for segment_id in decision.segment_ids):
            reject(item, "Codex cited a segment outside the supplied context.", provenance)
            continue
        span = _candidate_source_span(video, decision.segment_ids)
        if not span:
            reject(item, "Codex selected no valid normalized transcript span.", provenance)
            continue
        if span.dropped_segment_ids:
            defer(
                item,
                "Codex selected dispersed support; no cited cluster was discarded: "
                + ", ".join(span.dropped_segment_ids),
                provenance,
            )
            continue
        if span.needs_context:
            defer(
                item,
                "Codex-selected span failed deterministic boundary checks; "
                f"flags={','.join(span.flags)}; {span.reason}",
                provenance,
            )
            continue
        selected_rows = [segment.model_dump(mode="json") for segment in context_segments
                         if segment.id in span.segment_ids]
        target = concept_by_id.get(decision.canonical_concept_id)
        units = {
            "evidence:0:new": {
                "value": {"excerpt": decision.excerpt, "reason": decision.reason},
                "allowed_segment_ids": list(span.segment_ids),
            },
        }
        if decision.decision == "create_new":
            units.update({
                "field:label": {"value": decision.canonical_label, "allowed_segment_ids": list(span.segment_ids)},
                "field:short_definition": {"value": decision.definition, "allowed_segment_ids": list(span.segment_ids)},
                "field:facets": {"value": {facet.name: facet.values for facet in decision.facets},
                                 "allowed_segment_ids": list(span.segment_ids)},
                "field:concept_type": {"value": decision.concept_type,
                                       "allowed_segment_ids": list(span.segment_ids)},
            })
        elif target and target.review_status != "approved":
            if any(relation.review_status == "approved" for relation in target.relations):
                defer(item, "Quarantined article relations need full article review before restoration.", provenance)
                continue
            units.update({f"field:{field}": {"value": getattr(target, field),
                                             "allowed_segment_ids": list(span.segment_ids)}
                          for field in ("label", "aliases", "short_definition", "detailed_definition",
                                        "evidence_summary", "concept_type", "facets", "difficulty") if getattr(target, field) is not None})
        try:
            verification, verification_provenance = verify_article_with_codex({
                "article": {"id": decision.canonical_concept_id, "label": target.label if target else decision.canonical_label,
                            "short_definition": target.short_definition if target else decision.definition,
                            "concept_type": target.concept_type if target else decision.concept_type},
                "units": units, "selected_rows": selected_rows,
                "context_rows": [segment.model_dump(mode="json") for segment in context_segments
                                 if segment.id not in span.segment_ids],
                "source_metadata": {video.id: {"duration_ms": video.duration_ms}},
                "facet_meanings": (taxonomy or {}).get("facet_meanings", {}),
            }, processors_config, audit_dir, budget_path, heartbeat_callback=lambda details=dict(current_progress or {}), began=current_started: report_progress(
                "candidate_heartbeat", **{**details, "status": "waiting_for_support_verification",
                                          "elapsed_seconds": round(monotonic() - began, 1)}))
        except LLMBudgetExceeded as error:
            defer(item, f"Independent support verification budget deferred: {error}", provenance)
            break
        except (CodexError, ValueError) as error:
            defer(item, f"Independent support verification failed: {error}", provenance)
            continue
        if any(unit["status"] != "supported" for unit in verification["units"]):
            defer(item, "Independent support verification found unresolved support: "
                  + "; ".join(unit["note"] for unit in verification["units"] if unit["status"] != "supported"), provenance)
            continue
        provenance = {**provenance, "support_verification": verification_provenance}
        created_new = decision.decision == "create_new"
        target_id = decision.canonical_concept_id
        if decision.decision == "accept_existing" and target_id not in concept_by_id:
            reject(item, "Codex selected an unknown canonical concept ID.", provenance)
            continue
        if created_new:
            label = str(decision.canonical_label).strip()
            definition = str(decision.definition).strip()
            if len(label) < 3 or len(definition) < 40:
                defer(item, "Codex new-concept wording is not sufficiently specific.", provenance)
                continue
            allowed_facets = (taxonomy or {}).get("facets", {})
            invalid_facets = [
                f"{facet.name}={value}"
                for facet in decision.facets
                for value in facet.values
                if facet.name not in allowed_facets
                or value not in set(allowed_facets.get(facet.name, []))
            ]
            if invalid_facets:
                defer(
                    item,
                    "Codex new-concept facets are outside the configured taxonomy: "
                    + ", ".join(invalid_facets),
                    provenance,
                )
                continue
            base_slug = slugify(label) or f"concept-{video_id.lower()}"
            slug = base_slug
            suffix = 2
            while (concept_dir / f"{slug}.yaml").exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            target_id = f"concept-{slug}"
            document = {
                "id": target_id,
                "slug": slug,
                "label": label,
                "aliases": [],
                "short_definition": definition,
                "concept_type": str(decision.concept_type),
                "facets": {
                    str(facet.get("name")): [str(value) for value in facet.get("values", [])]
                    for facet in (item.model_dump(mode="json") for item in decision.facets)
                    if facet.get("name")
                },
                "difficulty": None,
                "review_status": "approved",
                "generated_by": {
                    "processor": "codex_semantic_adjudication",
                    "version": "1.0.0",
                    "input_hash": str(provenance.get("input_hash") or item.get("candidate_hash", "")),
                    "model": provenance.get("model"),
                    "reasoning_effort": provenance.get("reasoning_effort"),
                    "prompt_version": provenance.get("prompt_version"),
                    "schema_version": provenance.get("schema_version"),
                },
                "evidence": [],
            }
            documents[target_id] = document
            counts["concepts_added"] += 1
        elif documents[target_id].get("review_status") != "approved":
            # A quarantined legacy concept may return to the public corpus only
            # after Codex independently accepts its canonical topic. Older
            # heuristic evidence remains unreviewed and unpublished.
            documents[target_id]["review_status"] = "approved"
            documents[target_id]["generated_by"] = {
                "processor": "codex_semantic_adjudication",
                "version": "1.0.0",
                "input_hash": str(
                    provenance.get("input_hash") or item.get("candidate_hash", "")
                ),
                "model": provenance.get("model"),
                "reasoning_effort": provenance.get("reasoning_effort"),
                "prompt_version": provenance.get("prompt_version"),
                "schema_version": provenance.get("schema_version"),
            }
            counts["concepts_restored"] += 1
        selected_ids = list(span.segment_ids)
        start_ms, end_ms = span.start_ms, span.end_ms
        citation = (target_id, video_id, tuple(sorted(selected_ids)))
        evidence_id = f"{video_id}-{candidate.get('candidate_id')}-codex-reviewed"
        if evidence_id in existing_evidence_ids:
            evidence_id = (
                f"{evidence_id}-{sha256_json([target_id, selected_ids]).removeprefix('sha256:')[:8]}"
            )
        if citation not in existing_citations and evidence_id not in existing_evidence_ids:
            evidence = {
                "id": evidence_id,
                "evidence_type": decision.evidence_type,
                "excerpt": str(decision.excerpt).strip(),
                "reason": decision.reason.strip(),
                "confidence": decision.confidence,
                "visual_status": (
                    "transcript_inferred"
                    if any(
                        evidence.get("visual_status") in {"transcript_inferred", "verified_visual_demo"}
                        for evidence in candidate.get("evidence", [])
                    )
                    else "not_visual"
                ),
                "review_status": "approved",
                "source": {
                    "video_id": video_id,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "url": youtube_url(video_id, start_ms),
                    "segment_ids": selected_ids,
                },
            }
            documents[target_id].setdefault("evidence", []).append(evidence)
            existing_evidence_ids.add(evidence_id)
            existing_citations.add(citation)
            counts["evidence_added"] += 1
        if created_new:
            concepts.append(Concept.model_validate(documents[target_id]))
            concept_by_id[target_id] = concepts[-1]
        item["decision"] = "accepted"
        item["canonical_concept_id"] = target_id
        item["adjudicated_segment_ids"] = selected_ids
        item["adjudication_method"] = "codex_cli_semantic_review_v1"
        item["adjudication_reason"] = decision.reason
        item["adjudication_provenance"] = provenance
        item["last_adjudicated_at"] = datetime.now(UTC).isoformat()
        item["review_notes"] = (
            "Codex semantic adjudication accepted one exact contiguous transcript moment; "
            "optional human input remains advisory metadata or an explicit override."
        )
        dirty_concept_ids.add(target_id)
        counts["accepted"] += 1
        finish_progress("accepted")
    # Full batches already persisted the queue and changed concepts.
    if counts["considered"] % ADJUDICATION_CHECKPOINT_SIZE:
        persist_checkpoint()
    return counts


def validate_graph(concepts: list[Concept]) -> list[str]:
    errors: list[str] = []
    known = {concept.id for concept in concepts}
    graph = nx.DiGraph()
    graph.add_nodes_from(known)
    for concept in concepts:
        for relation in concept.relations:
            if relation.review_status != "approved":
                continue
            if relation.target_concept_id not in known:
                errors.append(f"{concept.id}: unknown relation target {relation.target_concept_id}")
            if relation.relation_type == "prerequisite_of":
                graph.add_edge(concept.id, relation.target_concept_id)
    try:
        cycle = nx.find_cycle(graph)
        if cycle:
            errors.append(f"prerequisite cycle: {cycle}")
    except nx.NetworkXNoCycle:
        pass
    return errors


def repair_source_envelopes(concept_dir: Path, videos: list[Video]) -> dict[str, int]:
    """Expand spoken source bounds only enough to enclose every cited segment."""
    segment_map = {
        segment.id: (segment, video.duration_ms)
        for video in videos
        if video.transcript
        for segment in video.transcript.segments
    }
    changed_files = changed_evidence = blocked = 0
    for path in sorted(concept_dir.glob("*.yaml")):
        document = roundtrip_yaml.load(path.read_text(encoding="utf-8"))
        changed = False
        for evidence in document.get("evidence", []):
            source = evidence.get("source") or {}
            cited_records = [
                segment_map[segment_id]
                for segment_id in source.get("segment_ids", [])
                if segment_id in segment_map
            ]
            if not cited_records:
                continue
            cited = [record[0] for record in cited_records]
            duration_ms = next((record[1] for record in cited_records if record[1]), 0)
            if caption_duration_conflicts(duration_ms, cited):
                blocked += 1
                continue
            start_ms = min(
                int(source.get("start_ms", cited[0].start_ms)),
                *(item.start_ms for item in cited),
            )
            cited_end_ms = max(item.end_ms for item in cited)
            if duration_ms:
                cited_end_ms = min(cited_end_ms, duration_ms)
            current_end_ms = int(source.get("end_ms", cited_end_ms))
            if duration_ms:
                current_end_ms = min(current_end_ms, duration_ms)
            end_ms = max(current_end_ms, cited_end_ms)
            if end_ms - start_ms > MAX_SPOKEN_SOURCE_MS:
                blocked += 1
                continue
            if start_ms == source.get("start_ms") and end_ms == source.get("end_ms"):
                continue
            source["start_ms"] = start_ms
            source["end_ms"] = end_ms
            source["url"] = youtube_url(str(source["video_id"]), start_ms)
            changed = True
            changed_evidence += 1
        if changed:
            temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                roundtrip_yaml.dump(document, handle)
            replace_with_retry(temporary, path)
            changed_files += 1
    return {"files": changed_files, "evidence": changed_evidence, "blocked": blocked}


def quarantine_legacy_automatic_promotions(
    queue_path: Path, concept_dir: Path
) -> dict[str, int]:
    """Return heuristic promotions to the Codex queue without deleting their audit trail."""
    queue = read_yaml(queue_path) or {"items": []}
    documents = {
        path: roundtrip_yaml.load(path.read_text(encoding="utf-8"))
        for path in sorted(concept_dir.glob("*.yaml"))
    }
    evidence_index: dict[str, tuple[Path, dict]] = {}
    for path, document in documents.items():
        for evidence in document.get("evidence", []):
            evidence_index[str(evidence.get("id") or "")] = (path, evidence)
    changed_paths: set[Path] = set()
    requeued = quarantined_evidence = quarantined_concepts = 0
    automatic_concept_ids = {
        str(document.get("id"))
        for document in documents.values()
        if (document.get("generated_by") or {}).get("processor")
        == "automatic_candidate_review"
    }
    for path, document in documents.items():
        if str(document.get("id")) not in automatic_concept_ids:
            continue
        for evidence in document.get("evidence", []):
            if evidence.get("review_status", "approved") == "approved":
                evidence["review_status"] = "unreviewed"
                quarantined_evidence += 1
                changed_paths.add(path)
    for item in queue.get("items", []):
        if item.get("decision") == "human_review":
            item["decision"] = "deferred"
            item["canonical_concept_id"] = None
            item["adjudication_method"] = "legacy_human_queue_migration_v1"
            item["adjudication_reason"] = (
                "Returned to the default Codex CLI workflow; human input is optional advice."
            )
            item["review_notes"] = (
                "Queued for Codex semantic adjudication; a person may optionally annotate or override."
            )
            item["last_adjudicated_at"] = datetime.now(UTC).isoformat()
            requeued += 1
            continue
        if item.get("decision") != "accepted":
            continue
        video_id = str(item.get("video_id") or "")
        candidate_id = str((item.get("candidate") or {}).get("candidate_id") or "")
        prefix = f"{video_id}-{candidate_id}-reviewed"
        matches = [
            (path, evidence)
            for evidence_id, (path, evidence) in evidence_index.items()
            if evidence_id == prefix or evidence_id.startswith(prefix + "-")
        ]
        if not matches and item.get("canonical_concept_id") not in automatic_concept_ids:
            continue
        for path, evidence in matches:
            if evidence.get("review_status", "approved") != "unreviewed":
                evidence["review_status"] = "unreviewed"
                quarantined_evidence += 1
                changed_paths.add(path)
        item["decision"] = "deferred"
        item["canonical_concept_id"] = None
        item["adjudication_method"] = "legacy_heuristic_quarantine_v1"
        item["adjudication_reason"] = (
            "Legacy heuristic promotion requires Codex semantic adjudication against the exact span."
        )
        item["review_notes"] = (
            "Queued for Codex CLI; optional human input is advisory and not required."
        )
        item["last_adjudicated_at"] = datetime.now(UTC).isoformat()
        requeued += 1
    for path, document in documents.items():
        if str(document.get("id")) not in automatic_concept_ids:
            continue
        if any(
            evidence.get("review_status", "approved") == "approved"
            for evidence in document.get("evidence", [])
        ):
            continue
        if document.get("review_status", "approved") != "unreviewed":
            document["review_status"] = "unreviewed"
            quarantined_concepts += 1
            changed_paths.add(path)
    for path in changed_paths:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            roundtrip_yaml.dump(documents[path], handle)
        replace_with_retry(temporary, path)
    queue_temporary = queue_path.with_name(f".{queue_path.name}.{os.getpid()}.tmp")
    with queue_temporary.open("w", encoding="utf-8", newline="") as handle:
        roundtrip_yaml.dump(queue, handle)
    replace_with_retry(queue_temporary, queue_path)
    return {
        "requeued": requeued,
        "evidence": quarantined_evidence,
        "concepts": quarantined_concepts,
    }


def candidate_citation_ids(item: dict) -> set[str]:
    """Citations retained by extraction or by the later reviewed adjudication."""
    return {
        str(segment_id)
        for evidence in (item.get("candidate") or {}).get("evidence", [])
        for segment_id in evidence.get("segment_ids", [])
    } | {str(segment_id) for segment_id in item.get("adjudicated_segment_ids", [])}


def validate_review_queue(
    queue_data: dict,
    concepts: list[Concept],
    *,
    ignored_video_ids: set[str] | None = None,
) -> list[str]:
    """Ensure accepted queue items are represented by their exact cited evidence."""
    errors: list[str] = []
    concept_map = {concept.id: concept for concept in concepts}
    ignored_video_ids = ignored_video_ids or set()
    for index, item in enumerate(queue_data.get("items", []), start=1):
        if item.get("decision") != "accepted":
            continue
        if item.get("video_id") in ignored_video_ids:
            continue
        canonical_id = item.get("canonical_concept_id")
        canonical = concept_map.get(canonical_id)
        if not canonical:
            errors.append(f"review-queue/{index}: accepted item has unknown canonical concept")
            continue
        candidate_segments = candidate_citation_ids(item)
        canonical_segments = {
            segment_id
            for evidence in canonical.evidence
            if evidence.source.video_id == item.get("video_id")
            for segment_id in evidence.source.segment_ids
        }
        if not candidate_segments.intersection(canonical_segments):
            errors.append(
                f"review-queue/{index}: accepted item has no cited segment in {canonical_id}"
            )
    return errors


def validate_navigation(
    navigation: KnowledgeNavigation, concepts: list[Concept]
) -> list[str]:
    errors: list[str] = []
    known = {concept.id for concept in concepts}
    referenced: set[str] = set()

    def check_nodes(nodes) -> None:
        for node in nodes:
            for concept_id in node.concept_ids:
                if concept_id not in known:
                    errors.append(f"navigation/{node.id}: unknown concept {concept_id}")
                referenced.add(concept_id)
            check_nodes(node.children)

    check_nodes(navigation.sections)
    for concept in concepts:
        if concept.id not in referenced and not (
            concept.generated_by and concept.generated_by.processor == "automatic_candidate_review"
        ):
            errors.append(f"navigation: approved concept is not placed: {concept.id}")
    return errors


def auto_place_generated_concepts(navigation: dict, concepts: list[Concept]) -> dict[str, int]:
    """Place generated concepts only when the navigation match is unambiguous.

    Navigation is editorial structure, so a weak keyword match must not silently
    choose a deep shot branch. Concepts without a strong, clearly better match
    go to the explicit editorial holding node instead.
    """
    nodes: list[dict] = []

    def collect(items: list[dict]) -> None:
        for node in items:
            nodes.append(node)
            collect(node.get("children", []))

    collect(navigation.get("sections", []))
    referenced = {item for node in nodes for item in node.get("concept_ids", [])}
    holding = next(
        (node for node in nodes if node.get("id") == "editorial-placement-review"),
        None,
    )
    keywords = {
        "serve-receive": ("receive", "flick", "serve receive"),
        "serve": ("serve", "spin serve"),
        "flick": ("flick", "flip", "over-table"),
        "block": ("block", "defensive"),
        "loop": ("loop", "topspin", "backspin"),
        "push": ("push", "chop"),
        "training": ("drill", "practice", "training"),
        "strategy": ("tactic", "selection", "placement"),
        "fundamentals": ("contact", "spin", "racket", "footwork"),
    }
    placed = skipped = holding_count = 0
    for concept in concepts:
        if concept.id in referenced or not (
            concept.generated_by
            and concept.generated_by.processor
            in ("automatic_candidate_review", "codex_semantic_adjudication")
        ):
            continue
        # Use all available editorial context. The summary may be generated in
        # a later stage, so placement must also work from the evidence already
        # attached to a newly accepted concept.
        text = " ".join(
            filter(
                None,
                [
                    concept.label,
                    *getattr(concept, "aliases", []),
                    concept.short_definition,
                    concept.evidence_summary or "",
                    concept.concept_type,
                    *(
                        part
                        for name, values in getattr(concept, "facets", {}).items()
                        for part in [name, *values]
                    ),
                    *(
                        evidence.excerpt
                        for evidence in getattr(concept, "evidence", [])
                    ),
                    *(
                        evidence.reason
                        for evidence in getattr(concept, "evidence", [])
                    ),
                ],
            )
        ).lower()
        ranked: list[tuple[int, dict]] = []
        for node in nodes:
            if node is holding:
                continue
            node_text = " ".join([node.get("id", ""), node.get("label", ""), node.get("description", "")]).lower()
            score = sum(1 for word in text.split() if len(word) > 4 and word in node_text)
            label_words = [word for word in re.findall(r"[a-z0-9]+", node.get("label", "").lower()) if len(word) > 3]
            score += sum(8 for word in label_words if word in text)
            for key, terms in keywords.items():
                if key in node.get("id", ""):
                    score += sum(3 for term in terms if term in text)
            ranked.append((score, node))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best_score, best = ranked[0] if ranked else (0, None)
        runner_up = ranked[1][0] if len(ranked) > 1 else 0
        if best is None or best_score < 8 or best_score - runner_up < 2:
            if holding is None:
                skipped += 1
            else:
                holding.setdefault("concept_ids", []).append(concept.id)
                referenced.add(concept.id)
                placed += 1
                holding_count += 1
        else:
            best.setdefault("concept_ids", []).append(concept.id)
            referenced.add(concept.id)
            placed += 1
    return {"placed": placed, "skipped": skipped, "holding": holding_count}


def validate_source_span(
    source: SourceSpan,
    video: Video,
    segment_map: dict[str, tuple[str, Segment]],
    *,
    require_transcript_segments: bool,
) -> list[str]:
    """Apply the same citation contract to evidence and relation claims."""
    errors: list[str] = []
    if video.duration_ms and source.end_ms > video.duration_ms:
        errors.append("source ends after video duration")
    if require_transcript_segments:
        missing = [item for item in source.segment_ids if item not in segment_map]
        if missing:
            errors.append(f"missing segments {missing}")
    mismatched = [
        item for item in source.segment_ids
        if item in segment_map and segment_map[item][0] != source.video_id
    ]
    if mismatched:
        errors.append(f"segments belong to another video {mismatched}")
    if source.end_ms - source.start_ms > MAX_SPOKEN_SOURCE_MS:
        errors.append(f"spoken source exceeds {MAX_SPOKEN_SOURCE_MS // 1000} seconds")
    cited = sorted(
        (segment_map[item][1] for item in source.segment_ids if item in segment_map),
        key=lambda segment: segment.start_ms,
    )
    if cited:
        if caption_duration_conflicts(video.duration_ms, cited):
            errors.append("selected caption ends after video duration; reconcile metadata/caption timing")
        if source.start_ms > cited[0].start_ms:
            errors.append("source starts after its first cited segment")
        cited_end_ms = max(segment.end_ms for segment in cited)
        if video.duration_ms:
            cited_end_ms = min(cited_end_ms, video.duration_ms)
        if source.end_ms < cited_end_ms:
            errors.append("source ends before its last cited segment")
    for previous, current in zip(cited, cited[1:], strict=False):
        gap_ms = current.start_ms - previous.end_ms
        if gap_ms > MAX_CITED_SEGMENT_GAP_MS:
            errors.append(f"cited segments have a {gap_ms / 1000:g}-second gap")
    if source.url != youtube_url(source.video_id, source.start_ms):
        errors.append("noncanonical source URL")
    return errors


def validate_corpus(
    concepts: list[Concept], videos: list[Video], *, require_transcript_segments: bool = True
) -> list[str]:
    concepts = [concept for concept in concepts if concept.review_status == "approved"]
    errors = validate_graph(concepts)
    video_map = {video.id: video for video in videos}
    segment_map = {
        segment.id: (video.id, segment)
        for video in videos
        if video.transcript
        for segment in video.transcript.segments
    }
    slugs: set[str] = set()
    ids: set[str] = set()
    for concept in concepts:
        if concept.id in ids:
            errors.append(f"duplicate concept id: {concept.id}")
        ids.add(concept.id)
        if concept.slug in slugs:
            errors.append(f"duplicate concept slug: {concept.slug}")
        slugs.add(concept.slug)
        citations: set[tuple] = set()
        for evidence in concept.evidence:
            if evidence.review_status != "approved":
                continue
            source = evidence.source
            visual = evidence.visual_source
            citation = (
                source.video_id, tuple(sorted(source.segment_ids)),
                (visual.video_id, visual.start_ms, visual.end_ms) if visual else None,
            )
            if citation in citations:
                errors.append(f"{concept.id}/{evidence.id}: duplicate spoken citation and visual window")
            citations.add(citation)
            video = video_map.get(source.video_id)
            if not video:
                errors.append(f"{concept.id}/{evidence.id}: unknown video {source.video_id}")
                continue
            errors.extend(
                f"{concept.id}/{evidence.id}: {error}"
                for error in validate_source_span(
                    source, video, segment_map,
                    require_transcript_segments=require_transcript_segments,
                )
            )
            if (
                evidence.spoken_context_start_ms is not None
                and evidence.spoken_context_start_ms > source.start_ms
            ):
                errors.append(
                    f"{concept.id}/{evidence.id}: spoken context starts after source"
                )
            if (
                evidence.spoken_context_end_ms
                and video.duration_ms
                and evidence.spoken_context_end_ms > video.duration_ms
            ):
                errors.append(f"{concept.id}/{evidence.id}: spoken context ends after video duration")
            visual = evidence.visual_source
            if visual:
                visual_video = video_map.get(visual.video_id)
                if not visual_video:
                    errors.append(
                        f"{concept.id}/{evidence.id}: unknown visual video {visual.video_id}"
                    )
                elif visual_video.duration_ms and visual.end_ms > visual_video.duration_ms:
                    errors.append(
                        f"{concept.id}/{evidence.id}: visual source ends after video duration"
                    )
                if visual.url != youtube_url(visual.video_id, visual.start_ms):
                    errors.append(
                        f"{concept.id}/{evidence.id}: noncanonical visual source URL"
                    )
                if (
                    visual.selection_method == "manual_review"
                    and evidence.visual_status != "verified_visual_demo"
                ):
                    errors.append(
                        f"{concept.id}/{evidence.id}: manually reviewed visual is not verified"
                    )
                if (
                    visual.selection_method == "nearby_visual_inference"
                    and evidence.visual_status == "verified_visual_demo"
                ):
                    errors.append(
                        f"{concept.id}/{evidence.id}: inferred visual cannot be verified"
                    )
            elif evidence.visual_status == "verified_visual_demo":
                errors.append(
                    f"{concept.id}/{evidence.id}: verified visual has no visual source"
                )
        for relation in concept.relations:
            if relation.review_status != "approved":
                continue
            prefix = f"{concept.id}/relation/{relation.target_concept_id}"
            if not relation.sources:
                errors.append(f"{prefix}: approved relation has no source")
            for source in relation.sources:
                video = video_map.get(source.video_id)
                if video is None:
                    errors.append(f"{prefix}: unknown video {source.video_id}")
                    continue
                errors.extend(
                    f"{prefix}: {error}"
                    for error in validate_source_span(
                        source, video, segment_map,
                        require_transcript_segments=require_transcript_segments,
                    )
                )
    return errors


def validate_published_corpus(corpus: PublishCorpus) -> list[str]:
    """Validate the sanitized artifact without requiring private transcripts."""
    errors = validate_corpus(
        corpus.concepts, corpus.videos, require_transcript_segments=False
    )
    for video in corpus.videos:
        if video.transcript is not None:
            errors.append(f"{video.id}: published video contains a private transcript")
    for concept in corpus.concepts:
        if concept.review_status != "approved":
            errors.append(f"{concept.id}: published concept is not approved")
        if any(item.review_status != "approved" for item in concept.evidence):
            errors.append(f"{concept.id}: published evidence is not approved")
        if any(item.review_status != "approved" for item in concept.relations):
            errors.append(f"{concept.id}: published relation is not approved")
    if corpus.navigation:
        errors.extend(validate_navigation(corpus.navigation, corpus.concepts))
    errors.extend(validate_text_encoding(corpus.model_dump(mode="json")))
    return errors


def validate_text_encoding(value, path: str = "corpus") -> list[str]:
    """Find common UTF-8/Windows-1252 mojibake in public strings."""
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            errors.extend(validate_text_encoding(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(validate_text_encoding(item, f"{path}[{index}]"))
    elif isinstance(value, str) and any(marker in value for marker in MOJIBAKE_MARKERS):
        errors.append(f"{path}: possible encoding corruption")
    return errors


def build_quality_report(corpus: PublishCorpus, queue_data: dict | None = None) -> dict:
    """Return editorial quality metrics without treating warnings as validity errors."""
    evidence = [item for concept in corpus.concepts for item in concept.evidence]
    source_counts = {
        concept.id: len({item.source.video_id for item in concept.evidence})
        for concept in corpus.concepts
    }
    excerpt_counts = Counter(item.excerpt for item in evidence)
    visual_methods = Counter(
        item.visual_source.selection_method
        for item in evidence
        if item.visual_source is not None
    )
    related_ids = {
        concept_id
        for concept in corpus.concepts
        for concept_id in (
            [concept.id, *(relation.target_concept_id for relation in concept.relations)]
            if concept.relations
            else []
        )
    }
    queue_items = (queue_data or {}).get("items", [])
    queue_decisions = Counter(str(item.get("decision") or "pending") for item in queue_items)
    awaiting_codex = [
        item
        for item in queue_items
        if item.get("decision") in {"pending", "deferred", "human_review"}
    ]
    return {
        "concept_count": len(corpus.concepts),
        "published_video_count": len(corpus.videos),
        "evidence_count": len(evidence),
        "distinct_excerpt_count": len(excerpt_counts),
        "moments_with_repeated_excerpt": sum(
            count for count in excerpt_counts.values() if count > 1
        ),
        "concepts_without_relations": sorted(
            concept.id for concept in corpus.concepts if concept.id not in related_ids
        ),
        "single_source_concepts": sorted(
            concept_id for concept_id, count in source_counts.items() if count == 1
        ),
        "evidence_outliers": [
            {"concept_id": concept.id, "label": concept.label, "evidence_count": len(concept.evidence)}
            for concept in sorted(corpus.concepts, key=lambda item: len(item.evidence), reverse=True)
            if len(concept.evidence) > 30
        ],
        "visual_sources": dict(sorted(visual_methods.items())),
        "verified_visual_count": sum(
            item.visual_status == "verified_visual_demo" for item in evidence
        ),
        "pending_candidate_count": queue_decisions["pending"],
        "awaiting_codex_adjudication_count": len(awaiting_codex),
        "candidate_decisions": dict(sorted(queue_decisions.items())),
        "pending_by_video": dict(
            sorted(Counter(item["video_id"] for item in awaiting_codex).items())
        ),
        "public_corpus_bytes": None,
    }


def render_quality_report_markdown(report: dict, title: str) -> str:
    """Render a compact, reviewable Markdown companion to the JSON report."""
    rows = [
        ("Concepts", report["concept_count"]),
        ("Published videos", report["published_video_count"]),
        ("Evidence moments", report["evidence_count"]),
        ("Distinct excerpts", report["distinct_excerpt_count"]),
        ("Isolated concepts", len(report["concepts_without_relations"])),
        ("Single-source concepts", len(report["single_source_concepts"])),
        ("Verified visuals", report["verified_visual_count"]),
        ("Pending candidates", report["pending_candidate_count"]),
        ("Awaiting Codex adjudication", report["awaiting_codex_adjudication_count"]),
        ("Public corpus bytes", report["public_corpus_bytes"]),
    ]
    lines = [f"# {title} quality report", "", "| Signal | Count |", "|---|---:|"]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.extend(["", "## Evidence outliers", ""])
    if report["evidence_outliers"]:
        lines.extend(
            f"- {item['label']}: {item['evidence_count']} moments"
            for item in report["evidence_outliers"]
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Remaining quality work", ""])
    lines.append(
        f"- {report['visual_sources'].get('nearby_visual_inference', 0)} proposed visual clips still require manual review."
    )
    lines.append(
        f"- {len(report['single_source_concepts'])} concepts still have evidence from only one source video."
    )
    lines.append(
        f"- {report['moments_with_repeated_excerpt']} moments share excerpt text with another moment."
    )
    return "\n".join(lines) + "\n"


def sanitized_video(video: Video) -> Video:
    return video.model_copy(
        update={"transcript": None, "channel_name": video.channel_name.strip()}
    )


def publish(
    concept_dir: Path,
    video_dir: Path,
    output_dir: Path,
    knowledge_base: dict[str, str],
    navigation: dict | None = None,
    include_demo: bool = False,
) -> PublishCorpus:
    videos = load_videos(video_dir)
    excluded_video_ids = {
        video.id for video in videos if video.availability == "demo_fixture" and not include_demo
    }
    concepts = []
    for concept in load_reviewed_concepts(concept_dir):
        if concept.review_status != "approved":
            continue
        public_evidence = [
            evidence
            for evidence in concept.evidence
            if evidence.review_status == "approved"
            and evidence.source.video_id not in excluded_video_ids
        ]
        if public_evidence:
            public_relations = []
            for relation in concept.relations:
                if relation.review_status != "approved":
                    continue
                public_sources = [
                    source
                    for source in relation.sources
                    if source.video_id not in excluded_video_ids
                ]
                if public_sources:
                    public_relations.append(
                        relation.model_copy(update={"sources": public_sources})
                    )
            concepts.append(
                concept.model_copy(
                    update={"evidence": public_evidence, "relations": public_relations}
                )
            )
    public_concept_ids = {concept.id for concept in concepts}
    concepts = [
        concept.model_copy(
            update={
                "relations": [
                    relation
                    for relation in concept.relations
                    if relation.target_concept_id in public_concept_ids
                ]
            }
        )
        for concept in concepts
    ]
    errors = validate_corpus(concepts, videos)
    public_navigation = None
    if navigation:
        public_navigation = dict(navigation)

        def public_nodes(nodes: list[dict]) -> list[dict]:
            output = []
            for node in nodes:
                item = dict(node)
                item["concept_ids"] = [
                    concept_id
                    for concept_id in item.get("concept_ids", [])
                    if concept_id in public_concept_ids
                ]
                item["children"] = public_nodes(item.get("children", []))
                output.append(item)
            return output

        public_navigation["sections"] = public_nodes(public_navigation.get("sections", []))
    parsed_navigation = (
        KnowledgeNavigation.model_validate(public_navigation) if public_navigation else None
    )
    if parsed_navigation:
        errors.extend(validate_navigation(parsed_navigation, concepts))
    if errors:
        raise ValueError("Publish validation failed:\n- " + "\n- ".join(errors))
    used_video_ids = {
        evidence.source.video_id for concept in concepts for evidence in concept.evidence
    }
    used_video_ids.update(
        evidence.visual_source.video_id
        for concept in concepts
        for evidence in concept.evidence
        if evidence.visual_source
    )
    used_video_ids.update(
        source.video_id
        for concept in concepts
        for relation in concept.relations
        for source in relation.sources
    )
    public_videos = [sanitized_video(video) for video in videos if video.id in used_video_ids]
    corpus = PublishCorpus(
        knowledge_base=knowledge_base,
        concepts=concepts,
        videos=public_videos,
        navigation=parsed_navigation,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "corpus.json", corpus)
    write_json(
        output_dir / "manifest.json",
        {
            "corpus_hash": sha256_json(corpus.model_dump(mode="json")),
            "concept_count": len(concepts),
            "video_count": len(public_videos),
        },
    )
    return corpus
