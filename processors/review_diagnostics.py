from pathlib import Path

from rapidfuzz.fuzz import token_set_ratio

from .pipeline import load_reviewed_concepts, load_videos
from .utils import read_yaml, write_json


def build_review_diagnostics(queue_path: Path, concept_dir: Path, output_path: Path) -> dict:
    concepts = load_reviewed_concepts(concept_dir)
    queue = read_yaml(queue_path) or {"items": []}
    video_dir = output_path.parents[3] / "data" / "normalized" / "table-tennis"
    videos = {video.id: video for video in load_videos(video_dir)} if video_dir.exists() else {}
    rows = []
    for item in queue.get("items", []):
        if item.get("decision") != "deferred":
            continue
        candidate = item.get("candidate") or {}
        label = str(candidate.get("canonical_label", "")).strip()
        matches = sorted(
            (
                max(token_set_ratio(label, name) for name in [concept.label, *concept.aliases]),
                concept.label,
                concept.slug,
            )
            for concept in concepts
        )
        best_score, best_label, best_slug = matches[-1] if matches else (0, "", "")
        note = str(item.get("review_notes", ""))
        evidence = candidate.get("evidence", [])
        first_evidence = max(evidence, key=lambda entry: entry.get("confidence", 0), default={})
        segment_ids = first_evidence.get("segment_ids", [])
        video = videos.get(item.get("video_id", ""))
        start_ms = 0
        end_ms = 0
        if video and video.transcript:
            cited = [segment for segment in video.transcript.segments if segment.id in segment_ids]
            if cited:
                start_ms = min(segment.start_ms for segment in cited)
                end_ms = max(segment.end_ms for segment in cited)
        if "boundary" in note or "span" in note:
            category = "evidence boundary"
        elif best_score >= 90:
            category = "likely duplicate"
        elif float(candidate.get("confidence") or 0) < 0.85:
            category = "low confidence"
        elif candidate.get("resolution") != "new":
            category = "ambiguous resolution"
        elif best_score < 90 and float(candidate.get("confidence") or 0) >= 0.85:
            category = "probable new concept"
        else:
            category = "other deferred"
        rows.append({
            "video_id": item.get("video_id", ""),
            "video_title": video.title if video else item.get("video_id", ""),
            "video_start_ms": start_ms,
            "video_end_ms": end_ms,
            "label": label,
            "definition": str(candidate.get("definition", "")),
            "resolution": candidate.get("resolution", ""),
            "confidence": candidate.get("confidence", 0),
            "category": category,
            "reason": note,
            "supporting_moments": len(evidence),
            "supporting_segments": len(segment_ids),
            "best_match": best_label,
            "best_match_slug": best_slug,
        })
    rows.sort(key=lambda row: (-float(row["confidence"]), row["label"]))
    payload = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "total": len(rows),
        "supporting_moments": sum(row["supporting_moments"] for row in rows),
        "supporting_videos": len({row["video_id"] for row in rows}),
        "categories": {category: sum(row["category"] == category for row in rows) for category in sorted({row["category"] for row in rows})},
        "items": rows,
    }
    write_json(output_path, payload)
    return payload
