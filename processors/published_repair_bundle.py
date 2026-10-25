"""Shared, private multi-article retention plans and recoverable reviewed application."""

import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from io import StringIO

from ruamel.yaml import YAML

from .codex_engine import CodexError
from .llm_budget import LLMBudgetExceeded
from .models import Concept
from .pipeline import validate_corpus
from .published_audit import (
    AUDIT_VERSION,
    _units,
    audit_dossier,
    build_published_audit,
    record_audit_reviews,
)
from .published_repair import (
    DRAFT_VERSION,
    PRIMARY_REVIEW_VERSION,
    REPAIR_VERSION,
    VERIFICATION_VERSION,
    _unchanged_draft,
    project_repair_document,
    proposed_inputs,
    reconcile_primary_reviews,
    recover_draft,
    relocation_candidates,
    review_article_with_codex,
    run_repair_campaign,
    source_correction_dossier,
    unit_inputs,
    validate_units,
    verification_payloads,
)
from .utils import read_json, read_yaml, replace_with_retry, sha256_json, write_json

BUNDLE_VERSION = "1.0.1"


def _eligible(document, excluded_video_ids=()):
    concept = Concept.model_validate(document)
    return concept.model_copy(
        update={
            "evidence": [e for e in concept.evidence if e.review_status == "approved"
                         and e.source.video_id not in excluded_video_ids],
            "relations": [r.model_copy(update={"sources": [s for s in r.sources
                          if s.video_id not in excluded_video_ids]})
                          for r in concept.relations if r.review_status == "approved"
                          and any(s.video_id not in excluded_video_ids for s in r.sources)],
        }
    )


def _environment(paths, videos, affected):
    return sha256_json(
        {
            "videos": [v.model_dump(mode="json") for v in videos],
            "normalized_files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(paths.data("normalized").glob("*.json"))
            },
            "other_concepts": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((paths.content / "concepts").glob("*.yaml"))
                if p.stem not in affected
            },
            "taxonomy": read_yaml(paths.config / "taxonomy.yaml"),
            "processor_config": read_yaml(paths.root / "config" / "processors.yaml")
            if (paths.root / "config" / "processors.yaml").exists()
            else None,
        }
    )


def _bundle_hash(bundle):
    return sha256_json(
        {k: v for k, v in bundle.items() if k not in {"bundle_hash", "review_template", "last_run"}}
    )


