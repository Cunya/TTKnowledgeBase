"""Private article repair drafts, separate source verification and reviewed application."""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field
from ruamel.yaml import YAML

from .codex_engine import CodexError, _run_schema_constrained_codex
from .evidence_summaries import _editorial_reason
from .llm_budget import LLMBudgetExceeded, usage_token_total
from .models import Concept, FacetCandidate, SourceSpan, StrictModel, Video
from .utils import normalize_text, read_json, read_yaml, replace_with_retry, sha256_json, write_json

REPAIR_VERSION = "1.1.1"
DRAFT_VERSION = "1.1.3"
VERIFICATION_VERSION = "1.1.3"
PROOF_LIMIT_NOTE = "Complete verification source/context proof exceeds row cap; no IDs or context were truncated."
EDITABLE_FIELDS = {
    "label", "aliases", "short_definition", "detailed_definition", "evidence_summary", "concept_type", "facets", "difficulty",
}
REVIEW_RULES = """Use only exact selected_rows as claim support; context_rows are not support.
Check every clause, the topic/object, incoming/outgoing role and necessary conditions.
Use context to detect missing conditions, magnitude or a consequence misread as an instruction.
Context cannot supply positive support: missing owned qualifiers require correction or uncertainty.
Preserve the source-grounded subject, not an erroneous heading. Correct an unsupported or
contradicted label/definition minimally when the owned selected wording establishes the correction.
Do not quarantine supported same-subject evidence merely because it contradicts an erroneous heading.
Do not switch to an unrelated topic to fit misplaced evidence. Quarantine genuinely misplaced or
unsafe evidence; missing topic identity stays uncertain. Shared vocabulary is not topic identity.
An article field may synthesize several citations. Each evidence excerpt/reason must be
supported by its OWN allowed_segment_ids. Relevant examples need not prove the whole article.
Do not infer a causal link merely because two instructions are mentioned together.
Editorial categories are not empirical difficulty ratings. Do not invent a taxonomy type.
Labels and aliases may paraphrase the topic; they do not have to be verbatim caption terms.
Balance and stability can be synonymous descriptions, not separate empirical claims.
For concept_type and category-only facets, judge fit to the article topic, NOT whether the
captions name the taxonomy. Generic 'concept' and a relevant instructional category are valid
editorial metadata. Do not flag these solely for lack of a spoken classification.
Level, difficulty, spin, side, distance and other technical conditions still need actual support.
Relation identity/type must be established by selected support, not just a shared broad subject.
Spoken introductions are not review scaffolding. Public prose must not describe model review.
Both excerpt and reason are public reader-facing text, NOT private justifications. Rewrite
'this contiguous span', 'matches the existing concept' and selected-segment commentary into
the actual instruction. Put review findings in note only. Write article prose directly.
Caption-duration disagreements require reconciliation, not invented trimming or a false-content verdict.
Never invent IDs, timestamps, source identity or visual verification. Visual units need footage.
Preserve meaningful short clips. Repeated text/overlap alone does not prove an error.
Uncertain/partial support stays uncertain. Return EVERY requested unit exactly once.
"""


class RepairEdit(StrictModel):
    field: Literal[
        "label", "aliases", "short_definition", "detailed_definition", "evidence_summary",
        "concept_type", "facets", "difficulty", "excerpt", "reason", "evidence_type",
    ]
    text: str | None = None
    strings: list[str] | None = None
    facets: list[FacetCandidate] | None = None


class RepairUnit(StrictModel):
    key: str
    status: Literal["supported", "needs_fix", "uncertain", "needs_footage"]
    note: str = Field(min_length=1)
    supporting_segment_ids: list[str]
    edits: list[RepairEdit] = []
    quarantine: bool = False


def _response_units(value: object) -> object:
    if isinstance(value, dict):
        if any(not isinstance(unit, dict) or unit.get("key") != key for key, unit in value.items()):
            raise ValueError("Response unit property must match its key")
        return list(value.values())
    return value


class ArticleRepairResponse(StrictModel):
    units: Annotated[list[RepairUnit], BeforeValidator(_response_units)]


class VerifiedUnit(StrictModel):
    key: str
    status: Literal["supported", "needs_fix", "uncertain", "needs_footage"]
    note: str = Field(min_length=1)
    supporting_segment_ids: list[str]


class ArticleVerificationResponse(StrictModel):
    units: Annotated[list[VerifiedUnit], BeforeValidator(_response_units)]


def unit_inputs(dossier: dict, keys: list[str]) -> dict:
    concept = dossier["concept"]
    result = {}
    for key in keys:
        kind, index, *_ = key.split(":", 2)
        if kind == "field":
            value = concept[index]
            sources = dossier["sources"][:len(concept["evidence"])]
        elif kind in {"evidence", "visual"}:
            value = concept["evidence"][int(index)]
            sources = [dossier["sources"][int(index)]]
        else:
            value = concept["relations"][int(index)]
            offset = len(concept["evidence"]) + sum(len(r["sources"]) for r in concept["relations"][:int(index)])
            sources = dossier["sources"][offset:offset+len(value["sources"])]
        result[key] = {
            "value": value,
            "allowed_segment_ids": sorted({row["id"] for source in sources for row in source["selected_rows"]}),
            "source_spans": [source["source"] for source in sources],
        }
    return result


def public_prose_findings(key: str, value: object) -> list[str]:
    texts = [value] if key in {"field:short_definition", "field:detailed_definition", "field:evidence_summary"} else (
        [value.get("excerpt"), value.get("reason")] if key.startswith("evidence:") else []
    )
    findings = []
    if any(isinstance(text, str) and text.strip() and not _editorial_reason(text) for text in texts):
        findings.append("Public prose retains private review scaffolding; replace it with source-grounded instruction.")
    if isinstance(value, dict) and key.startswith("evidence:") and len(value.get("excerpt", "")) > 420:
        findings.append("Evidence excerpt exceeds the existing 420-character publication contract.")
    return findings


def direct_summary_text(concept: dict) -> str | None:
    """Only delete the known deterministic template; never resynthesize unreviewed claims."""
    if concept.get("evidence_summary_generator") != "deterministic" or not concept.get("evidence_summary_source_hash"):
        return None
    summary = concept.get("evidence_summary") or ""
    prefix = f"{concept['label']} brings together several connected ideas. "
    suffix = " Together, these principles show how the topic is applied in practice while preserving the relevant distinctions and constraints."
    if not summary.startswith(prefix) or not summary.endswith(suffix):
        return None
    body = summary[len(prefix):-len(suffix)]
    extra = " Additional points reinforce the same theme."
    if body.endswith(extra):
        body = body[:-len(extra)]
    return body or None


def validate_units(units: list[dict], expected: dict, *, draft: bool) -> None:
    """Check exact coverage, per-citation IDs and the edit whitelist before saving a result."""
    keys = [unit["key"] for unit in units]
    if len(keys) != len(set(keys)) or set(keys) != set(expected):
        raise ValueError("Repair response must cover each requested unit exactly once")
    for unit in units:
        key = unit["key"]
        if set(unit["supporting_segment_ids"]) - set(expected[key]["allowed_segment_ids"]):
            raise ValueError(f"Foreign supporting IDs for {key}")
        if key.startswith("visual:") and unit["status"] != "needs_footage":
            raise ValueError("Unwatched visual units must remain needs_footage")
        editorial_category = key == "field:facets" and isinstance(expected[key]["value"], dict) and set(expected[key]["value"]) <= {"category"}
        if (not draft and unit["status"] == "supported" and expected[key]["value"] and not editorial_category
                and key != "field:concept_type" and not expected[key].get("quarantine")
                and not unit["supporting_segment_ids"]):
            raise ValueError(f"Supported substantive unit has no source IDs: {key}")
        if not draft:
            continue
        edits = unit["edits"]
        fields = [edit["field"] for edit in edits]
        if len(fields) != len(set(fields)):
            raise ValueError(f"Duplicate edits for {key}")
        kind, name, *_ = key.split(":", 2)
        allowed = {name} & EDITABLE_FIELDS if kind == "field" else (
            {"excerpt", "reason"} if kind == "evidence" else set()
        )
        if kind == "evidence" and expected[key]["value"].get("evidence_type") == "demonstration":
            allowed.add("evidence_type")
        if set(fields) - allowed or (unit["quarantine"] and kind not in {"evidence", "relation"}):
            raise ValueError(f"Unauthorized repair for {key}")
        if unit["quarantine"] and edits:
            raise ValueError("Quarantine cannot also rewrite a record")
        if (edits or unit["quarantine"]) and unit["status"] == "supported":
            raise ValueError("Changed units must identify their original finding")
        for edit in edits:
            field = edit["field"]
            if field == "evidence_type" and edit["text"] != "explanation":
                raise ValueError("A demonstration may only be reclassified as a spoken explanation")
            if field == "aliases":
                valid = edit["strings"] is not None and edit["text"] is None and edit["facets"] is None
            elif field == "facets":
                valid = edit["facets"] is not None and edit["text"] is None and edit["strings"] is None
                if valid:
                    names = [facet["name"] for facet in edit["facets"]]
                    valid = len(names) == len(set(names))
            else:
                valid = edit["strings"] is None and edit["facets"] is None
                if field not in {"difficulty", "detailed_definition"}:
                    valid = valid and bool(edit["text"] and edit["text"].strip())
            if not valid:
                raise ValueError(f"Invalid replacement type for {field}")


