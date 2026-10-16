"""Optional local advice and audited overrides for source-grounded candidates."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .inventory import build_inventory_ledger, load_inventory_catalog, select_source_balanced
from .models import Concept
from .pipeline import (
    _candidate_source_span,
    load_reviewed_concepts,
    load_videos,
    roundtrip_yaml,
)
from .utils import read_yaml, replace_with_retry, sha256_json, slugify, youtube_url
from .workspace import KnowledgeBasePaths, load_knowledge_base

ROOT = Path(__file__).resolve().parents[1]
MAX_BATCH = 5
ALLOWED_ACTIONS = {"accept_existing", "accept_new", "reject", "keep"}


def _queue_path(paths: KnowledgeBasePaths) -> Path:
    return paths.content / "annotations" / "review-queue.yaml"


def _candidate_hash(item: dict[str, Any]) -> str:
    value = item.get("candidate_hash")
    if isinstance(value, dict):
        value = value.get("sha256")
    return str(value or sha256_json(item.get("candidate") or {})).removeprefix("sha256:")


def _best_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = candidate.get("evidence") or []
    if not evidence:
        raise ValueError("The candidate has no transcript evidence.")
    return max(evidence, key=lambda item: float(item.get("confidence") or 0))


def _context_segments(video: Any, cited_ids: list[str]) -> list[dict[str, Any]]:
    segments = video.transcript.segments if video.transcript else []
    indexes = [index for index, segment in enumerate(segments) if segment.id in cited_ids]
    if not indexes:
        return []
    selected = {
        neighbor
        for index in indexes
        for neighbor in range(max(0, index - 2), min(len(segments), index + 3))
    }
    return [
        {
            "id": segment.id,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "text": segment.normalized_text,
            "cited": segment.id in cited_ids,
        }
        for index, segment in enumerate(segments)
        if index in selected
    ]


def list_human_review(
    paths: KnowledgeBasePaths, *, limit: int = MAX_BATCH, offset: int = 0
) -> dict[str, Any]:
    """Return a small private batch with exact transcript context."""
    queue = read_yaml(_queue_path(paths)) or {"items": []}
    items = [
        item
        for item in queue.get("items", [])
        if item.get("decision") in {"deferred", "human_review"}
    ]
    catalog = load_inventory_catalog(paths)
    balanced = select_source_balanced(
        [
            {
                "video_id": str(item.get("video_id") or ""),
                "source_ids": (catalog.get(str(item.get("video_id") or "")) or {}).get(
                    "source_ids", ["unassigned"]
                ),
                "view_count": (catalog.get(str(item.get("video_id") or "")) or {}).get(
                    "view_count", 0
                ),
                "queue_item": item,
            }
            for item in items
        ],
        len(items),
    )
    items = [value["queue_item"] for value in balanced]
    concepts = load_reviewed_concepts(paths.content / "concepts")
    videos = {video.id: video for video in load_videos(paths.data("normalized"))}
    limit = max(1, min(MAX_BATCH, int(limit)))
    offset = max(0, int(offset))
    output = []
    for item in items[offset : offset + limit]:
        candidate = item.get("candidate") or {}
        evidence = _best_evidence(candidate)
        cited_ids = [str(value) for value in evidence.get("segment_ids", [])]
        video = videos.get(str(item.get("video_id") or ""))
        span = _candidate_source_span(video, cited_ids) if video else None
        output.append(
            {
                "source_id": str(
                    (catalog.get(str(item.get("video_id") or "")) or {}).get(
                        "source_ids", ["unassigned"]
                    )[0]
                ),
                "video_id": item.get("video_id"),
                "candidate_id": candidate.get("candidate_id"),
                "candidate_hash": _candidate_hash(item),
                "decision": item.get("decision"),
                "candidate": candidate,
                "selected_evidence": evidence,
                "review_notes": item.get("review_notes") or "",
                "adjudication_reason": item.get("adjudication_reason") or "",
                "adjudication_attempts": int(item.get("adjudication_attempts") or 0),
                "video": (
                    {
                        "title": video.title,
                        "channel_name": video.channel_name,
                        "url": video.canonical_url,
                    }
                    if video
                    else None
                ),
                "context_segments": _context_segments(video, cited_ids) if video else [],
                "boundary": (
                    {
                        "segment_ids": list(span.segment_ids),
                        "start_ms": span.start_ms,
                        "end_ms": span.end_ms,
                        "snapped_start_ms": span.snapped_start_ms,
                        "snapped_end_ms": span.snapped_end_ms,
                        "flags": list(span.flags),
                        "needs_context": span.needs_context,
                        "reason": span.reason,
                    }
                    if span
                    else None
                ),
            }
        )
    return {
        "knowledge_base": paths.id,
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "items": output,
        "concepts": [
            {"id": concept.id, "label": concept.label, "definition": concept.short_definition}
            for concept in sorted(concepts, key=lambda value: value.label.casefold())
        ],
    }


def _write_yaml_atomic(path: Path, payload: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        roundtrip_yaml.dump(payload, handle)
    replace_with_retry(temporary, path)


def apply_human_review_decision(
    paths: KnowledgeBasePaths, payload: dict[str, Any]
) -> dict[str, Any]:
    """Apply one audited human decision without inventing source metadata."""
    action = str(payload.get("action") or "")
    if action not in ALLOWED_ACTIONS:
        raise ValueError("Action must be accept_existing, accept_new, reject, or keep.")
    notes = str(payload.get("notes") or "").strip()
    if len(notes) < 12:
        raise ValueError("Add a specific review note of at least 12 characters.")

    queue_path = _queue_path(paths)
    queue = read_yaml(queue_path) or {"items": []}
    requested_hash = str(payload.get("candidate_hash") or "")
    item = next(
        (
            value
            for value in queue.get("items", [])
            if value.get("video_id") == payload.get("video_id")
            and (value.get("candidate") or {}).get("candidate_id") == payload.get("candidate_id")
            and _candidate_hash(value) == requested_hash
        ),
        None,
    )
    if not item or item.get("decision") not in {"deferred", "human_review"}:
        raise ValueError("This review item changed or was already resolved. Reload the batch.")

    original_decision = str(item.get("decision"))
    now = datetime.now(UTC).isoformat()
    target_id = str(payload.get("target_concept_id") or "").strip() or None
    history = item.setdefault("manual_review_history", [])
    history.append({"reviewed_at": now, "action": action, "target_concept_id": target_id, "notes": notes})
    item.update(
        review_notes=notes,
        adjudication_method="manual_human_review_v1",
        adjudication_reason=f"Human reviewer selected {action.replace('_', ' ')}.",
        last_adjudicated_at=now,
    )

    if action == "keep":
        _write_yaml_atomic(queue_path, queue)
        return {
            "decision": original_decision,
            "message": "Optional advice saved; the candidate remains automated work.",
        }
    if action == "reject":
        item.update(decision="rejected", canonical_concept_id=None)
        _write_yaml_atomic(queue_path, queue)
        build_inventory_ledger(paths)
        return {"decision": "rejected", "message": "Candidate rejected; no canonical content was changed."}

    if not payload.get("confirm_source") or not payload.get("confirm_concept"):
        raise ValueError("Confirm both transcript support and the target concept before accepting.")
    concepts = load_reviewed_concepts(paths.content / "concepts")
    concept = next((value for value in concepts if value.id == target_id), None)
    if action == "accept_existing" and not concept:
        raise ValueError("Choose an existing reviewed target concept.")
    videos = {video.id: video for video in load_videos(paths.data("normalized"))}
    video = videos.get(str(item.get("video_id") or ""))
    if not video:
        raise ValueError("The normalized source video is unavailable.")
    candidate = item.get("candidate") or {}
    candidate_evidence = _best_evidence(candidate)
    span = _candidate_source_span(video, candidate_evidence.get("segment_ids") or [])
    if not span:
        raise ValueError("The cited segment IDs do not resolve to normalized transcript evidence.")
    if span.dropped_segment_ids:
        raise ValueError(
            "This candidate cites dispersed support. Let Codex split or re-adjudicate it "
            "instead of discarding cited rows."
        )
    if span.needs_context:
        raise ValueError(
            "This candidate fails the deterministic boundary checks and cannot be "
            "accepted through the advisory override."
        )

    if action == "accept_new":
        slug = slugify(str(candidate.get("canonical_label") or ""))
        if not slug:
            raise ValueError("The candidate label cannot produce a stable concept ID.")
        target_id = f"concept-{slug}"
        concept_path = paths.content / "concepts" / f"{slug}.yaml"
        if target_id in {value.id for value in concepts} or concept_path.exists():
            raise ValueError(
                "A concept with this label already exists. Accept into the existing concept instead."
            )
        document = {
            "id": target_id,
            "slug": slug,
            "label": str(candidate.get("canonical_label") or "").strip(),
            "aliases": [
                str(value).strip()
                for value in candidate.get("aliases", [])
                if str(value).strip()
            ],
            "short_definition": str(candidate.get("definition") or "").strip(),
            "concept_type": str(candidate.get("concept_type") or "technique"),
            "facets": {
                str(facet.get("name")): [str(value) for value in facet.get("values", [])]
                for facet in candidate.get("facets", [])
                if facet.get("name")
            },
            "difficulty": candidate.get("difficulty"),
            "evidence": [],
            "relations": [],
            "review_status": "approved",
            "generated_by": {
                "processor": "manual_human_review",
                "version": "1.0.0",
                "input_hash": requested_hash,
                "prompt_version": "manual-human-review-v1",
            },
        }
    else:
        concept_path = paths.content / "concepts" / f"{concept.slug}.yaml"
        document = roundtrip_yaml.load(concept_path.read_text(encoding="utf-8"))
    history[-1]["target_concept_id"] = target_id
    base_id = f"{video.id}-{candidate.get('candidate_id')}-human-reviewed"
    evidence_id = f"{base_id}-{requested_hash[:8]}"
    known_ids = {str(value.get("id")) for value in document.get("evidence", [])}
    if evidence_id not in known_ids:
        visual_status = candidate_evidence.get("visual_status", "not_visual")
        if visual_status == "verified_visual_demo":
            visual_status = "transcript_inferred"
        document.setdefault("evidence", []).append(
            {
                "id": evidence_id,
                "evidence_type": candidate_evidence.get("evidence_type", "explanation"),
                "excerpt": str(candidate.get("definition") or "").strip()[:420],
                "reason": str(candidate_evidence.get("reason") or "").strip(),
                "confidence": min(
                    float(candidate.get("confidence") or 0),
                    float(candidate_evidence.get("confidence") or candidate.get("confidence") or 0),
                ),
                "visual_status": visual_status,
                "review_status": "approved",
                "source": {
                    "video_id": video.id,
                    "start_ms": span.start_ms,
                    "end_ms": span.end_ms,
                    "url": youtube_url(video.id, span.start_ms),
                    "segment_ids": list(span.segment_ids),
                },
            }
        )
    Concept.model_validate(document)
    _write_yaml_atomic(concept_path, document)
    item.update(decision="accepted", canonical_concept_id=target_id)
    _write_yaml_atomic(queue_path, queue)
    build_inventory_ledger(paths)
    return {
        "decision": "accepted",
        "canonical_concept_id": target_id,
        "message": (
            "A new reviewed concept was created from the source-backed candidate."
            if action == "accept_new"
            else "Source-backed evidence was added to the reviewed concept."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("list", "decide"))
    parser.add_argument("--kb", default=None)
    parser.add_argument("--limit", type=int, default=MAX_BATCH)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    paths = load_knowledge_base(ROOT, args.kb)
    try:
        if args.command == "list":
            result = list_human_review(paths, limit=args.limit, offset=args.offset)
        else:
            result = apply_human_review_decision(paths, json.load(sys.stdin))
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
