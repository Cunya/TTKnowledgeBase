"""Build concise, source-grounded concept summaries without an LLM.

The canonical evidence ``reason`` fields are already reviewed editorial
paraphrases. This module only combines those reasons into a readable paragraph;
it never reads or republishes raw transcript text and never invents a claim.
"""

from __future__ import annotations

import re
from pathlib import Path

from .codex_engine import (
    CodexError,
    summarize_evidence_batch_with_codex,
)
from .models import Concept
from .utils import normalize_text, read_yaml, sha256_json

SUMMARY_FORMAT_VERSION = "direct-synthesis-v10"

_REPORTING_PREFIX = re.compile(
    r"^(?:(?:the)\s+)?(?:speaker|coach|source|evidence|transcript|moments?|examples?)\s+"
    r"(?:(?:repeatedly|directly|explicitly|specifically|independently|clearly|also)\s+)*"
    r"(?:[a-z]+(?:s|ed)|appears\s+to\s+[a-z]+)\s+(?:that\s+)?",
    re.IGNORECASE,
)


def _editorial_reason(reason: str) -> str:
    value = normalize_text(reason)
    contrast_match = re.match(
        r"^(?:(?:the)\s+)?(?:speaker|coach|source|evidence|transcript|moments?|examples?)\s+"
        r"(?:(?:repeatedly|directly|explicitly|clearly|also)\s+)*contrasts?\s+(.+)$",
        value,
        re.IGNORECASE,
    )
    if contrast_match and " with " in contrast_match.group(1):
        left, right = contrast_match.group(1).split(" with ", 1)
        return f"A useful contrast is between {left} and {right}"
    value = _REPORTING_PREFIX.sub("", value)
    value = re.sub(
        r"(?i)\b(?:the )?speaker\s+tells\s+players\s+to\s+",
        "players should ",
        value,
    )
    value = re.sub(
        r"(?i)\b(?:the )?(?:speaker|coach)'s\s+",
        "the ",
        value,
    )
    value = re.sub(
        r"(?i)\bacting as (?:your|their|its) own coach\b",
        "using self-review",
        value,
    )
    value = re.sub(
        r"(?i)\s+with\s+(?:the )?(?:speaker|coach)\s+"
        r"(?:noting|saying|stating|explaining|describing)\s+that\s+",
        " because ",
        value,
    )
    value = re.sub(
        r"(?i)\b(?:the )?(?:speaker|coach)\s+(?:again\s+)?(?:says?|states?|explains?)\s+",
        "",
        value,
    )
    value = re.sub(
        r"(?i)\b(?:(?:the|a)\s+(?:second|first|other)\s+)?(?:the\s+)?"
        r"(?:speaker|coach|source|evidence|transcript)\s+"
        r"(?:(?:repeatedly|directly|explicitly|specifically|independently|clearly|also)\s+)*"
        r"(?:[a-z]+(?:s|ed)|appears\s+to\s+[a-z]+)\s+(?:(?:that|to)\s+)?",
        "",
        value,
    )
    value = re.sub(
        r"\s+(?:and|while|but)\s+(?:(?:the)\s+)?(?:speaker|coach|source|evidence|transcript)\s+"
        r"(?:(?:repeatedly|directly|explicitly|clearly|also)\s+)*"
        r"(?:[a-z]+(?:s|ed)|appears\s+to\s+[a-z]+)\s+(?:that\s+)?",
        " and ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s+and\s+(?:warns?|says?|states?|explains?|describes?|emphasizes?|"
        r"defines?|identifies?|adds?|contrasts?)\s+(?:that\s+)?",
        " and ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\bthe source material\b", "the guidance", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:the )?(?:source|evidence|transcript)\b\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"^A (.+?) and without (.+)$",
        lambda match: f"{match.group(1)} is needed; without {match.group(2)}",
        value,
        flags=re.IGNORECASE,
    )
    if value:
        return value[0].upper() + value[1:]
    return normalize_text(reason)