def _extend_dependants(paths, documents, before, concepts, videos):
    """Relation changes need checks; overlap-only changes use the separate advisory ledger."""
    excluded = {v.id for v in videos.values() if v.availability == "demo_fixture"}
    projected = {**concepts, **{cid: _eligible(doc, excluded) for cid, doc in documents.items()}}
    added = False
    for cid, concept in concepts.items():
        if cid in documents:
            continue
        original = audit_dossier(concept, videos, concepts)
        proposed = audit_dossier(concept, videos, projected)
        if original["relation_targets"] == proposed["relation_targets"]:
            continue
        path = paths.content / "concepts" / f"{concept.slug}.yaml"
        documents[cid] = read_yaml(path)
        before[cid] = {
            "slug": concept.slug,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        added = True
    if len(documents) > 20:
        raise ValueError(
            "Affected dependency bundle exceeds 20 articles; use smaller origin batches"
        )
    return added


def _merge_document(node, value):
    """Keep untouched YAML nodes/comments while applying the verified semantic delta."""
    if isinstance(node, dict) and isinstance(value, dict):
        for key in set(node) - set(value):
            del node[key]
        for key, new in value.items():
            node[key] = _merge_document(node[key], new) if key in node else deepcopy(new)
        return node
    if isinstance(node, list) and isinstance(value, list):
        for i, new in enumerate(value):
            if i < len(node):
                node[i] = _merge_document(node[i], new)
            else:
                node.append(deepcopy(new))
        del node[len(value) :]
        return node
    return node if node == value else deepcopy(value)


def prepare_repair_bundle(
    paths, plans, concepts, videos, concept_ids, config_path, *, max_calls=10, **campaign_options
):
    """Project saved proposals, retain moved records, and verify the resulting corpus; no approval."""
    if not concept_ids or len(concept_ids) != len(set(concept_ids)) or len(concept_ids) > 20:
        raise ValueError("Choose 1–20 unique origin articles")
    cm = {c.id: c for c in concepts}
    vm = {v.id: v for v in videos}
    excluded = sorted(v.id for v in videos if v.availability == "demo_fixture")
    documents, origins, moves = {}, {}, []
    origin_proofs = {}
    for cid in concept_ids:
        item = plans["items"][cid]
        dossier = audit_dossier(cm[cid], vm, cm)
        fingerprint = sha256_json({"version": AUDIT_VERSION, "dossier": dossier})
        if (
            item.get("fingerprint") != fingerprint
            or item.get("status") != "verified"
            or item.get("review_version") != REPAIR_VERSION
            or item.get("stage_versions")
            != {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION}
            or item.get("plan_hash")
            != sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
        ):
            raise ValueError("Origin requires a fresh verified repair plan")
        proof = (
            source_correction_dossier(dossier, item["source_corrections"], videos, concepts)
            if item.get("source_corrections")
            else dossier
        )
        units = unit_inputs(proof, [u["key"] for u in item["draft"]["units"]])
        for key, unit in units.items():
            if key.startswith("evidence:"):
                unit["relocation_candidates"] = relocation_candidates(unit["value"], cid, concepts)
        validate_units(item["draft"]["units"], units, draft=True)
        validate_units(
            item["verification"]["units"], proposed_inputs(units, item["draft"]), draft=False
        )
        if any(
            u["status"] != "supported" and not u["key"].startswith("visual:")
            for u in item["verification"]["units"]
        ):
            raise ValueError("Origin still has unverified written claims")
        if item.get("planning_config") == read_yaml(config_path)["codex"]:
            from .published_repair import _evidence_proof_fingerprints
            origin_proofs[cid] = _evidence_proof_fingerprints(proof, item["draft"],
                int(item["planning_config"].get("max_segments_per_job", 80)), include_original_topic=False)
        path = paths.content / "concepts" / f"{cm[cid].slug}.yaml"
        documents[cid] = project_repair_document(read_yaml(path), item, dossier)
        origins[cid] = item["plan_hash"]
        for unit in item["draft"]["units"]:
            target = unit.get("destination_concept_id")
            if not target:
                continue
            if target not in cm or target == cid or not unit["quarantine"]:
                raise ValueError("Relocation needs an existing different reviewed destination")
            record = deepcopy(proof["concept"]["evidence"][int(unit["key"].split(":")[1])])
            record["review_status"] = "approved"
            moves.append(
                {
                    "origin": cid,
                    "destination": target,
                    "evidence_id": record["id"],
                    "record": record,
                }
            )
    for move in moves:
        cid = move["destination"]
        documents.setdefault(cid, read_yaml(paths.content / "concepts" / f"{cm[cid].slug}.yaml"))
        if any(e["id"] == move["evidence_id"] for e in documents[cid]["evidence"]):
            raise ValueError("Destination already contains this evidence ID; reconcile explicitly")
        documents[cid]["evidence"].append(move["record"])
    if len(documents) > 20:
        raise ValueError("Bundle exceeds the finite 20-article limit")
    before = {}
    for cid in documents:
        path = paths.content / "concepts" / f"{cm[cid].slug}.yaml"
        before[cid] = {
            "slug": cm[cid].slug,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    _extend_dependants(paths, documents, before, cm, vm)
    environment = _environment(paths, videos, {v["slug"] for v in before.values()})
    identity = sha256_json(
        {
            "version": BUNDLE_VERSION,
            "origins": origins,
            "documents": documents,
            "before": before,
            "environment": environment,
            "policy": [DRAFT_VERSION, VERIFICATION_VERSION],
            "excluded_video_ids": excluded,
        }
    )
    path = paths.data("manifests") / "published-repair-bundle.json"
    bundle = read_json(path) if path.exists() else {}
    if bundle.get("identity") != identity:
        journal = paths.data("manifests") / "published-repair-bundle-transaction.json"
        if journal.exists() and read_json(journal).get("state") == "prepared":
            raise ValueError("Resume or roll back the prepared bundle transaction first")
        if bundle:
            write_json(
                paths.data("manifests")
                / "repair-bundle-history"
                / f"{bundle['identity'].removeprefix('sha256:')}.json",
                bundle,
            )
        bundle = {
            "version": BUNDLE_VERSION,
            "identity": identity,
            "before": before,
            "environment": environment,
            "origins": origins,
            "documents": documents,
            "moves": moves,
            "pass": 0,
            "status": "pending",
            "policy": [DRAFT_VERSION, VERIFICATION_VERSION],
            "excluded_video_ids": excluded,
        }
    if bundle.get("status") == "verified":
        return bundle, {"calls": 0, "stopped": "ready_for_primary_review"}
    if bundle["pass"] >= 3:
        return bundle, {"calls": 0, "stopped": "bundle_revision_limit"}
    projected = {cid: _eligible(doc, excluded) for cid, doc in bundle["documents"].items()}
    full = {**cm, **projected}
    if any(not c.evidence for c in projected.values()):
        raise ValueError("A bundle cannot silently remove an entire public article")
    errors = validate_corpus(list(full.values()), videos)
    if errors:
        raise ValueError("Bundle corpus invalid: " + "; ".join(errors))
    dossiers = {cid: audit_dossier(c, vm, full) for cid, c in projected.items()}
    audit = build_published_audit(list(projected.values()), videos, paths.id)
    for article in audit["items"]:
        article["fingerprint"] = sha256_json(
            {"version": AUDIT_VERSION, "dossier": dossiers[article["concept_id"]]}
        )
        cid = article["concept_id"]
        if cid not in origins:
            original = audit_dossier(cm[cid], vm, cm)
            fingerprint = sha256_json({"version": AUDIT_VERSION, "dossier": original})
            seed = recover_draft([*plans.get("history", []), *plans["items"].values()], dossiers[cid],
                unit_inputs(dossiers[cid], list(article["decisions"])), fingerprint)
            if seed:
                article["proposal_seed"] = seed
        if cid in origin_proofs:
            from .published_repair import _evidence_proof_fingerprints
            after_units = unit_inputs(dossiers[cid], list(article["decisions"]))
            seed = _unchanged_draft(after_units)
            prior_units = {u["key"]: u for u in plans["items"][cid]["draft"]["units"]}
            for unit in seed["units"]:
                if unit["key"].startswith("field:"):
                    ids = prior_units[unit["key"]]["supporting_segment_ids"]
                    if set(ids) <= set(after_units[unit["key"]]["allowed_segment_ids"]):
                        unit["supporting_segment_ids"] = ids
            article["proposal_seed"] = seed
            after_proofs = _evidence_proof_fingerprints(dossiers[cid], _unchanged_draft(after_units),
                int(read_yaml(config_path)["codex"].get("max_segments_per_job", 80)), include_original_topic=False)
            before_keys = {k.split(":", 2)[2]: k for k in origin_proofs[cid]}
            checks = {u["key"]: u for u in plans["items"][cid]["verification"]["units"]}
            reused = {}
            for key, digest in after_proofs.items():
                old_key = before_keys.get(key.split(":", 2)[2])
                if old_key and digest == origin_proofs[cid][old_key]:
                    check = {**checks[old_key], "key": key}
                    validate_units([check], {key: after_units[key]}, draft=False)
                    article["decisions"][key] = check
                    reused[key] = digest
            bundle.setdefault("source_proof_reuse", {})[cid] = {
                "plan_hash": plans["items"][cid]["plan_hash"], "unit_proofs": reused}
    checkpoint = paths.data("manifests") / "published-repair-bundle-plans.json"
    report = run_repair_campaign(
        audit,
        dossiers,
        config_path,
        paths.data("manifests") / "published-audit-model",
        paths.data("manifests") / "llm-budget.json",
        checkpoint,
        max_calls=max_calls,
        max_articles=len(projected),
        repair_confirmed=True,
        source_context=(videos, list(full.values())),
        facet_vocabulary=read_yaml(paths.config / "taxonomy.yaml").get("facets", {}),
        topic_identity_rules=read_yaml(paths.config / "taxonomy.yaml").get("topic_identity_rules", []),
        **campaign_options,
    )
    generated = read_json(checkpoint)["items"]
    if all(cid in generated and generated[cid].get("status") == "verified" for cid in projected):
        revised = {}
        for cid in projected:
            item = generated[cid]
            if any(u.get("destination_concept_id") for u in item["draft"]["units"]):
                raise ValueError(
                    "A destination requires another relocation; inspect the saved bundle plan"
                )
            revised[cid] = project_repair_document(bundle["documents"][cid], item, dossiers[cid])
        for move in moves:
            record = next(
                (
                    e
                    for e in revised[move["destination"]]["evidence"]
                    if e["id"] == move["evidence_id"]
                ),
                None,
            )
            if not record or record.get("review_status") != "approved":
                raise ValueError(
                    "Destination rejected retained evidence; origin cannot be archived"
                )
            if record.get("visual_source") != move["record"].get("visual_source"):
                raise ValueError("Relocation changed a visual window")
        dependencies_added = _extend_dependants(paths, revised, bundle["before"], cm, vm)
        if sha256_json(revised) != sha256_json(bundle["documents"]) or dependencies_added:
            bundle.update(documents=revised, status="pending", **{"pass": bundle["pass"] + 1})
            bundle["environment"] = _environment(
                paths, videos, {v["slug"] for v in bundle["before"].values()}
            )
        else:
            bundle.update(
                status="verified",
                dossiers=dossiers,
                verification={cid: generated[cid]["verification"] for cid in projected},
            )
    bundle["last_run"] = report
    bundle["bundle_hash"] = _bundle_hash(bundle)
    bundle["review_template"] = {
        "bundle_hash": bundle["bundle_hash"],
        "reviewer": "",
        "ready_for_application": False,
        "decisions": {cid: {key: None for key in _units(c)} for cid, c in projected.items()},
    }
    write_json(path, bundle)
    return bundle, report


def _validate_review(bundle, review):
    if (
        bundle.get("version") != BUNDLE_VERSION
        or bundle.get("status") != "verified"
        or bundle.get("bundle_hash") != _bundle_hash(bundle)
        or bundle.get("policy") != [DRAFT_VERSION, VERIFICATION_VERSION]
        or review.get("bundle_hash") != bundle["bundle_hash"]
        or review.get("ready_for_application") is not True
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or set(review.get("decisions", {})) != set(bundle["documents"])
    ):
        raise ValueError("Fresh complete bundle primary review is required")
    for cid, dossier in bundle["dossiers"].items():
        units = unit_inputs(dossier, list(_units(_eligible(bundle["documents"][cid], bundle.get("excluded_video_ids", ())))))
        validate_units(bundle["verification"][cid]["units"], units, draft=False)
        if set(review["decisions"][cid]) != set(units):
            raise ValueError("Primary review must cover every final unit")
        for key, decision in review["decisions"][cid].items():
            if (
                not isinstance(decision, dict)
                or not isinstance(decision.get("note"), str)
                or not decision["note"].strip()
            ):
                raise ValueError("Source-grounded primary review notes are required")
            if key.startswith("visual:"):
                if decision.get("status") not in {"needs_footage", "supported"} or (
                    decision["status"] == "supported"
                    and decision.get("watched_full_clip") is not True
                ):
                    raise ValueError("Visual approval requires complete clip inspection")
            elif decision.get("status") != "supported":
                raise ValueError("Unresolved written primary findings cannot apply")
        if any(
            u["status"] != "supported" and not u["key"].startswith("visual:")
            for u in bundle["verification"][cid]["units"]
        ):
            raise ValueError("Independent written verification is unresolved")


def review_repair_bundle(paths, bundle, config_path, *, max_calls=4,
                         reviewer=review_article_with_codex, progress=None):
    """Separate final source reading; exact cached jobs, no verifier verdicts or visual approval."""
    if not 0 <= max_calls <= 20:
        raise ValueError("Final review allows 0–20 calls")
    if bundle.get("status") != "verified" or bundle.get("bundle_hash") != _bundle_hash(bundle):
        raise ValueError("Final review requires a verified unchanged bundle")
    config = read_yaml(config_path)
    identity = sha256_json({"bundle": bundle["bundle_hash"], "config": config,
                            "version": PRIMARY_REVIEW_VERSION})
    checkpoint = paths.data("manifests") / "published-repair-bundle-primary.json"
    saved = read_json(checkpoint) if checkpoint.exists() else {}
    if saved.get("identity") != identity:
        saved = {"identity": identity, "jobs": {}}
    review = deepcopy(bundle["review_template"])
    profile = config["codex"]
    review.update(reviewer=f"{profile['default_model']}/{profile.get('reasoning_effort', 'low')} final source review",
                  policy=PRIMARY_REVIEW_VERSION, profile=profile)
    calls, stopped = 0, "review_complete"
    for cid, dossier in bundle["dossiers"].items():
        from .topic_identity import topic_identity_findings
        conflicts = topic_identity_findings(dossier["concept"], dossier["sources"],
            read_yaml(paths.config / "taxonomy.yaml").get("topic_identity_rules", []))
        if conflicts:
            review["ready_for_application"] = False
            review["topic_identity_holds"] = {cid: conflicts}
            write_json(paths.data("manifests") / "published-repair-bundle-review.json", review)
            return review, {"calls": calls, "stopped": "topic_identity_hold"}
        units = unit_inputs(dossier, list(review["decisions"][cid]))
        proof_selection = _unchanged_draft(units)
        seeds = {u["key"]: u["supporting_segment_ids"] for u in bundle["verification"][cid]["units"]}
        for unit in proof_selection["units"]:
            if unit["key"].startswith("field:"):
                unit["supporting_segment_ids"] = seeds.get(unit["key"], [])
        batches, exceptions = verification_payloads(dossier, units, proof_selection,
                                                    int(profile.get("max_segments_per_job", 80)))
        for unit in exceptions:
            review["decisions"][cid][unit["key"]] = unit
        for payload in batches:
            payload["facet_vocabulary"] = read_yaml(paths.config / "taxonomy.yaml").get("facets", {})
            key = sha256_json({"identity": identity, "article": cid, "payload": payload})
            job = saved["jobs"].get(key)
            if job is None:
                if calls >= max_calls:
                    stopped = "call_limit"
                    continue
                message = f"{cid} / final source review"
                if progress:
                    progress(message)
                try:
                    calls += 1
                    result, provenance = reviewer(payload, config_path,
                        paths.data("manifests") / "published-audit-primary-model",
                        paths.data("manifests") / "llm-budget.json",
                        heartbeat_callback=(lambda message=message: progress(f"Waiting: {message}")) if progress else None)
                    validate_units(result["units"], payload["units"], draft=False)
                    job = {"result": result, "provenance": provenance}
                    saved["jobs"][key] = job
                    write_json(checkpoint, saved)
                except (LLMBudgetExceeded, CodexError, ValueError) as error:
                    saved["last_error"] = str(error)
                    write_json(checkpoint, saved)
                    review["ready_for_application"] = False
                    write_json(paths.data("manifests") / "published-repair-bundle-review.json", review)
                    return review, {"calls": calls, "stopped": "budget" if isinstance(error, LLMBudgetExceeded) else "review_failed"}
            validate_units(job["result"]["units"], payload["units"], draft=False)
            for unit in job["result"]["units"]:
                review["decisions"][cid][unit["key"]] = unit
    complete = all(d is not None for ds in review["decisions"].values() for d in ds.values())
    review["ready_for_application"] = complete and all(
        d["status"] == "supported" or (key.startswith("visual:") and d["status"] == "needs_footage")
        for ds in review["decisions"].values() for key, d in ds.items())
    if review["ready_for_application"]:
        _validate_review(bundle, review)
    elif complete:
        # Feed actual final-review defects back to the existing bounded repair loop.
        checkpoint_plans = paths.data("manifests") / "published-repair-bundle-plans.json"
        plans = read_json(checkpoint_plans)
        reviews, articles = [], []
        for cid, decisions in review["decisions"].items():
            item = plans["items"][cid]
            articles.append({"concept_id": cid, "fingerprint": item["fingerprint"]})
            reviews.append({"concept_id": cid, "plan_hash": item["plan_hash"],
                "fingerprint": item["fingerprint"], "reviewer": review["reviewer"],
                "ready_for_application": False,
                "decisions": {key: {**d, "status": "needs_fix" if d["status"] == "uncertain" else d["status"]}
                              for key, d in decisions.items()}})
        write_json(checkpoint_plans, reconcile_primary_reviews(plans, {"items": articles}, reviews))
        bundle["status"] = "pending"
        bundle["pass"] += 1
        bundle["bundle_hash"] = _bundle_hash(bundle)
        write_json(paths.data("manifests") / "published-repair-bundle.json", bundle)
        stopped = "final_review_findings"
    write_json(paths.data("manifests") / "published-repair-bundle-review.json", review)
    return review, {"calls": calls, "stopped": stopped}


def apply_repair_bundle(paths, bundle, review, concepts, videos, *, writer=replace_with_retry):
    """Journal all before/after bytes; destination writes precede archival; retry only exact states."""
    _validate_review(bundle, review)
    from .topic_identity import topic_identity_findings
    rules = read_yaml(paths.config / "taxonomy.yaml").get("topic_identity_rules", [])
    if any(topic_identity_findings(d["concept"], d["sources"], rules) for d in bundle["dossiers"].values()):
        raise ValueError("Unresolved topic identity conflict; installation held")
    slugs = {v["slug"] for v in bundle["before"].values()}
    if _environment(paths, videos, slugs) != bundle["environment"]:
        raise ValueError("Bundle source, taxonomy or other article changed")
    jp = paths.data("manifests") / "published-repair-bundle-transaction.json"
    journal = read_json(jp) if jp.exists() else {}
    if journal.get("state") == "prepared" or (
        journal.get("state") == "applied" and journal.get("bundle_hash") == bundle["bundle_hash"]
    ):
        if journal.get("bundle_hash") != bundle["bundle_hash"] or journal.get(
            "review_hash"
        ) != sha256_json(review):
            raise ValueError("Resume with the same bundle and reviewer")
    else:
        full = {c.id: c for c in concepts}
        full.update({cid: _eligible(doc, {v.id for v in videos if v.availability == "demo_fixture"})
                     for cid, doc in bundle["documents"].items()})
        errors = validate_corpus(list(full.values()), videos)
        if errors:
            raise ValueError("Reviewed bundle corpus invalid: " + "; ".join(errors))
        vm = {v.id: v for v in videos}
        for cid in bundle["documents"]:
            if sha256_json(audit_dossier(full[cid], vm, full)) != sha256_json(
                bundle["dossiers"][cid]
            ):
                raise ValueError("Final source or relation proof changed")
        files = []
        targets = {m["destination"] for m in bundle["moves"]}
        yaml = YAML()
        yaml.width = 4096
        for cid in sorted(bundle["documents"], key=lambda cid: (cid not in targets, cid)):
            before = bundle["before"][cid]
            path = paths.content / "concepts" / f"{before['slug']}.yaml"
            if path.resolve().parent != (paths.content / "concepts").resolve():
                raise ValueError("Invalid bundle canonical path")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != before["sha256"]:
                raise ValueError("Canonical file changed since bundle preparation")
            out = StringIO()
            yaml.preserve_quotes = True
            rendered = _merge_document(yaml.load(raw.decode("utf-8")), bundle["documents"][cid])
            yaml.dump(rendered, out)
            after = out.getvalue()
            if sha256_json(YAML(typ="safe").load(after)) != sha256_json(bundle["documents"][cid]):
                raise ValueError("Bundle YAML serialization changed values")
            files.append(
                {
                    "slug": before["slug"],
                    "before": raw.decode("utf-8"),
                    "after": after,
                    "before_hash": before["sha256"],
                    "after_hash": hashlib.sha256(after.encode()).hexdigest(),
                }
            )
        journal = {
            "state": "prepared",
            "bundle_hash": bundle["bundle_hash"],
            "review_hash": sha256_json(review),
            "reviewer": review["reviewer"],
            "at": datetime.now(UTC).isoformat(),
            "files": files,
        }
        if jp.exists():
            previous = read_json(jp)
            write_json(paths.data("manifests") / "repair-bundle-history"
                       / f"{previous['bundle_hash'].removeprefix('sha256:')}.transaction.json", previous)
        write_json(jp, journal)
    for item in journal["files"]:
        if item["slug"] not in slugs:
            raise ValueError("Unexpected canonical path in bundle journal")
        path = paths.content / "concepts" / f"{item['slug']}.yaml"
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        if current not in {item["before_hash"], item["after_hash"]}:
            raise ValueError("Unrelated edit blocks bundle recovery")
    for item in journal["files"]:
        path = paths.content / "concepts" / f"{item['slug']}.yaml"
        if hashlib.sha256(path.read_bytes()).hexdigest() == item["before_hash"]:
            temp = path.with_suffix(".yaml.bundle.tmp")
            temp.write_text(item["after"], encoding="utf-8", newline="")
            writer(temp, path)
    if _environment(paths, videos, slugs) != bundle["environment"]:
        raise ValueError(
            "Source inputs changed during application; retain the journal and roll back"
        )
    journal["state"] = "applied"
    write_json(jp, journal)
    return journal


def record_bundle_reviews(bundle, review, concepts, videos, audit):
    _validate_review(bundle, review)
    cm, vm = {c.id: c for c in concepts}, {v.id: v for v in videos}
    reviews = []
    for cid in bundle["documents"]:
        if sha256_json(audit_dossier(cm[cid], vm, cm)) != sha256_json(bundle["dossiers"][cid]):
            raise ValueError("Installed bundle differs from verified proposal")
        item = next(x for x in audit["items"] if x["concept_id"] == cid)
        reviews.append(
            {
                "concept_id": cid,
                "fingerprint": item["fingerprint"],
                "reviewer": review["reviewer"],
                "decisions": review["decisions"][cid],
            }
        )
    return record_audit_reviews(audit, reviews)


def rollback_repair_bundle(paths, *, writer=replace_with_retry):
    jp = paths.data("manifests") / "published-repair-bundle-transaction.json"
    journal = read_json(jp)
    if journal.get("state") not in {"prepared", "applied"}:
        raise ValueError("No bundle transaction to roll back")
    for item in journal["files"]:
        path = paths.content / "concepts" / f"{item['slug']}.yaml"
        if path.resolve().parent != (paths.content / "concepts").resolve() or hashlib.sha256(
            path.read_bytes()
        ).hexdigest() not in {item["before_hash"], item["after_hash"]}:
            raise ValueError("Unrelated edit blocks bundle rollback")
        if hashlib.sha256(item["before"].encode()).hexdigest() != item["before_hash"]:
            raise ValueError("Bundle archive changed")
    for item in reversed(journal["files"]):
        path = paths.content / "concepts" / f"{item['slug']}.yaml"
        temp = path.with_suffix(".yaml.bundle-rollback.tmp")
        temp.write_text(item["before"], encoding="utf-8", newline="")
        writer(temp, path)
    journal["state"] = "rolled_back"
    write_json(jp, journal)
