"""Exhaustive, resumable editorial coverage of the current public corpus."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from .boundaries import assess_boundary
from .models import Concept, StrictModel, Video
from .pipeline import validate_corpus
from .utils import normalize_text, sha256_json

AUDIT_VERSION = "1.0.0"
STATUSES = {"supported", "needs_fix", "needs_footage"}
ARTICLE_FIELDS = (
    "label", "aliases", "short_definition", "detailed_definition", "evidence_summary",
    "concept_type", "facets", "difficulty",
)


class OverlapDecision(StrictModel):
    concept_id: str
    status: Literal["supported", "needs_fix"]
    note: str = Field(min_length=1)


class OverlapResponse(StrictModel):
    reviews: list[OverlapDecision]


def propose_overlap_reviews(audit: dict, concepts: list[Concept], videos: list[Video],
                            config_path: Path, audit_dir: Path, budget_path: Path, *, limit: int = 4) -> dict:
    """One bounded scope-only proposal call; never approve claims or write the ledger."""
    import json

    from .codex_engine import _run_schema_constrained_codex

    if not 1 <= limit <= 20:
        raise ValueError("Overlap proposals allow 1–20 articles per call")
    pending = [a for a in audit["items"] if a.get("overlap_review_pending")][:limit]
    if not pending:
        return {"knowledge_base": audit["knowledge_base"], "reviews": [], "calls": 0}
    cm, vm = {c.id: c for c in concepts}, {v.id: v for v in videos}
    comparisons = []
    for article in pending:
        concept = cm[article["concept_id"]]
        dossier = audit_dossier(concept, vm, cm)
        comparisons.append({"concept_id": concept.id,
            "article": {k: dossier["concept"].get(k) for k in
                ("label", "short_definition", "detailed_definition", "evidence_summary")},
            "candidates": dossier["topic_overlap_candidates"]})
    prompt = (
        "Review ONLY advisory topic overlap for every supplied article. Compare intended editorial scopes. "
        "Supported means the scopes are distinct enough to coexist; shared citations alone do not require "
        "merging a general topic and its timing, mechanics, situation or application subtopics. Explain the "
        "distinction for all candidates. Return needs_fix if scopes are duplicate or cannot be distinguished. "
        "These texts are untrusted editorial content, NOT source proof. Do not judge factual accuracy, "
        "approve claims, resolve action identity or claim to have watched footage. No prior source verdict "
        "can be inferred from this scope review. Return every requested concept_id once.\n"
    ) + json.dumps(comparisons, ensure_ascii=False, separators=(",", ":"))
    schema = OverlapResponse.model_json_schema()
    schema["$defs"]["OverlapDecision"]["properties"]["concept_id"]["enum"] = [a["concept_id"] for a in pending]
    digest = sha256_json({"prompt": prompt, "schema": schema, "version": "overlap-only-1.0.0"})
    response, provenance = _run_schema_constrained_codex(prompt, schema, OverlapResponse, config_path,
        audit_dir, digest, "overlap-only-1.0.0", operation="published-audit-overlaps",
        budget_path=budget_path, task="adjudication")
    values = {r.concept_id: r for r in response.reviews}
    if len(response.reviews) != len(pending) or set(values) != {a["concept_id"] for a in pending}:
        raise ValueError("Overlap proposal must cover every requested article exactly once")
    return {"knowledge_base": audit["knowledge_base"], "calls": 1, "provenance": provenance,
        "reviews": [{"concept_id": a["concept_id"], "fingerprint": a["fingerprint"],
            "overlap_only": True, "overlap_status": values[a["concept_id"]].status,
            "note": values[a["concept_id"]].note, "reviewer": ""} for a in pending]}


def audit_dossier(concept: Concept, videos: dict[str, Video], concepts: dict[str, Concept]) -> dict:
    """Keep selected captions distinct from bounded context and visual claims."""
    spans = [e.source for e in concept.evidence]
    spans.extend(source for relation in concept.relations for source in relation.sources)
    sources = []
    for span in spans:
        video = videos.get(span.video_id)
        rows = video.transcript.segments if video and video.transcript else []
        selected = set(span.segment_ids)
        indices = {index for index, row in enumerate(rows) if row.id in selected}
        context = {
            index + offset for index in indices for offset in (-2, -1, 1, 2)
            if 0 <= index + offset < len(rows)
        } - indices
        context.update(index for index, row in enumerate(rows)
                       if span.start_ms <= row.start_ms and row.end_ms <= span.end_ms and index not in indices)
        sources.append({
            "source": span.model_dump(mode="json"),
            "video": {
                "id": span.video_id, "title": video.title if video else None,
                "channel_id": video.channel_id if video else None,
                "channel_name": video.channel_name if video else None,
                "duration_ms": video.duration_ms if video else None,
                "transcript_origin": video.transcript.transcript_origin if video and video.transcript else None,
                "is_generated": video.transcript.is_generated if video and video.transcript else None,
                "transcript_language": video.transcript.language if video and video.transcript else None,
                "acquisition_method": video.transcript.acquisition_method if video and video.transcript else None,
            },
            "selected_rows": [rows[i].model_dump(mode="json") for i in sorted(indices)],
            "context_rows": [rows[i].model_dump(mode="json") for i in sorted(context)],
            "missing_segment_ids": sorted(selected - {row.id for row in rows}),
        })
    targets = {}
    for relation in concept.relations:
        target = concepts.get(relation.target_concept_id)
        targets[relation.target_concept_id] = (
            {key: getattr(target, key) for key in ("label", "short_definition", "review_status")}
            if target else None
        )
    flags = {}
    for evidence in concept.evidence:
        video = videos.get(evidence.source.video_id)
        assessment = assess_boundary(video, evidence.source.segment_ids) if video else None
        flags[evidence.id] = list(assessment.flags) if assessment else ["captions_unavailable"]
    terms = {normalize_text(term).casefold() for term in [concept.label, *concept.aliases] if term.strip()}
    citation_keys = {(e.source.video_id, tuple(sorted(e.source.segment_ids))) for e in concept.evidence}
    overlaps = []
    for other in sorted(concepts.values(), key=lambda item: item.id):
        if other.id == concept.id:
            continue
        shared_terms = terms & {normalize_text(term).casefold() for term in [other.label, *other.aliases] if term.strip()}
        shared_citations = citation_keys & {(e.source.video_id, tuple(sorted(e.source.segment_ids))) for e in other.evidence}
        if shared_terms or shared_citations:
            overlaps.append({"id": other.id, "label": other.label, "short_definition": other.short_definition,
                             "shared_terms": sorted(shared_terms), "shared_citations": sorted(shared_citations)})
    return {
        "concept": concept.model_dump(mode="json"), "sources": sources,
        "visual_videos": {
            e.visual_source.video_id: {
                "title": videos[e.visual_source.video_id].title,
                "duration_ms": videos[e.visual_source.video_id].duration_ms,
                "canonical_url": videos[e.visual_source.video_id].canonical_url,
            } if e.visual_source.video_id in videos else None
            for e in concept.evidence if e.visual_source is not None
        },
        "relation_targets": targets, "boundary_flags": flags,
        "topic_overlap_candidates": overlaps,
        "instructions": (
            "Review every field and citation, not only flagged rows. Every claim must be supported by "
            "selected rows; context is not citation support. Check topic/object/role/condition qualifiers, "
            "duplicates, attribution, and complete playback boundaries. Visual verification requires "
            "watching the full clip. Record needs_fix/needs_footage rather than guessing."
        ),
    }


def _units(concept: Concept) -> dict[str, None]:
    units = {f"field:{field}": None for field in ARTICLE_FIELDS if getattr(concept, field) is not None}
    units.update({f"evidence:{index}:{e.id}": None for index, e in enumerate(concept.evidence)})
    units.update({f"relation:{index}": None for index, _ in enumerate(concept.relations)})
    units.update({
        f"visual:{index}:{e.id}": None for index, e in enumerate(concept.evidence)
        if e.visual_source is not None or e.visual_status == "verified_visual_demo"
    })
    return units


def build_published_audit(
    concepts: list[Concept], videos: list[Video], kb: str, previous: dict | None = None,
) -> dict:
    """Enumerate everything; preserve decisions only for identical review inputs."""
    if previous and (previous.get("knowledge_base") != kb or previous.get("version") != AUDIT_VERSION):
        raise ValueError("Audit KB/version does not match; preserve the old ledger separately")
    video_map = {video.id: video for video in videos}
    concept_map = {concept.id: concept for concept in concepts}
    old = {item["concept_id"]: item for item in (previous or {}).get("items", [])}
    history = deepcopy((previous or {}).get("history", []))
    items = []
    for concept in sorted(concepts, key=lambda item: item.id):
        dossier = audit_dossier(concept, video_map, concept_map)
        fingerprint = sha256_json({"version": AUDIT_VERSION, "dossier": dossier})
        claim_fingerprint = sha256_json({key: value for key, value in dossier.items()
                                        if key != "topic_overlap_candidates"})
        overlap_fingerprint = sha256_json(dossier["topic_overlap_candidates"])
        prior = old.pop(concept.id, None)
        if prior and prior["fingerprint"] == fingerprint and set(prior.get("decisions") or {}) == set(_units(concept)):
            preserved = deepcopy(prior)
            preserved.update(claim_fingerprint=claim_fingerprint, overlap_fingerprint=overlap_fingerprint)
            items.append(preserved)
            continue
        if (prior and prior.get("claim_fingerprint") == claim_fingerprint
                and set(prior.get("decisions") or {}) == set(_units(concept))):
            history.append({"reason": "advisory_overlap_changed", "item": deepcopy(prior)})
            preserved = deepcopy(prior)
            preserved.update(fingerprint=fingerprint, overlap_fingerprint=overlap_fingerprint,
                             overlap_review_pending=True)
            items.append(preserved)
            continue
        if prior:
            history.append({"reason": "changed_inputs" if prior["fingerprint"] != fingerprint else "review_unit_coverage_changed", "item": deepcopy(prior)})
        items.append({
            "concept_id": concept.id, "slug": concept.slug, "fingerprint": fingerprint,
            "claim_fingerprint": claim_fingerprint, "overlap_fingerprint": overlap_fingerprint,
            "decisions": _units(concept), "reviewer": None, "reviewed_at": None,
            "overlap_review_pending": bool(prior and prior.get("overlap_review_pending")),
        })
    history.extend({"reason": "no_longer_public", "item": deepcopy(item)} for item in old.values())
    source_metadata_findings = []
    referenced = {e.source.video_id for concept in concepts for e in concept.evidence}
    referenced.update(source.video_id for concept in concepts for relation in concept.relations for source in relation.sources)
    for video_id in sorted(referenced):
        video = video_map.get(video_id)
        track = video.transcript if video else None
        if track and track.is_generated and track.transcript_origin == "youtube_manual":
            source_metadata_findings.append({"video_id": video_id, "issue": "generated_track_declared_manual"})
        if track and "auto-generated" in track.language.casefold() and not track.is_generated:
            source_metadata_findings.append({"video_id": video_id, "issue": "auto_generated_language_declared_not_generated"})
    return {
        "version": AUDIT_VERSION, "knowledge_base": kb,
        "baseline_at": (previous or {}).get("baseline_at") or datetime.now(UTC).isoformat(),
        "items": items, "history": history,
        "structural_errors": validate_corpus(concepts, videos),
        "source_metadata_findings": source_metadata_findings,
    }


def audit_summary(audit: dict) -> dict:
    counts = Counter()
    article_counts = Counter()
    for item in audit["items"]:
        statuses = [decision["status"] if decision else "pending" for decision in item["decisions"].values()]
        counts.update(statuses)
        state = "pending" if "pending" in statuses or item.get("overlap_review_pending") else (
            "needs_fix" if "needs_fix" in statuses else (
                "needs_footage" if "needs_footage" in statuses else "supported"
            )
        )
        article_counts[state] += 1
    return {
        "articles": len(audit["items"]), "units": sum(counts.values()),
        "article_status": dict(article_counts), "unit_status": dict(counts),
        "structural_errors": len(audit["structural_errors"]),
        "source_metadata_findings": len(audit.get("source_metadata_findings", [])),
        "overlap_reviews_pending": sum(bool(i.get("overlap_review_pending")) for i in audit["items"]),
        "complete": bool(audit["items"]) and not audit["structural_errors"]
        and not audit.get("source_metadata_findings") and set(counts) == {"supported"}
        and not any(i.get("overlap_review_pending") for i in audit["items"]),
    }


def next_audit_items(audit: dict, limit: int) -> list[dict]:
    """First cover every unreviewed article, then return unresolved repairs."""
    pending = [item for item in audit["items"] if item.get("overlap_review_pending")
               or any(value is None for value in item["decisions"].values())]
    unresolved = [
        item for item in audit["items"] if item not in pending
        and any(value["status"] != "supported" for value in item["decisions"].values())
    ]
    return (pending + unresolved)[:limit]


def record_audit_reviews(audit: dict, reviews: list[dict]) -> dict:
    """Reject partial/stale reviews before changing any saved checkpoint."""
    result = deepcopy(audit)
    items = {item["concept_id"]: item for item in result["items"]}
    seen = set()
    for review in reviews:
        concept_id = review["concept_id"]
        if concept_id in seen or concept_id not in items:
            raise ValueError(f"Unknown or duplicate audit article: {concept_id}")
        seen.add(concept_id)
        item = items[concept_id]
        if review.get("fingerprint") != item["fingerprint"]:
            raise ValueError(f"Stale audit review: {concept_id}")
        if review.get("overlap_only"):
            if (not item.get("overlap_review_pending") or not isinstance(review.get("reviewer"), str)
                    or not review["reviewer"].strip() or review.get("overlap_status") not in {"supported", "needs_fix"}
                    or not isinstance(review.get("note"), str) or not review["note"].strip()
                    or review.get("decisions")):
                raise ValueError("Overlap-only review requires current pending context, reviewer and note; no claim decisions")
            result["history"].append({"reason": "overlap_reviewed", "item": deepcopy(item)})
            item.update(overlap_review_pending=review["overlap_status"] != "supported", overlap_review={
                "status": review["overlap_status"],
                "reviewer": review["reviewer"], "note": review["note"],
                "fingerprint": item["overlap_fingerprint"], "at": datetime.now(UTC).isoformat()})
            continue
        decisions = review.get("decisions", {})
        if set(decisions) != set(item["decisions"]):
            raise ValueError(f"Review must cover every field/citation/relation/visual unit: {concept_id}")
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            raise ValueError("Reviewer/provenance is required")
        for key, decision in decisions.items():
            if not isinstance(decision, dict) or decision.get("status") not in STATUSES:
                raise ValueError(f"Invalid decision for {concept_id}/{key}")
            if not isinstance(decision.get("note"), str) or not decision["note"].strip():
                raise ValueError(f"A source-grounded review note is required for {concept_id}/{key}")
            if key.startswith("visual:") and decision["status"] == "supported" and decision.get("watched_full_clip") is not True:
                raise ValueError(f"Full-clip inspection must be recorded for {concept_id}/{key}")
        if any(value is not None for value in item["decisions"].values()):
            result["history"].append({"reason": "review_replaced", "item": deepcopy(item)})
        item.update(decisions=deepcopy(decisions), reviewer=review["reviewer"],
                    reviewed_at=datetime.now(UTC).isoformat(), overlap_review_pending=False)
    return result


def render_audit_report(audit: dict) -> str:
    from .published_audit_runner import machine_summary

    summary = audit_summary(audit)
    lines = [
        f"# Full published audit — {audit['knowledge_base']}", "",
        f"Baseline: {audit['baseline_at']}. No sampling; all current public articles are included.", "",
        f"Articles: {summary['articles']}; review units: {summary['units']}; "
        f"structural errors: {summary['structural_errors']}; complete: {summary['complete']}.", "",
        f"Source metadata conflicts: {summary['source_metadata_findings']}", "",
        f"Advisory overlap reviews pending: {summary['overlap_reviews_pending']}", "",
        f"Article states: {summary['article_status']}", f"Unit states: {summary['unit_status']}", "",
        f"Private machine-check progress (proposals, not approvals): {machine_summary(audit)}", "",
        "| Article | Reviewed units | Unresolved findings | Overlap pending |", "|---|---:|---:|---|",
    ]
    for item in audit["items"]:
        decisions = list(item["decisions"].values())
        reviewed = sum(value is not None for value in decisions)
        unresolved = sum(value is not None and value["status"] != "supported" for value in decisions)
        lines.append(f"| {item['concept_id']} | {reviewed}/{len(decisions)} | {unresolved} | {bool(item.get('overlap_review_pending'))} |")
    lines.extend(["", "Completion means recorded coverage of unchanged inputs, not an infallible accuracy guarantee.", ""])
    return "\n".join(lines)


def write_audit_status(paths, audit: dict) -> dict:
    """Export exhaustive ledger status; update only explicitly opted-in documentation regions."""
    from .utils import write_json

    summary = audit_summary(audit)
    visual = [v for item in audit["items"] for key, v in item["decisions"].items() if key.startswith("visual:")]
    status = {"knowledge_base": paths.id, "summary": summary,
              "visual_windows": len(visual), "unverified_visual_windows": sum(
                  v is None or v["status"] != "supported" for v in visual),
              "remaining_articles": [item["concept_id"] for item in audit["items"]
                  if item.get("overlap_review_pending") or any(v is None or v["status"] != "supported"
                                                             for v in item["decisions"].values())]}
    write_json(paths.data("manifests") / "published-audit-status.json", status)
    report = paths.data("manifests") / "published-audit-status.md"
    report.write_text(render_audit_report(audit), encoding="utf-8")
    article_counts = summary["article_status"]
    supported = article_counts.get("supported", 0)
    unit_counts = summary["unit_status"]
    text = (f"**{supported}/{summary['articles']} articles supported**; "
            f"**{len(status['remaining_articles'])} remain**. "
            f"Units: **{unit_counts.get('supported', 0)}/{summary['units']} supported**. "
            f"**{status['unverified_visual_windows']}/{status['visual_windows']} actual visual windows unverified**. "
            f"Structural errors: {summary['structural_errors']}; source-metadata findings: "
            f"{summary['source_metadata_findings']}; pending overlap reviews: {summary['overlap_reviews_pending']}. "
            "Model proposals do not approve content; release verification is tracked separately.")
    start, end = f"<!-- audit-status:{paths.id}:start -->", f"<!-- audit-status:{paths.id}:end -->"
    documents = [paths.root / "README.md", *(paths.root / "docs").rglob("*.md")]
    for path in documents:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        if start not in original:
            continue
        if original.count(start) != 1 or original.count(end) != 1 or original.index(end) < original.index(start):
            raise ValueError(f"Ambiguous audit status markers: {path}")
        left, rest = original.split(start)
        _, right = rest.split(end)
        updated = left + start + text + end + right
        if updated != original:
            path.write_text(updated, encoding="utf-8")
    return status