def edit_value(edit: dict) -> object:
    if edit["field"] == "aliases":
        return edit["strings"]
    if edit["field"] == "facets":
        return {facet["name"]: facet["values"] for facet in edit["facets"]}
    return edit["text"]


def proposed_value(value: object, unit: dict) -> object:
    result = deepcopy(value)
    if unit.get("quarantine"):
        result["review_status"] = "unreviewed"
    for edit in unit["edits"]:
        replacement = edit_value(edit)
        if unit["key"].startswith("field:"):
            result = replacement
        else:
            result[edit["field"]] = replacement
    return result


def proposed_inputs(units: dict, draft: dict) -> dict:
    return {unit["key"]: {**units[unit["key"]],
                          "value": proposed_value(units[unit["key"]]["value"], unit),
                          "quarantine": unit["quarantine"]} for unit in draft["units"]}


def compact_model_payload(payload: dict) -> dict:
    """Share repeated source spans without removing any owned caption or timing."""
    result = deepcopy(payload)
    result.pop("article_fields_hash", None)
    spans = {}
    for unit in result["units"].values():
        owned = unit.pop("source_spans", None)
        if not owned:
            continue
        digest = sha256_json(owned)
        if digest not in spans:
            spans[digest] = (f"s{len(spans)}", owned)
        unit["source_spans_ref"] = spans[digest][0]
        for name in ("value", "archived_original"):
            value = unit.get(name)
            if isinstance(value, dict):
                if len(owned) == 1 and value.get("source") == owned[0]:
                    del value["source"]
                if value.get("sources") == owned:
                    del value["sources"]
    if spans:
        result["source_span_sets"] = {key: value for key, value in spans.values()}
    for name in ("selected_rows", "context_rows"):
        for row in result.get(name, []):
            if row.get("normalized_text") == row.get("text"):
                row.pop("normalized_text", None)
    return result


def _model_call(payload: dict, config_path: Path, audit_dir: Path, budget_path: Path,
                *, verify: bool, heartbeat_callback: Callable | None = None) -> tuple[dict, dict]:
    cap = int(read_yaml(config_path)["codex"].get("max_segments_per_job", 80))
    if len(payload["selected_rows"]) > cap:
        raise ValueError("Selected-source verification exceeds row cap; no support may be truncated")
    if verify and len(payload["selected_rows"]) + len(payload.get("context_rows", [])) > cap:
        raise ValueError("Complete source/context verification exceeds row cap; no context may be truncated")
    payload = {**payload, "context_rows": payload.get("context_rows", [])[:cap-len(payload["selected_rows"])]}
    model = ArticleVerificationResponse if verify else ArticleRepairResponse
    purpose = (
        "Independently verify the proposed values/dispositions. You have no drafter verdict or confidence. "
        "Supported means EVERY resulting clause is grounded, or omission of an unsafe record is justified. "
        "Quarantine is reversible exclusion, not a claim that the captions are false. Do not propose edits.\n"
        if verify else
        "Inspect existing article units. Draft minimal repairs or reversible quarantine for demonstrated "
        "unsupported content/timing conflicts. Do not delete original captions. Keep correct content unchanged. "
        "Missing support in one source chunk is uncertain, not proof against the complete article.\n"
    )
    if verify:
        payload = deepcopy(payload)
        for key, unit in payload["units"].items():
            if key.startswith(("evidence:", "relation:")) and isinstance(unit["value"], dict):
                # Prior processing confidence/approval must not bias source verification.
                unit["value"] = {name: value for name, value in unit["value"].items()
                                 if name not in {"confidence", "review_status"}}
                if unit.get("quarantine"):
                    unit["archived_original"] = unit["value"]
                    unit["value"] = None
        purpose += (
            "Each unit.value is the authoritative PROPOSED result to assess. Article heading/definition "
            "mirror those proposed values. original_topic is only previous editorial context for topic fit, "
            "NOT a claim to verify or source proof. Do not flag an old clause already removed from unit.value.\n"
            "For quarantine=true, value=null means the record is omitted from publication. "
            "archived_original is retained only to assess whether omission is justified. Return supported "
            "when omission is justified, not only when the archived claim is accurate. Preserve supported "
            "narrower same-topic instruction rather than approving unnecessary exclusion.\n"
            "Context can veto an instruction: a described failure is not a goal, and a missing "
            "conditional prefix or magnitude cannot be ignored because the result appears in owned "
            "rows. Explain such a veto in note; positive correction still needs owned condition IDs.\n"
            "Check each claimed actor/object, action and condition against the owned selected wording. "
            "In note, identify the wording establishing any disputed referent. The proposal's nouns are "
            "NOT source evidence. An unfinished or elliptical clause with an unidentified subject/object "
            "cannot establish which body part, equipment or entity it describes. Do not complete that "
            "referent from topic familiarity, adjacent instructions or context outside owned IDs. "
            "If a claim assigns that missing referent, return needs_fix or uncertain, not supported. "
            "A preceding complete independent instruction can still support a narrower claim.\n"
        )
    if not verify and "chunk_proposals" in payload:
        purpose = (
            "Assemble an UNTRUSTED repair proposal from all supplied source-chunk proposals. "
            "This is proposal assembly, not transcript adjudication; selected_rows are deliberately empty. "
            "Do not discard the proposals or mark every unit uncertain merely because those rows are absent. "
            "Preserve per-unit findings and proposed edits/quarantines. Reconcile article fields using the "
            "proposed wording; do not add new factual claims. Use a minimal set of allowed support IDs "
            "covering every proposed clause, taking them from the chunk proposals. Unresolved contradictions "
            "remain uncertain. Statuses are draft findings, NEVER approval. Every resulting nonvisual unit "
            "will receive separate verification with actual selected captions; proposals cannot prove truth. "
            "Preserve the source-grounded subject and proposed corrections to erroneous headings; "
            "do not switch to an unrelated topic. Preserve source/visual metadata, every requested key "
            "and edit restrictions.\n"
        )
        rules = ""
    else:
        rules = REVIEW_RULES
    if not verify:
        purpose += ("If a demonstration record has a supported spoken claim but no inspected visual proof, "
                    "you may change evidence_type only from demonstration to explanation. Preserve all "
                    "source and visual metadata; this never verifies footage. Prefer retaining supported speech.\n")
    purpose += (
        "Identifiers are opaque references, not topic proof. Concept/evidence IDs and slugs may contain "
        "obsolete labels; assess the current proposed wording and owned captions instead.\n"
        "Resolve source_spans_ref through source_span_sets. Owned IDs remain each unit's "
        "allowed_segment_ids; shared spans/context cannot expand that ownership.\n"
    )
    prompt = purpose + rules + json.dumps(compact_model_payload(payload), ensure_ascii=False, separators=(",", ":"))
    version = VERIFICATION_VERSION if verify else DRAFT_VERSION
    schema = model.model_json_schema()
    schema["$defs"]["VerifiedUnit" if verify else "RepairUnit"]["properties"]["key"]["enum"] = list(payload["units"])
    allowed_ids = sorted({sid for unit in payload["units"].values() for sid in unit["allowed_segment_ids"]})
    ids_schema = schema["$defs"]["VerifiedUnit" if verify else "RepairUnit"]["properties"]["supporting_segment_ids"]
    if allowed_ids:
        ids_schema["items"]["enum"] = allowed_ids
    else:
        ids_schema["maxItems"] = 0
    variants = {}
    id_pools = {}
    for key, value in payload["units"].items():
        choices = []
        variant = deepcopy(schema["$defs"]["VerifiedUnit" if verify else "RepairUnit"])
        variant["required"] = list(variant["properties"])
        variant["properties"]["key"]["enum"] = [key]
        per_unit_ids = variant["properties"]["supporting_segment_ids"]
        if value["allowed_segment_ids"]:
            ids = tuple(sorted(value["allowed_segment_ids"]))
            if ids not in id_pools:
                pool = f"SupportIds{len(id_pools)}"
                id_pools[ids] = pool
                schema["$defs"][pool] = {"type": "string", "enum": list(ids)}
            per_unit_ids["items"] = {"$ref": f"#/$defs/{id_pools[ids]}"}
        else:
            per_unit_ids["items"] = {"type": "string"}
            per_unit_ids["maxItems"] = 0
        if not verify:
            kind, name, *_ = key.split(":", 2)
            allowed_fields = sorted({name} & EDITABLE_FIELDS if kind == "field" else (
                {"excerpt", "reason"} if kind == "evidence" else set()
            ))
            if kind == "evidence" and value["value"].get("evidence_type") == "demonstration":
                allowed_fields = sorted([*allowed_fields, "evidence_type"])
            if allowed_fields:
                edit = deepcopy(schema["$defs"]["RepairEdit"])
                edit["required"] = list(edit["properties"])
                edit["properties"]["field"]["enum"] = allowed_fields
                representation = "strings" if allowed_fields == ["aliases"] else (
                    "facets" if allowed_fields == ["facets"] else "text"
                )
                for unused in {"text", "strings", "facets"} - {representation}:
                    edit["properties"][unused] = {"type": "null"}
                if representation in {"strings", "facets"}:
                    edit["properties"][representation] = next(
                        option for option in edit["properties"][representation]["anyOf"]
                        if option.get("type") == "array"
                    )
                vocabulary = payload.get("facet_vocabulary", {})
                if representation == "facets" and vocabulary:
                    edit["properties"]["facets"]["items"] = {"anyOf": [
                        {"type": "object", "properties": {
                            "name": {"type": "string", "enum": [name]},
                            "values": {"type": "array", "items": {"type": "string", "enum": values}},
                        }, "required": ["name", "values"], "additionalProperties": False}
                        for name, values in vocabulary.items()
                    ]}
                variant["properties"]["edits"]["items"] = edit
                variant["properties"]["edits"]["maxItems"] = len(allowed_fields)
            else:
                variant["properties"]["edits"]["maxItems"] = 0
            if kind in {"evidence", "relation"}:
                quarantined = deepcopy(variant)
                quarantined["properties"]["quarantine"]["enum"] = [True]
                quarantined["properties"]["edits"]["maxItems"] = 0
                choices.append(quarantined)
            variant["properties"]["quarantine"]["enum"] = [False]
        choices.append(variant)
        variants[key] = {"anyOf": choices} if len(choices) > 1 else choices[0]
    schema["properties"]["units"] = {"type": "object", "properties": variants,
                                       "required": list(payload["units"]), "additionalProperties": False}
    del schema["$defs"]["VerifiedUnit" if verify else "RepairUnit"]
    input_hash = sha256_json({"prompt": prompt, "version": version, "schema": schema})
    response, provenance = _run_schema_constrained_codex(
        prompt, schema, model, config_path, audit_dir, input_hash, version,
        operation="published-repair-verify" if verify else "published-repair-draft",
        task="adjudication", budget_path=budget_path, heartbeat_callback=heartbeat_callback,
    )
    result = response.model_dump(mode="json")
    if not verify:
        for unit in result["units"]:
            if (unit["edits"] or unit["quarantine"]) and unit["status"] == "supported":
                unit["status"] = "needs_fix"
    try:
        validate_units(result["units"], payload["units"], draft=not verify)
    except ValueError as error:
        write_json(audit_dir / f"{input_hash.removeprefix('sha256:')}.repair.failure.json",
                   {**provenance, "result": result, "error": str(error)})
        raise
    if verify:
        for unit in result["units"]:
            expected = payload["units"][unit["key"]]
            findings = public_prose_findings(unit["key"], expected["value"]) if not expected.get("quarantine") else []
            if findings and unit["status"] == "supported":
                unit.update(status="needs_fix", note=" ".join(findings))
    write_json(audit_dir / f"{input_hash.removeprefix('sha256:')}.repair.json", {**provenance, "result": result})
    return result, provenance