def _distinct_reasons(concept: Concept) -> list[str]:
    reasons: list[str] = []
    for evidence in concept.evidence:
        if evidence.review_status != "approved" or not evidence.reason.strip():
            continue
        reason = _editorial_reason(evidence.reason)
        if reason not in reasons:
            reasons.append(reason)
    return reasons


def evidence_summary_source_hash(concept: Concept) -> str:
    """Fingerprint the approved evidence reasons that feed a generated summary."""
    return sha256_json(
        [{"summary_format": SUMMARY_FORMAT_VERSION}]
        + [
            {
                "id": evidence.id,
                "reason": normalize_text(evidence.reason),
                "review_status": evidence.review_status,
            }
            for evidence in concept.evidence
            if evidence.review_status == "approved" and evidence.reason.strip()
        ]
    )


def _sample_reasons(reasons: list[str], limit: int) -> list[str]:
    if len(reasons) <= limit:
        return reasons
    if limit < 2:
        return reasons[:limit]
    indexes = {
        round(index * (len(reasons) - 1) / (limit - 1)) for index in range(limit)
    }
    return [reason for index, reason in enumerate(reasons) if index in indexes]


def build_evidence_summary(concept: Concept, *, max_points: int = 8) -> str | None:
    """Return an essay-like synthesis of approved evidence reasons.

    This is deliberately deterministic. It is suitable for filling missing
    summaries from already reviewed evidence, while leaving any existing
    hand-authored summary untouched.
    """
    reasons = _distinct_reasons(concept)
    if not reasons:
        return None
    points = _sample_reasons(reasons, max_points)
    body = " ".join(points)
    if len(reasons) > len(points):
        body += " Additional points reinforce the same theme."
    return (
        f"{concept.label} brings together several connected ideas. {body} Together, "
        "these principles show how the topic is applied in practice while preserving "
        "the relevant distinctions and constraints."
    )


def build_missing_summaries(concept_dir: Path, *, max_points: int = 8) -> list[tuple[Path, str]]:
    """Build summaries for concepts that do not yet have one."""
    missing: list[tuple[Path, str]] = []
    for path in sorted(concept_dir.glob("*.yaml")):
        data = read_yaml(path)
        if not data or data.get("evidence_summary"):
            continue
        concept = Concept.model_validate(data)
        summary = build_evidence_summary(concept, max_points=max_points)
        if summary:
            missing.append((path, summary))
    return missing


def build_stale_summaries(concept_dir: Path, *, max_points: int = 8) -> list[tuple[Path, str]]:
    """Build replacements for generated summaries whose evidence changed."""
    stale: list[tuple[Path, str]] = []
    for path in sorted(concept_dir.glob("*.yaml")):
        data = read_yaml(path)
        if not data or not data.get("evidence_summary_source_hash"):
            continue
        if data.get("evidence_summary_generator") == "codex":
            continue
        concept = Concept.model_validate(data)
        if data["evidence_summary_source_hash"] == evidence_summary_source_hash(concept):
            continue
        summary = build_evidence_summary(concept, max_points=max_points)
        if summary:
            stale.append((path, summary))
    return stale


def _codex_summary_targets(concept_dir: Path, *, refresh_generated: bool) -> list[Path]:
    targets: list[Path] = []
    for path in sorted(concept_dir.glob("*.yaml")):
        data = read_yaml(path)
        if not data:
            continue
        if not data.get("evidence_summary"):
            targets.append(path)
        elif refresh_generated and data.get("evidence_summary_source_hash"):
            targets.append(path)
    return targets


def _validate_codex_summary(summary: str) -> None:
    value = normalize_text(summary)
    if "\n" in summary or re.search(r"(?:^|\n)\s*[-*•]", summary):
        raise CodexError("Codex summary must be one paragraph, not a list")
    if len(re.findall(r"[.!?](?:\s|$)", value)) < 2:
        raise CodexError("Codex summary must contain at least two complete sentences")
    if re.search(
        r"\b(?:the )?(?:source|evidence|transcript|speaker|coach)\b",
        value,
        re.IGNORECASE,
    ):
        raise CodexError("Codex summary contains source-reporting language")