def verify_article_with_codex(payload: dict, config_path: Path, audit_dir: Path, budget_path: Path,
                            heartbeat_callback: Callable | None = None) -> tuple[dict, dict]:
    return _model_call(payload, config_path, audit_dir, budget_path, verify=True,
                       heartbeat_callback=heartbeat_callback)


def draft_article_with_codex(payload: dict, config_path: Path, audit_dir: Path, budget_path: Path,
                           heartbeat_callback: Callable | None = None) -> tuple[dict, dict]:
    return _model_call(payload, config_path, audit_dir, budget_path, verify=False,
                       heartbeat_callback=heartbeat_callback)


def article_payloads(dossier: dict, units: dict, cap: int) -> list[dict]:
    selected_cap = max(1, cap - min(8, cap // 4))
    owned = {sid for unit in units.values() for sid in unit["allowed_segment_ids"]}
    rows = {r["id"]: r for s in dossier["sources"] for r in s["selected_rows"] if r["id"] in owned}
    context = {r["id"]: r for s in dossier["sources"] for r in s["context_rows"] if r["id"] not in rows}
    ordered = [rows[key] for key in sorted(rows)]
    chunks = [ordered[i:i+selected_cap] for i in range(0, len(ordered), selected_cap)] or [[]]
    result = []
    for index, chunk in enumerate(chunks):
        ids = {row["id"] for row in chunk}
        included = {
            key: {**value, "allowed_segment_ids": sorted(set(value["allowed_segment_ids"]) & ids)}
            for key, value in units.items()
            if key.startswith("field:") or ids & set(value["allowed_segment_ids"])
            or (index == 0 and (key.startswith("visual:") or not value["allowed_segment_ids"]))
        }
        result.append({
            "article": {key: dossier["concept"][key] for key in ("id", "label", "short_definition")},
            "units": included, "selected_rows": chunk,
            "context_rows": [context[key] for key in sorted(context)][:cap-len(chunk)],
            "source_metadata": {s["source"]["video_id"]: s["video"] for s in dossier["sources"]},
            "boundary_flags": dossier["boundary_flags"], "relation_targets": dossier["relation_targets"],
            "topic_overlap_candidates": dossier.get("topic_overlap_candidates", []),
            "chunk": index+1, "chunks": len(chunks),
        })
    return result


def verification_payloads(dossier: dict, units: dict, draft: dict, cap: int,
                          *, article_draft: dict | None = None) -> tuple[list[dict], list[dict]]:
    rows = {r["id"]: r for s in dossier["sources"] for r in s["selected_rows"]}
    context_by_id = {}
    for source in dossier["sources"]:
        surrounding = {r["id"]: r for r in source["selected_rows"] + source["context_rows"]}
        for row in source["selected_rows"]:
            context_by_id.setdefault(row["id"], {}).update(surrounding)
    groups = []
    exceptions = []
    pending = {}
    selected = set()
    context = {}
    for unit in sorted(draft["units"], key=lambda u: u["key"].startswith("field:")):
        key = unit["key"]
        if key.startswith("visual:") or unit["status"] == "needs_footage":
            exceptions.append({key: value for key, value in unit.items() if key not in {"edits", "quarantine"}})
            continue
        original = units[key]
        ids = set(unit["supporting_segment_ids"])
        if not key.startswith("field:") or not ids:
            ids = set(original["allowed_segment_ids"])
        if key.startswith("field:") and ids:
            contributing = [source for source in dossier["sources"]
                            if source["source"] in original.get("source_spans", [])
                            and ids & {row["id"] for row in source["selected_rows"]}]
            if contributing:
                # A support seed selects citations, not an outcome stripped of its owned condition.
                ids = {row["id"] for source in contributing for row in source["selected_rows"]}
                ids &= set(original["allowed_segment_ids"])
        required_context = {rid: row for sid in ids for rid, row in context_by_id.get(sid, {}).items()
                            if rid not in ids}
        if len(ids | required_context.keys()) > cap:
            exceptions.append({"key": key, "status": "uncertain", "note": PROOF_LIMIT_NOTE, "supporting_segment_ids": []})
            continue
        if pending and len(selected | ids | context.keys() | required_context.keys()) > cap:
            groups.append((pending, selected, context))
            pending, selected, context = {}, set(), {}
        pending[key] = {"source_spans": original.get("source_spans", []), "value": proposed_value(original["value"], unit),
                        "allowed_segment_ids": sorted(ids), "quarantine": unit["quarantine"]}
        selected |= ids
        context.update(required_context)
    if pending:
        groups.append((pending, selected, context))
    article_units = {u["key"]: u for u in (article_draft or draft)["units"]}
    original_topic = {key: dossier["concept"].get(key) for key in ("id", "label", "short_definition", "detailed_definition")}
    article = {key: proposed_value(value, article_units[f"field:{key}"]) if f"field:{key}" in article_units else value
               for key, value in original_topic.items()}
    return [{
        "units": group, "selected_rows": [rows[key] for key in sorted(ids)],
        "context_rows": [context[key] for key in sorted(context) if key not in ids],
        "article": article, "original_topic": original_topic,
        "source_metadata": {s["source"]["video_id"]: s["video"] for s in dossier["sources"]},
        "boundary_flags": dossier["boundary_flags"], "relation_targets": dossier["relation_targets"],
        "topic_overlap_candidates": dossier.get("topic_overlap_candidates", []),
    } for group, ids, context in groups], exceptions


def review_findings(article: dict) -> dict:
    return {key: decision["note"] for key, decision in article["decisions"].items()
            if decision and decision["status"] == "needs_fix"}


def reconcile_primary_reviews(saved: dict, audit: dict, reviews: list[dict]) -> dict:
    """Bind private reviews to exact fresh proposals, never to unchanged public content."""
    result = deepcopy(saved)
    articles = {item["concept_id"]: item for item in audit["items"]}
    seen = set()
    for review in reviews:
        cid = review["concept_id"]
        item = result["items"].get(cid)
        if cid in seen or not item or cid not in articles:
            raise ValueError(f"Unknown or duplicate primary review: {cid}")
        seen.add(cid)
        if (item.get("plan_hash") != review.get("plan_hash") or not item.get("plan_hash")
                or item["fingerprint"] != articles[cid]["fingerprint"]
                or review.get("fingerprint", item["fingerprint"]) != item["fingerprint"]):
            raise ValueError(f"Stale primary review: {cid}")
        decisions = review["decisions"]
        if (set(decisions) != {unit["key"] for unit in item["draft"]["units"]}
                or not review.get("reviewer", "").strip()
                or not isinstance(review.get("ready_for_application"), bool)):
            raise ValueError(f"Incomplete primary review: {cid}")
        for key, decision in decisions.items():
            if (decision.get("status") not in {"supported", "needs_fix", "needs_footage"}
                    or not decision.get("note", "").strip()
                    or (key.startswith("visual:") and decision["status"] != "needs_footage")):
                raise ValueError(f"Invalid primary decision: {cid}/{key}")
        if review["ready_for_application"] and any(d["status"] != "supported"
                                                 for key, d in decisions.items() if not key.startswith("visual:")):
            raise ValueError(f"Unresolved primary review cannot be ready: {cid}")
        if item.get("primary_review") != review:
            if item.get("primary_review"):
                item.setdefault("primary_review_history", []).append(item["primary_review"])
            item["primary_review"] = deepcopy(review)
            if not review["ready_for_application"]:
                item["status"] = "exceptions"
            elif all(u["status"] == "supported" or u["key"].startswith("visual:") for u in item["verification"]["units"]):
                item["status"] = "verified"
    return result


def _unchanged_draft(units: dict) -> dict:
    return {"units": [RepairUnit(key=key, status="needs_footage" if key.startswith("visual:") else "uncertain",
        note="Unchanged value awaiting exact-source review.", supporting_segment_ids=[]).model_dump() for key in units]}


def _facet_findings(value: object, vocabulary: dict) -> list[str]:
    if isinstance(value, dict) and vocabulary and any(
            name not in vocabulary or set(values) - set(vocabulary[name]) for name, values in value.items()):
        return ["Facet names/values must belong to the configured KB vocabulary."]
    return []


def _missing_source_ids(unit: dict) -> set[str]:
    return {sid for span in unit.get("source_spans", []) for sid in span["segment_ids"]} - set(unit["allowed_segment_ids"])


def run_repair_campaign(audit: dict, dossiers: dict, config_path: Path, audit_dir: Path,
                        budget_path: Path, checkpoint_path: Path, *, max_calls: int,
                        retry_failed: bool = False, drafter: Callable = draft_article_with_codex,
                        verifier: Callable = verify_article_with_codex, progress: Callable | None = None,
                        repair_confirmed: bool = False, max_articles: int = 10,
                        facet_vocabulary: dict | None = None,
                        source_context: tuple[list[Video], list[Concept]] | None = None) -> dict:
    """Bound each invocation; checkpoint every stage; never write canonical content or approvals."""
    from .published_audit import AUDIT_VERSION
    if not 0 <= max_calls <= 20 or not 1 <= max_articles <= 20:
        raise ValueError("Audit batches allow 0–20 model calls and 1–20 articles")
    config = read_yaml(config_path)["codex"]
    saved = read_json(checkpoint_path) if checkpoint_path.exists() else {"version": REPAIR_VERSION, "items": {}, "history": []}
    saved["version"] = REPAIR_VERSION
    verification_cache = saved.setdefault("verification_cache", {})
    profile = {key: config.get(key) for key in ("default_model", "reasoning_effort", "service_tier")}
    versions = {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION}
    calls = 0
    started = time.monotonic()
    recorded_tokens = visited = 0
    facet_vocabulary = facet_vocabulary or {}
    source_videos = {video.id: video for video in source_context[0]} if source_context else {}
    consecutive_transport_failures = 0
    cached_jobs = cached_units = parked_articles = 0
    stopped = "no_pending_jobs"

    def call(item: dict, name: str, payload: dict, reviewer: Callable) -> dict:
        nonlocal calls, cached_jobs, cached_units, consecutive_transport_failures, recorded_tokens
        payload = {**payload, "facet_vocabulary": facet_vocabulary}
        checking = name.startswith(("verify:", "audit:"))
        policy = VERIFICATION_VERSION if checking else DRAFT_VERSION
        digest = sha256_json({"payload": payload, "profile": profile, "version": policy,
                              "review_findings": item["review_findings"] if checking else {},
                              "primary_findings": item.get("primary_findings", {}) if checking else {}})
        job = item["jobs"].get(name)
        if job and job["digest"] != digest:
            item.setdefault("job_history", []).append({"name": name, **deepcopy(job)})
            job = None
        if job is None:
            job = item["jobs"][name] = {"status": "pending", "digest": digest}
        if job["status"] == "done":
            validate_units(job["result"]["units"], payload["units"], draft=not checking)
            cached_jobs += 1
            return job["result"]
        if job["status"] == "failed" and not retry_failed:
            raise StopIteration("failed_job")
        reused, fingerprints = {}, {}
        request = payload
        if checking:
            context = {key: value for key, value in payload.items()
                       if key not in {"units", "selected_rows", "article_fields_hash"}}
            for key, value in payload["units"].items():
                fingerprint = sha256_json({
                    "unit": {key: value}, "context": {**context,
                        "context_rows": payload.get("context_rows", []) + [r for r in payload["selected_rows"]
                            if r["id"] not in value["allowed_segment_ids"]]},
                    "profile": profile, "version": policy,
                    "review_findings": {key: item["review_findings"].get(key)},
                    "primary_findings": {key: item.get("primary_findings", {}).get(key)},
                    "primary_ready_review": sha256_json(item["primary_review"])
                    if item.get("primary_review", {}).get("ready_for_application") else None,
                    "selected_rows": [r for r in payload["selected_rows"] if r["id"] in value["allowed_segment_ids"]],
                })
                fingerprints[key] = fingerprint
                if fingerprint in verification_cache:
                    entry = verification_cache[fingerprint]
                    validate_units([entry["unit"]], {key: value}, draft=False)
                    reused[key] = entry
            pending = {key: value for key, value in payload["units"].items() if key not in reused}
            selected = {sid for unit in pending.values() for sid in unit["allowed_segment_ids"]}
            request = {**payload, "units": pending,
                       "selected_rows": [r for r in payload["selected_rows"] if r["id"] in selected],
                       "context_rows": payload.get("context_rows", []) + [r for r in payload["selected_rows"]
                           if r["id"] not in selected]}
        if request["units"] and calls >= max_calls:
            raise StopIteration("call_limit")
        message = f"{item['concept_id']} / {name}"
        if progress:
            progress(message)
        try:
            result, provenance = ({"units": []}, {"method": "cached_source_verification"})
            if request["units"]:
                calls += 1
                result, provenance = reviewer(request, config_path, audit_dir, budget_path,
                                              heartbeat_callback=(lambda: progress(f"Waiting: {message}")) if progress else None)
                recorded_tokens += usage_token_total(provenance.get("usage"))
                consecutive_transport_failures = 0
                validate_units(result["units"], request["units"], draft=not checking)
                if not checking:
                    for unit in result["units"]:
                        if unit["key"] == "field:facets" and _facet_findings(
                                proposed_value(request["units"][unit["key"]]["value"], unit), facet_vocabulary):
                            raise ValueError("Repair proposed unregistered KB facets")
            if checking:
                fresh = {unit["key"]: unit for unit in result["units"]}
                result = {"units": [fresh.get(key, reused.get(key, {}).get("unit")) for key in payload["units"]]}
                validate_units(result["units"], payload["units"], draft=False)
                for key, unit in fresh.items():
                    verification_cache[fingerprints[key]] = {"unit": unit, "provenance": provenance}
                if reused:
                    cached_units += len(reused)
                    provenance = {**provenance, "reused_units": {key: entry["provenance"] for key, entry in reused.items()}}
        except LLMBudgetExceeded:
            calls -= 1
            job["status"] = "budget_deferred"
            write_json(checkpoint_path, saved)
            raise StopIteration("budget") from None
        except (CodexError, ValueError) as error:
            recorded_tokens += usage_token_total(getattr(error, "provenance", {}).get("usage"))
            consecutive_transport_failures = consecutive_transport_failures + 1 if isinstance(error, CodexError) else 0
            job.update(status="failed", error=str(error))
            write_json(checkpoint_path, saved)
            raise StopIteration("transport_failure_circuit" if consecutive_transport_failures >= 3 else "failed_job") from error
        job.update(status="done", result=result, provenance=provenance)
        job.pop("error", None)
        write_json(checkpoint_path, saved)
        return result

    for article in audit["items"]:
        if all(value is not None and (value["status"] == "supported" or key.startswith("visual:"))
               for key, value in article["decisions"].items()):
            continue
        cid = article["concept_id"]
        item = saved["items"].get(cid)
        primary = item.get("primary_review", {}) if item else {}
        if (item and item.get("status") == "verified" and item["fingerprint"] == article["fingerprint"]
                and item.get("review_version") == REPAIR_VERSION
                and item.get("stage_versions") == versions and primary.get("ready_for_application")
                and primary.get("plan_hash") == item.get("plan_hash")):
            parked_articles += 1
            continue
        dossier = dossiers[cid]
        corrections = source_coverage_corrections(Concept.model_validate(dossier["concept"]), source_videos)
        if corrections:
            original_source_ids = {e["id"]: set(e["source"]["segment_ids"]) for e in dossier["concept"]["evidence"]}
            dossier = source_correction_dossier(dossier, corrections, *source_context)
        findings = {} if corrections else review_findings(article)
        identity = (source_correction_identity(article["fingerprint"], corrections, dossier) if corrections else
                    sha256_json({"fingerprint": article["fingerprint"], "config": config,
                                 "version": REPAIR_VERSION, "stage_versions": versions, "review_findings": findings}))
        if (not item or item["identity"] != identity or item.get("review_version") != REPAIR_VERSION
                or (corrections and item.get("planning_config") != config)):
            previous_jobs = deepcopy(item.get("jobs", {})) if item else {}
            if item:
                saved["history"].append(item)
            item = {"concept_id": cid, "fingerprint": article["fingerprint"], "identity": identity,
                    "jobs": previous_jobs, "status": "pending", "concept": dossier["concept"],
                    "review_version": REPAIR_VERSION, "stage_versions": versions, "review_findings": findings}
            if corrections:
                item.update(scope="owned_source_correction", source_corrections=corrections,
                            source_proof_fingerprint=sha256_json({"version": AUDIT_VERSION, "dossier": dossier}),
                            planning_config=deepcopy(config), previous_source_findings=review_findings(article),
                            source_coverage_added_ids={c["evidence_id"]: sorted(set(c["source"]["segment_ids"])
                                - original_source_ids[c["evidence_id"]]) for c in corrections})
            saved["items"][cid] = item
        primary = item.get("primary_review", {})
        primary_hash = sha256_json(primary)
        new_primary = bool(primary) and item.get("processed_primary_hash") != primary_hash
        proof_pending = not item.get("field_proof_attempted") and any(
            u["key"].startswith("field:") and u["status"] == "uncertain" and u["note"] == PROOF_LIMIT_NOTE
            for u in (item.get("verification") or {}).get("units", []))
        if primary and not repair_confirmed:
            parked_articles += 1
            continue
        if item["status"] in {"verified", "exceptions"} and not new_primary:
            if not (repair_confirmed and item.get("workflow") == "coverage-first"
                    and (not item.get("repair_attempted") or proof_pending)):
                parked_articles += 1
                continue
        if primary.get("ready_for_application") and item["status"] == "verified":
            parked_articles += 1
            continue
        if visited >= max_articles:
            stopped = "article_limit"
            break
        visited += 1
        units = unit_inputs(dossier, list(article["decisions"]))
        conflicts = duration_conflict_units(dossier, units)
        try:
            cap = int(config.get("max_segments_per_job", 80))
            if proof_pending and item.get("draft") and item.get("verification"):
                item.update(baseline_draft=deepcopy(item["draft"]),
                            baseline_verification=deepcopy(item["verification"]))
            if item.get("workflow") != "coverage-first" or new_primary:
                baseline = deepcopy(item.get("draft", _unchanged_draft(units)))
                validate_units(baseline["units"], units, draft=True)
                item.update(workflow="coverage-first", baseline_draft=baseline, repair_attempted=False,
                            processed_primary_hash=primary_hash, status="pending")
                # Existing complete source verdicts remain usable; proposals alone never become proof.
                item["baseline_verification"] = deepcopy(item.get("verification"))
                if new_primary:
                    item["field_proof_attempted"] = False
                    item["primary_findings"] = {key: d["note"] for key, d in primary["decisions"].items()
                                                if d["status"] == "needs_fix"}
                write_json(checkpoint_path, saved)
            draft = deepcopy(item["baseline_draft"])
            proposed = proposed_inputs(units, draft)
            if item.get("baseline_verification"):
                verification = deepcopy(item["baseline_verification"]["units"])
                validate_units(verification, proposed, draft=False)
            else:
                mechanical = {}
                for key, value in proposed.items():
                    # Old verdicts cannot approve or reject a newly completed source proof.
                    decision = None if corrections else article["decisions"][key]
                    original = next(u for u in draft["units"] if u["key"] == key)
                    if decision and not original["edits"] and not original["quarantine"]:
                        mechanical[key] = VerifiedUnit(key=key, status=decision["status"], note=decision["note"],
                            supporting_segment_ids=value["allowed_segment_ids"] if decision["status"] == "supported" else []).model_dump()
                        continue
                    notes = public_prose_findings(key, value["value"])
                    if key == "field:facets":
                        notes += _facet_findings(value["value"], facet_vocabulary)
                    if key in conflicts:
                        notes += ["Caption-duration conflict needs authoritative timing reconciliation."]
                    if _missing_source_ids(value):
                        notes += ["Owned source segment IDs are missing from the transcript; reconcile the proof first."]
                    if notes:
                        mechanical[key] = VerifiedUnit(key=key, status="needs_fix", note=" ".join(notes),
                                                       supporting_segment_ids=[]).model_dump()
                audit_draft = {"units": [u for u in draft["units"] if u["key"] not in mechanical]}
                batches, exceptions = verification_payloads(dossier, units, audit_draft, cap)
                verification = list(mechanical.values()) + exceptions + [u for index, payload in enumerate(batches)
                    for u in call(item, f"audit:{index}", payload, verifier)["units"]]
                item["baseline_verification"] = {"units": deepcopy(verification)}
                write_json(checkpoint_path, saved)
            checks = {u["key"]: u for u in verification}
            findings = {key: note for key, note in item["review_findings"].items()
                        if proposed[key]["value"] == units[key]["value"]}
            for key, note in {**findings, **item.get("primary_findings", {})}.items():
                checks[key] = VerifiedUnit(key=key, status="needs_fix", note=note, supporting_segment_ids=[]).model_dump()
            if repair_confirmed:
                failures = {key: {**value, "verifier_feedback": checks[key]["note"]}
                            for key, value in proposed.items()
                            if checks[key]["status"] == "needs_fix" and not key.startswith("visual:")
                            and (not value.get("quarantine") or key in item.get("primary_findings", {}))
                            and key not in conflicts and not _missing_source_ids(value)
                            and not primary.get("ready_for_application")}
                if not item.get("field_proof_attempted"):
                    failures.update({key: {**proposed[key], "verifier_feedback": check["note"]}
                                     for key, check in checks.items()
                                     if key.startswith("field:") and check["status"] == "uncertain"
                                     and check["note"] == PROOF_LIMIT_NOTE
                                     and not _missing_source_ids(proposed[key])})
                # Pack whole proofs; an oversized unit is an exception, never split or adjudicated by vote.
                # Authoring can select alternative citations; final verification owns its whole chosen proof.
                batches, exceptions = verification_payloads(dossier, failures, _unchanged_draft(failures), cap,
                                                            article_draft=draft)
                replacements = {}
                for index, payload in enumerate(batches):
                    for key, value in payload["units"].items():
                        value["verifier_feedback"] = failures[key]["verifier_feedback"]
                    replacements.update({u["key"]: u for u in call(item, f"draft:targeted:{index}", payload, drafter)["units"]})
                proof_fields = {u["key"]: failures[u["key"]] for u in exceptions
                                if u["key"].startswith("field:") and u["note"] == PROOF_LIMIT_NOTE}
                if proof_fields:
                    proposals = [call(item, f"draft:field-proof:{index}", payload, drafter)
                                 for index, payload in enumerate(article_payloads(dossier, proof_fields, cap))]
                    reduced = call(item, "draft:field-proof:reduce", {
                        "units": proof_fields, "selected_rows": [], "context_rows": [],
                        "chunk_proposals": proposals}, drafter)
                    replacements.update({u["key"]: u for u in reduced["units"]})
                final_units = []
                changed = set()
                proof_changed = set()
                for old in draft["units"]:
                    key = old["key"]
                    new = replacements.get(key)
                    if new:
                        edits = {e["field"]: e for e in old["edits"]}
                        edits.update({e["field"]: e for e in new["edits"]})
                        merged = {**new, "edits": [] if new["quarantine"] else list(edits.values())}
                        if merged["edits"] or merged["quarantine"]:
                            merged["status"] = "needs_fix"
                        if proposed_value(units[key]["value"], merged) != proposed[key]["value"]:
                            changed.add(key)
                        if set(merged["supporting_segment_ids"]) != set(old["supporting_segment_ids"]):
                            proof_changed.add(key)
                        final_units.append(merged)
                    else:
                        final_units.append(old)
                draft = {"units": final_units}
                validate_units(draft["units"], units, draft=True)
                topic_changed = bool(changed & {"field:label", "field:short_definition", "field:detailed_definition"})
                recheck = set(units) if topic_changed else changed | proof_changed
                if primary.get("ready_for_application"):
                    recheck |= {key for key, check in checks.items() if check["status"] != "supported"}
                if any(key.startswith("evidence:") for key in changed):
                    recheck |= {key for key in units if key.startswith("field:")}
                final_draft = {"units": [u for u in draft["units"] if u["key"] in recheck]}
                batches, exceptions = verification_payloads(dossier, units, final_draft, cap, article_draft=draft)
                for unit in exceptions + [u for index, payload in enumerate(batches)
                    for u in call(item, f"verify:targeted:{index}", payload, verifier)["units"]]:
                    checks[unit["key"]] = unit
                if proof_fields or proof_pending:
                    item["field_proof_attempted"] = True
                item["repair_attempted"] = True
            verification = [checks[key] for key in units]
            validate_units(verification, proposed_inputs(units, draft), draft=False)
            item.update(draft=draft, verification={"units": verification})
            item["status"] = "verified" if all(u["status"] == "supported" or u["key"].startswith("visual:") for u in verification) else "exceptions"
            item["plan_hash"] = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
            write_json(checkpoint_path, saved)
        except StopIteration as error:
            stopped = str(error)
            if stopped in {"call_limit", "budget", "transport_failure_circuit"}:
                break
    write_json(checkpoint_path, saved)
    return {"calls": calls, "cached_jobs": cached_jobs, "cached_verification_units": cached_units,
            "visited_articles": visited, "recorded_tokens": recorded_tokens,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "parked_articles": parked_articles, "stopped": stopped,
            "article_states": dict(Counter(i["status"] for i in saved["items"].values()))}


def render_repair_plans(saved: dict) -> str:
    lines = ["# Private published repair plans", "", "Proposals require separate verification and reviewed application. No automatic editorial approval.", ""]
    queues = {"Text and metadata": [], "Citations and relations": [], "Footage": []}
    for item in saved["items"].values():
        if item["status"] == "applied":
            continue
        verification = {u["key"]: u for u in item.get("verification", {}).get("units", [])}
        decisions = [(u["key"], verification.get(u["key"], {"status": "pending"}))
                     for u in item.get("draft", {}).get("units", [])]
        decisions.extend(verification.items())
        decisions.extend(item.get("primary_review", {}).get("decisions", {}).items())
        for label, prefixes in (("Text and metadata", ("field:",)), ("Citations and relations", ("evidence:", "relation:")),
                                ("Footage", ("visual:",))):
            if any(key.startswith(prefixes) and value["status"] != "supported" for key, value in decisions):
                queues[label].append(item["concept_id"])
    lines.extend(["## Unresolved work queues", "", "Articles may appear in more than one queue; counts are not clearance.", ""])
    for label, ids in queues.items():
        lines.append(f"- {label} ({len(ids)}): {', '.join(ids) or '(none)'}")
    lines.append("")
    for item in saved["items"].values():
        lines.extend([f"## {item['concept_id']} — {item['status']}", ""])
        for correction in item.get("source_corrections", []):
            span = correction["source"]
            lines.append(f"- Spoken source proposal for {correction['evidence_id']}: {span['url']} "
                         f"({span['start_ms']}–{span['end_ms']} ms).")
            added = item.get("source_coverage_added_ids", {}).get(correction["evidence_id"])
            if added is not None:
                lines.append(f"  Added caption IDs: {', '.join(added)}; spoken bounds unchanged.")
        verification = {u["key"]: u for u in item.get("verification", {}).get("units", [])}
        for unit in item.get("draft", {}).get("units", []):
            state = verification.get(unit["key"], {}).get("status", "pending")
            lines.append(f"- {unit['key']}: {unit['status']}; verifier: {state}. {unit['note']}")
            if state != "supported":
                lines.append(f"  Unresolved: {verification.get(unit['key'], {}).get('note', 'Source review not completed.')}")
            if unit["quarantine"]:
                lines.append("  Proposed action: quarantine; keep original record and sources.")
            for edit in unit["edits"]:
                kind, index, *_ = unit["key"].split(":", 2)
                before = item["concept"].get(edit["field"]) if kind == "field" else item["concept"]["evidence"][int(index)][edit["field"]]
                after = proposed_value(before, {**unit, "key": f"field:{edit['field']}", "edits": [edit]})
                lines.append(f"  {edit['field']}: {before!r} → {after!r}")
            lines.append(f"  Selected support IDs: {', '.join(unit['supporting_segment_ids']) or '(none)'}")
        lines.append("")
    return "\n".join(lines)


def duration_conflict_units(dossier: dict, units: dict) -> dict:
    rows = {r["id"]: r for s in dossier["sources"] for r in s["selected_rows"]}
    durations = {s["source"]["video_id"]: s["video"]["duration_ms"] for s in dossier["sources"]}
    return {key: unit for key, unit in units.items() if key.startswith(("evidence:", "relation:"))
            and any(durations.get(rows[sid]["video_id"]) and rows[sid]["start_ms"]+rows[sid]["duration_ms"] > durations[rows[sid]["video_id"]]
                    for sid in unit["allowed_segment_ids"])}


def timing_quarantine_plan(article: dict, dossier: dict) -> dict | None:
    """Prepare only objectively measured exclusions; no semantic review is credited."""
    units = duration_conflict_units(dossier, unit_inputs(dossier, list(article["decisions"])))
    if not units:
        return None
    note = "Selected caption tail exceeds cached video duration. Reconciliation is pending; reversible exclusion does not assert the spoken content is false."
    draft = {"units": [RepairUnit(key=key, status="needs_fix", note=note, supporting_segment_ids=[], quarantine=True).model_dump()
                       for key in units]}
    verification = {"units": [VerifiedUnit(key=key, status="supported", note=note,
                                           supporting_segment_ids=unit["allowed_segment_ids"]).model_dump()
                              for key, unit in units.items()]}
    item = {"concept_id": article["concept_id"], "fingerprint": article["fingerprint"],
            "identity": sha256_json({"fingerprint": article["fingerprint"], "scope": "duration_conflicts", "version": REPAIR_VERSION}),
            "concept": dossier["concept"], "scope": "duration_conflicts", "status": "verified", "jobs": {},
            "draft": draft, "verification": verification}
    item["plan_hash"] = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
    return item


def summary_format_plan(article: dict, dossier: dict) -> dict | None:
    body = direct_summary_text(dossier["concept"])
    if body is None:
        return None
    key = "field:evidence_summary"
    source_ids = unit_inputs(dossier, [key])[key]["allowed_segment_ids"]
    note = "Literal deterministic template removal only; existing claims/qualifiers preserved. Semantic review remains pending."
    draft = {"units": [RepairUnit(key=key, status="needs_fix", note=note, supporting_segment_ids=[],
                                  edits=[RepairEdit(field="evidence_summary", text=body)]).model_dump()]}
    verification = {"units": [VerifiedUnit(key=key, status="supported", note=note, supporting_segment_ids=source_ids).model_dump()]}
    item = {"concept_id": article["concept_id"], "fingerprint": article["fingerprint"], "concept": dossier["concept"],
            "identity": sha256_json({"fingerprint": article["fingerprint"], "scope": "summary_format", "version": REPAIR_VERSION}),
            "scope": "summary_format", "status": "verified", "jobs": {}, "draft": draft, "verification": verification}
    item["plan_hash"] = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
    return item


def reviewed_rating_removal_plan(item: dict, dossier: dict, reviewer: str) -> dict:
    """Remove only a rating explicitly rejected by a complete, current primary review."""
    from .published_audit import AUDIT_VERSION, _units

    expected = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
    primary = item.get("primary_review", {})
    fingerprint = sha256_json({"version": AUDIT_VERSION, "dossier": dossier})
    units = unit_inputs(dossier, list(_units(Concept.model_validate(dossier["concept"]))))
    if (not reviewer.strip() or item.get("status") == "applied"
            or item.get("plan_hash") != expected or primary.get("plan_hash") != expected
            or item.get("fingerprint") != fingerprint or primary.get("fingerprint") != fingerprint
            or set(primary.get("decisions", {})) != set(units)
            or {key for key, value in primary["decisions"].items()
                if value.get("status") != "supported"} != {"field:difficulty"}
            or primary["decisions"]["field:difficulty"]["status"] != "needs_fix"):
        raise ValueError("Rating removal requires an exact complete primary review rejecting only difficulty")
    result = deepcopy(item)
    before = proposed_inputs(units, result["draft"])
    if before["field:difficulty"]["value"] is None:
        raise ValueError("There is no proposed difficulty rating to remove")
    note = "Explicit editorial removal of unsupported optional difficulty; no replacement claim or model call."
    for unit in result["draft"]["units"]:
        if unit["key"] == "field:difficulty":
            unit.update(status="needs_fix", note=note, quarantine=False,
                        edits=[RepairEdit(field="difficulty", text=None).model_dump()])
    after = proposed_inputs(units, result["draft"])
    if after["field:difficulty"]["value"] is not None or any(
            after[key] != before[key] for key in units if key != "field:difficulty"):
        raise ValueError("Rating removal changed another reviewed unit")
    for unit in result["verification"]["units"]:
        if unit["key"] == "field:difficulty":
            unit.update(status="supported", note=note, supporting_segment_ids=[])
    validate_units(result["draft"]["units"], units, draft=True)
    validate_units(result["verification"]["units"], after, draft=False)
    result["status"] = "verified" if all(u["status"] == "supported" or u["key"].startswith("visual:")
                                        for u in result["verification"]["units"]) else "exceptions"
    result["plan_hash"] = sha256_json({key: result[key] for key in ("identity", "draft", "verification")})
    result.setdefault("primary_review_history", []).append(deepcopy(primary))
    result["primary_review"] = {**deepcopy(primary), "plan_hash": result["plan_hash"],
        "reviewer": reviewer, "reviewed_at": datetime.now(UTC).isoformat(), "ready_for_application": True}
    result["primary_review"]["decisions"]["field:difficulty"] = {"status": "supported", "note": note}
    result["editorial_transform"] = {"kind": "optional_difficulty_removal", "before_plan_hash": expected,
                                    "reviewer": reviewer, "model_calls": 0}
    return result


def _block_style(node: object) -> None:
    if hasattr(node, "fa"):
        node.fa.set_block_style()
    if isinstance(node, dict):
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return
    for child in children:
        _block_style(child)


def write_repair_archive(path: Path, archive: dict, writer: Callable = replace_with_retry) -> None:
    """Flow-list colon scalars must also parse through the repository's safe YAML reader."""
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096
    _block_style(archive)
    stream = io.StringIO()
    yaml.dump(archive, stream)
    rendered = stream.getvalue()
    if YAML(typ="safe").load(rendered) != archive:
        raise ValueError("Archive serialization changed values")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="")
    writer(temporary, path)


def source_coverage_corrections(concept: Concept, videos: dict[str, Video]) -> list[dict]:
    """Propose strictly additive actual IDs inside unchanged exact spoken bounds."""
    corrections = []
    for evidence in concept.evidence:
        source = evidence.source
        video = videos.get(source.video_id)
        if evidence.review_status != "approved" or not video or not video.duration_ms or not video.transcript:
            continue
        rows = sorted((row for row in video.transcript.segments
                       if row.start_ms >= source.start_ms and row.end_ms <= source.end_ms),
                      key=lambda row: (row.start_ms, row.id))
        if (not set(source.segment_ids) < {row.id for row in rows}
                or min(row.start_ms for row in rows) != source.start_ms
                or max(row.end_ms for row in rows) != source.end_ms):
            continue
        corrected = source.model_dump(mode="json")
        corrected["segment_ids"] = [row.id for row in rows]
        corrections.append({"evidence_id": evidence.id, "source": corrected})
    return corrections


def source_correction_dossier(dossier: dict, corrections: list[dict], videos: list[Video], concepts: list[Concept]) -> dict:
    """Rebuild owned proof from actual captions without changing canonical or visual data."""
    from .pipeline import validate_source_span
    from .published_audit import audit_dossier

    concept = Concept.model_validate(dossier["concept"])
    video_map = {v.id: v for v in videos}
    segment_map = {r.id: (v.id, r) for v in videos if v.transcript for r in v.transcript.segments}
    seen = set()
    if not isinstance(corrections, list) or not corrections:
        raise ValueError("Source corrections require a nonempty list")
    for correction in corrections:
        if not isinstance(correction, dict) or set(correction) != {"evidence_id", "source"}:
            raise ValueError("Source correction may change only the spoken source")
        evidence_id = correction["evidence_id"]
        matches = [e for e in concept.evidence if e.id == evidence_id and e.review_status == "approved"]
        if evidence_id in seen or len(matches) != 1:
            raise ValueError("Source correction identity is duplicate, missing or unapproved")
        seen.add(evidence_id)
        if not isinstance(correction["source"], dict) or set(correction["source"]) != set(SourceSpan.model_fields):
            raise ValueError("Source correction requires exact spoken-source fields")
        span = SourceSpan.model_validate(correction["source"])
        video = video_map.get(span.video_id)
        if span.video_id != matches[0].source.video_id or not video or not video.duration_ms:
            raise ValueError("Source correction needs the original video and known duration")
        if len(set(span.segment_ids)) != len(span.segment_ids):
            raise ValueError("Source correction has duplicate segment IDs")
        errors = validate_source_span(span, video, segment_map, require_transcript_segments=True)
        if errors:
            raise ValueError("Invalid source correction: " + "; ".join(errors))
        rows = [segment_map[sid][1] for sid in span.segment_ids]
        if span.start_ms != min(r.start_ms for r in rows) or span.end_ms != max(r.end_ms for r in rows):
            raise ValueError("Source correction must use the exact selected-caption envelope")
        matches[0].source = span
    concept_map = {c.id: c for c in concepts}
    concept_map[concept.id] = concept
    return audit_dossier(concept, video_map, concept_map)


def source_correction_identity(fingerprint: str, corrections: list[dict], proof: dict) -> str:
    return sha256_json({"scope": "owned_source_correction", "version": "1.0.0",
                       "original_fingerprint": fingerprint, "source_corrections": corrections, "proof": proof,
                       "stage_versions": {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION}})


def apply_reviewed_plan(paths, item: dict, dossier: dict, reviewer: str, *, writer: Callable = replace_with_retry,
                        source_context: tuple[list[Video], list[Concept]] | None = None) -> dict:
    """Archive before writing; a prepared transaction resumes only matching before/after bytes."""
    from .pipeline import load_reviewed_concepts
    from .published_audit import AUDIT_VERSION, _units

    if not reviewer.strip() or item["status"] != "verified":
        raise ValueError("A verified plan and explicit reviewer provenance are required")
    mechanical = item.get("scope") in {"duration_conflicts", "summary_format"}
    if not mechanical and item.get("review_version") != REPAIR_VERSION:
        raise ValueError("Repair verification version changed; refresh the plan")
    if not mechanical and item.get("stage_versions") != {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION}:
        raise ValueError("Repair stage policy changed; refresh the plan")
    expected = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
    if item.get("plan_hash") != expected:
        raise ValueError("Repair plan hash does not match its verified content")
    ArticleRepairResponse.model_validate(item["draft"])
    ArticleVerificationResponse.model_validate(item["verification"])
    corrections = item.get("source_corrections")
    if (item.get("scope") == "owned_source_correction") != bool(corrections):
        raise ValueError("Source corrections require their explicit application scope")
    proof = dossier
    if corrections:
        if source_context is None:
            raise ValueError("Source correction requires a fresh eligible corpus snapshot")
        if item["fingerprint"] != sha256_json({"version": AUDIT_VERSION, "dossier": dossier}):
            raise ValueError("Original source-correction fingerprint changed")
        videos, concepts = source_context
        proof = source_correction_dossier(dossier, corrections, videos, concepts)
        if (item["identity"] != source_correction_identity(item["fingerprint"], corrections, proof)
                or item.get("source_proof_fingerprint") != sha256_json({"version": AUDIT_VERSION, "dossier": proof})):
            raise ValueError("Corrected source proof changed; obtain fresh verification and primary review")
    units = unit_inputs(proof, list(_units(Concept.model_validate(proof["concept"]))))
    if item.get("scope") == "duration_conflicts":
        units = duration_conflict_units(dossier, units)
        if not units or any(not unit["quarantine"] or unit["edits"] for unit in item["draft"]["units"]):
            raise ValueError("Duration plans may only quarantine the currently measured conflicting records")
    elif item.get("scope") == "summary_format":
        body = direct_summary_text(dossier["concept"])
        units = {"field:evidence_summary": units["field:evidence_summary"]}
        edits = item["draft"]["units"]
        if body is None or len(edits) != 1 or edits[0]["quarantine"] or len(edits[0]["edits"]) != 1 or edits[0]["edits"][0]["text"] != body:
            raise ValueError("Summary format plan is not an exact template-only removal")
    validate_units(item["draft"]["units"], units, draft=True)
    validate_units(item["verification"]["units"], proposed_inputs(units, item["draft"]), draft=False)
    if any(u["status"] != "supported" and not u["key"].startswith("visual:") for u in item["verification"]["units"]):
        raise ValueError("Unresolved nonvisual verification cannot be applied")
    primary = item.get("primary_review")
    if corrections:
        if not primary or primary.get("fingerprint") != item["fingerprint"]:
            raise ValueError("Source corrections require a fresh complete primary review")
        reconcile_primary_reviews({"items": {item["concept_id"]: item}},
                                  {"items": [{"concept_id": item["concept_id"], "fingerprint": item["fingerprint"]}]}, [primary])
    if item.get("workflow") == "coverage-first" and not primary:
        raise ValueError("Coverage-first plans require an exact final primary review before application")
    if primary and (not primary["ready_for_application"] or primary["plan_hash"] != item.get("plan_hash")):
        raise ValueError("Primary review requires corrections or review of the changed final plan")
    concept = dossier["concept"]
    if concept["id"] != item["concept_id"]:
        raise ValueError("Repair plan belongs to another article")
    concept_path = paths.content / "concepts" / f"{concept['slug']}.yaml"
    if concept_path.resolve().parent != (paths.content / "concepts").resolve():
        raise ValueError("Invalid canonical concept path")
    journal_path = paths.data("manifests") / "published-repair-transaction.json"
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    previous = read_json(journal_path) if journal_path.exists() else {}
    if previous.get("state") == "prepared" or (previous.get("state") == "applied" and previous.get("plan_hash") == expected):
        transaction = read_json(journal_path)
        if transaction["plan_hash"] != expected or transaction["concept_id"] != concept["id"]:
            raise ValueError("Finish the prepared repair transaction before another plan")
        if transaction["reviewer"] != reviewer:
            raise ValueError("Resume with the original transaction reviewer")
    else:
        original = concept_path.read_bytes()
        document = yaml.load(original.decode("utf-8"))
        for unit in item["draft"]["units"]:
            kind, key, *_ = unit["key"].split(":", 2)
            if kind == "field":
                if unit["edits"]:
                    document[key] = proposed_value(document.get(key), unit)
            elif kind in {"evidence", "relation"}:
                name = "evidence" if kind == "evidence" else "relations"
                original_record = concept[name][int(key)]
                matches = [record for record in document.get(name, [])
                           if record.get("review_status", "approved") == "approved" and (
                               record.get("id") == original_record["id"]
                               and record["source"] == original_record["source"]
                               and record.get("visual_source") == original_record.get("visual_source")
                               if kind == "evidence" else
                               record["relation_type"] == original_record["relation_type"]
                               and record["target_concept_id"] == original_record["target_concept_id"]
                               and record["sources"] == original_record["sources"])]
                if len(matches) != 1:
                    raise ValueError("Canonical record identity changed or is ambiguous")
                record = matches[0]
                if unit["quarantine"]:
                    record["review_status"] = "unreviewed"
                else:
                    for edit in unit["edits"]:
                        record[edit["field"]] = edit_value(edit)
        for correction in corrections or []:
            record = next(record for record in document["evidence"] if record["id"] == correction["evidence_id"])
            if record.get("review_status", "approved") != "approved":
                # Keep an excluded original intact; completed proof does not need publication.
                continue
            record["source"] = correction["source"]
        if not mechanical:
            # The complete summary was independently reviewed; publication must not regenerate it.
            document.pop("evidence_summary_source_hash", None)
            document.pop("evidence_summary_generator", None)
        Concept.model_validate(document)
        old_terms = {normalize_text(term).casefold() for term in [concept["label"], *concept["aliases"]]}
        new_terms = {normalize_text(term).casefold() for term in [document["label"], *document.get("aliases", [])]}
        for other in (load_reviewed_concepts(paths.content / "concepts") if new_terms - old_terms else []):
            if other.id != concept["id"] and other.review_status == "approved":
                other_terms = {normalize_text(term).casefold() for term in [other.label, *other.aliases]}
                if (new_terms - old_terms) & other_terms:
                    raise ValueError("Repair introduces an existing concept label/alias collision")
        taxonomy = read_yaml(paths.config / "taxonomy.yaml").get("facets", {})
        old_invalid = {(name, value) for name, values in concept.get("facets", {}).items() for value in values
                       if name not in taxonomy or value not in taxonomy[name]}
        new_invalid = {(name, value) for name, values in document.get("facets", {}).items() for value in values
                       if name not in taxonomy or value not in taxonomy[name]}
        if new_invalid - old_invalid:
            raise ValueError("Repair facets are outside the KB taxonomy")
        stream = io.StringIO()
        yaml.dump(document, stream)
        after = stream.getvalue().encode("utf-8")
        parsed = YAML(typ="safe").load(after.decode("utf-8"))
        if parsed != document:
            raise ValueError("YAML serialization changed canonical values")
        Concept.model_validate(parsed)
        transaction = {"state": "prepared", "concept_id": concept["id"], "plan_hash": expected,
                       "reviewer": reviewer, "original": original.decode("utf-8"), "after": after.decode("utf-8"),
                       "before_hash": hashlib.sha256(original).hexdigest(), "after_hash": hashlib.sha256(after).hexdigest()}
        write_json(journal_path, transaction)
    current = hashlib.sha256(concept_path.read_bytes()).hexdigest()
    if current not in {transaction["before_hash"], transaction["after_hash"]}:
        raise ValueError("Canonical file changed during the prepared transaction")
    archive_path = paths.content / "annotations" / "published-repair-history.yaml"
    archive = YAML(typ="safe").load(archive_path) if archive_path.exists() else {"repairs": []}
    if not any(r["plan_hash"] == expected for r in archive["repairs"]):
        archive["repairs"].append({"plan_hash": expected, "concept_id": concept["id"], "reviewer": transaction["reviewer"],
                                   "reviewed_at": datetime.now(UTC).isoformat(), "previous_concept": YAML(typ="safe").load(transaction["original"]),
                                   "draft": item["draft"], "verification": item["verification"],
                                   **({"source_corrections": corrections} if corrections else {})})
        write_repair_archive(archive_path, archive, writer)
    if current == transaction["before_hash"]:
        temporary = concept_path.with_name(f".{concept_path.name}.{os.getpid()}.tmp")
        temporary.write_text(transaction["after"], encoding="utf-8", newline="")
        writer(temporary, concept_path)
    transaction["state"] = "applied"
    write_json(journal_path, transaction)
    return transaction


def rollback_repair_transaction(paths) -> None:
    """Restore only this transaction's known bytes; never overwrite an unrelated editor change."""
    journal_path = paths.data("manifests") / "published-repair-transaction.json"
    transaction = read_json(journal_path)
    concept = Concept.model_validate(YAML(typ="safe").load(transaction["original"]))
    target = paths.content / "concepts" / f"{concept.slug}.yaml"
    if target.resolve().parent != (paths.content / "concepts").resolve() or concept.id != transaction["concept_id"]:
        raise ValueError("Invalid transaction identity/path")
    current = hashlib.sha256(target.read_bytes()).hexdigest()
    if current not in {transaction["before_hash"], transaction["after_hash"]}:
        raise ValueError("Unrelated canonical edit prevents rollback")
    original = transaction["original"].encode("utf-8")
    if hashlib.sha256(original).hexdigest() != transaction["before_hash"]:
        raise ValueError("Transaction original checksum mismatch")
    temporary = target.with_name(f".{target.name}.{os.getpid()}.rollback.tmp")
    temporary.write_bytes(original)
    replace_with_retry(temporary, target)
    history_path = paths.data("manifests") / "published-repair-recovery-history.json"
    history = read_json(history_path) if history_path.exists() else []
    history.append({**transaction, "state": "rolled_back"})
    write_json(history_path, history)
    transaction["state"] = "rolled_back"
    write_json(journal_path, transaction)