def write_codex_summaries(
    concept_dir: Path,
    config_path: Path,
    audit_dir: Path,
    budget_path: Path,
    *,
    max_points: int = 8,
    refresh_generated: bool = False,
    model_override: str | None = None,
) -> list[Path]:
    """Use the configured Codex model to write coherent generated essays."""
    targets = _codex_summary_targets(concept_dir, refresh_generated=refresh_generated)
    written: list[Path] = []
    for start in range(0, len(targets), 8):
        batch_paths = targets[start : start + 8]
        batch: list[dict] = []
        concepts: dict[str, Concept] = {}
        for path in batch_paths:
            concept = Concept.model_validate(read_yaml(path))
            reasons = _sample_reasons(_distinct_reasons(concept), max_points)
            if not reasons:
                continue
            concepts[concept.id] = concept
            batch.append({"concept_id": concept.id, "label": concept.label, "reasons": reasons})
        if not batch:
            continue
        summaries, _ = summarize_evidence_batch_with_codex(
            batch,
            config_path,
            audit_dir,
            model_override=model_override,
            budget_path=budget_path,
        )
        for path in batch_paths:
            concept = next(
                (item for item in concepts.values() if item.slug == path.stem),
                None,
            )
            if concept is None:
                continue
            summary = summaries[concept.id]
            _validate_codex_summary(summary)
            _write_summary_file(
                path,
                summary,
                evidence_summary_source_hash(concept),
                generator="codex",
            )
            written.append(path)
    return written


def write_missing_summaries(
    concept_dir: Path, *, max_points: int = 8, refresh_generated: bool = False
) -> list[Path]:
    """Write missing summaries and optionally refresh generated ones.

    Existing reviewed prose is never overwritten unless it has the generated
    source hash marker and ``refresh_generated`` is enabled.
    """
    updates = build_missing_summaries(concept_dir, max_points=max_points)
    if refresh_generated:
        updates.extend(build_stale_summaries(concept_dir, max_points=max_points))
    written: list[Path] = []
    for path, summary in updates:
        concept = Concept.model_validate(read_yaml(path))
        _write_summary_file(
            path,
            summary,
            evidence_summary_source_hash(concept),
            generator="deterministic",
        )
        written.append(path)
    return written


def _write_summary_file(
    path: Path, summary: str, source_hash: str, *, generator: str
) -> None:
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    replacement = _summary_yaml(summary, source_hash, newline, generator=generator)
    summary_match = _summary_block_pattern().search(text)
    if summary_match:
        text = text[: summary_match.start()] + replacement + text[summary_match.end() :]
    else:
        text = re.sub(
            r"(?m)^evidence_summary_source_hash:.*(?:\r?\n|$)", "", text, count=1
        )
        text = re.sub(
            r"(?m)^evidence_summary_generator:.*(?:\r?\n|$)", "", text, count=1
        )
        lines = text.splitlines(keepends=True)
        insertion = next(
            (index + 1 for index, line in enumerate(lines) if line.startswith("short_definition:")),
            None,
        )
        if insertion is None:
            return
        lines[insertion:insertion] = [replacement]
        text = "".join(lines)
    path.write_text(text, encoding="utf-8", newline="")


def _summary_block_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?m)^evidence_summary: >-\r?\n(?:^  [^\r\n]*(?:\r?\n|$))+"
        r"(?:^evidence_summary_source_hash:.*(?:\r?\n|$))?"
        r"(?:^evidence_summary_generator:.*(?:\r?\n|$))?"
    )


def _summary_yaml(summary: str, source_hash: str, newline: str, *, generator: str) -> str:
    folded = ["evidence_summary: >-", *[f"  {line}" for line in _fold_summary(summary)]]
    folded.append(f'evidence_summary_source_hash: "{source_hash}"')
    folded.append(f'evidence_summary_generator: "{generator}"')
    return "".join(f"{line}{newline}" for line in folded)


def _fold_summary(summary: str, width: int = 96) -> list[str]:
    words = summary.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
