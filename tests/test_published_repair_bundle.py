from copy import deepcopy

import pytest
from ruamel.yaml import YAML
from test_published_repair import fixture_inputs, verify

from processors.models import Concept, ConceptEvidence, SourceSpan
from processors.published_audit import (
    _units,
    audit_dossier,
    build_published_audit,
    write_audit_status,
)
from processors.published_repair import (
    DRAFT_VERSION,
    REPAIR_VERSION,
    VERIFICATION_VERSION,
    RepairUnit,
    _unchanged_draft,
    apply_reviewed_plan,
    relocation_candidates,
    unit_inputs,
    validate_units,
)
from processors.published_repair_bundle import (
    _eligible,
    apply_repair_bundle,
    prepare_repair_bundle,
    record_bundle_reviews,
    review_repair_bundle,
    rollback_repair_bundle,
)
from processors.utils import read_json, read_yaml, replace_with_retry, sha256_json


def test_final_review_resumes_separately_without_prior_verdicts(tmp_path):
    paths, _, _, bundle, _ = prepare_fixture(tmp_path)
    config = tmp_path / "processors.yaml"
    seen = []

    def final(payload, *_args, **_kwargs):
        assert not {"draft", "verification", "primary_findings"} & payload.keys()
        assert payload["selected_rows"]
        seen.append(payload["article"]["id"])
        return verify(payload)

    review, report = review_repair_bundle(paths, bundle, config, max_calls=1, reviewer=final)
    assert report["calls"] == 1 and not review["ready_for_application"]
    review, report = review_repair_bundle(paths, bundle, config, max_calls=1, reviewer=final)
    assert report["calls"] == 1 and review["ready_for_application"]
    assert len(seen) == 2
    _, report = review_repair_bundle(paths, bundle, config, max_calls=0, reviewer=final)
    assert report["calls"] == 0
    config.write_text(config.read_text().replace("fixture", "changed-profile"))
    review, _ = review_repair_bundle(paths, bundle, config, max_calls=0, reviewer=final)
    assert not review["ready_for_application"]


def test_final_source_defect_returns_to_bounded_repairs_without_writes(tmp_path):
    paths, _, _, bundle, _ = prepare_fixture(tmp_path)
    before = {p: p.read_bytes() for p in (paths.content / "concepts").glob("*.yaml")}

    def reject(payload, *_args, **_kwargs):
        result, provenance = verify(payload)
        result["units"][0].update(status="uncertain", note="Source does not establish the stated subject.")
        return result, provenance

    review, report = review_repair_bundle(paths, bundle, tmp_path / "processors.yaml", max_calls=20, reviewer=reject)
    assert report["stopped"] == "final_review_findings"
    assert not review["ready_for_application"] and bundle["status"] == "pending"
    assert before == {p: p.read_bytes() for p in before}
    plans = read_json(paths.data("manifests") / "published-repair-bundle-plans.json")
    assert all(item["primary_review"]["ready_for_application"] is False for item in plans["items"].values())


def test_final_review_error_keeps_partial_checkpoint_and_blocks_application(tmp_path):
    from processors.codex_engine import CodexError

    paths, _, _, bundle, _ = prepare_fixture(tmp_path)

    def fail(*_args, **_kwargs):
        raise CodexError("transport failure")

    review, report = review_repair_bundle(paths, bundle, tmp_path / "processors.yaml", reviewer=fail)
    assert report["stopped"] == "review_failed"
    assert not review["ready_for_application"]
    saved = read_json(paths.data("manifests") / "published-repair-bundle-primary.json")
    assert saved["last_error"] == "transport failure" and saved["jobs"] == {}


def test_new_transaction_preserves_previous_original_byte_journal(tmp_path):
    from processors.utils import write_json

    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)
    previous = {"bundle_hash": "sha256:previous", "state": "applied", "files": [{"before": "original"}]}
    write_json(paths.data("manifests") / "published-repair-bundle-transaction.json", previous)
    apply_repair_bundle(paths, bundle, review, concepts, videos)
    assert read_json(paths.data("manifests") / "repair-bundle-history/previous.transaction.json") == previous


def test_coordinator_shares_budget_and_resumes_through_actual_application(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from processors import cli
    from processors.utils import write_json

    paths, _, videos, bundle, _ = prepare_fixture(tmp_path)
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    write_json(paths.data("manifests") / "published-repair-plans.json",
               {"items": {cid: {"status": "verified"} for cid in bundle["origins"]}})

    def snapshot(_paths):
        current = [_eligible(read_yaml(p)) for p in (paths.content / "concepts").glob("*.yaml")]
        ledger = paths.data("manifests") / "published-audit.json"
        return current, videos, build_published_audit(current, videos, paths.id,
            read_json(ledger) if ledger.exists() else None)

    monkeypatch.setattr(cli, "_published_audit_inputs", snapshot)
    monkeypatch.setattr(cli, "run_repair_campaign", lambda *_a, **_kw: {"calls": 1, "stopped": "fixture"})
    budgets = []

    def prepare(*_a, **kw):
        budgets.append(kw["max_calls"])
        return bundle, {"calls": 1, "stopped": "fixture"}

    monkeypatch.setattr(cli, "prepare_repair_bundle", prepare)
    monkeypatch.setattr(cli, "review_repair_bundle", lambda *a, **kw: review_repair_bundle(*a, reviewer=verify, **kw))
    runner = CliRunner()
    result = runner.invoke(cli.app, ["continue-published-repairs", "--kb", paths.id, "--max-calls", "3"])
    assert result.exit_code == 0, result.output
    assert "call_limit" in result.output and budgets == [2]
    assert not (paths.data("manifests") / "published-repair-bundle-transaction.json").exists()
    result = runner.invoke(cli.app, ["continue-published-repairs", "--kb", paths.id, "--max-calls", "3"])
    assert result.exit_code == 0, result.output
    assert "applied_reviewed_bundle" in result.output
    assert read_json(paths.data("manifests") / "published-audit-status.json")["summary"]["article_status"] == {"supported": 2}


def test_final_model_call_has_distinct_prompt_policy_and_operation(tmp_path, monkeypatch):
    import processors.published_repair as repair

    _, config, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    payload = repair.article_payloads(dossier, units, 80)[0]

    def transport(prompt, schema, model, _config, _directory, _digest, version, **kwargs):
        assert "FINAL independent editorial source review" in prompt
        assert version == repair.PRIMARY_REVIEW_VERSION
        assert kwargs["operation"] == "published-repair-primary"
        return model.model_validate(verify(payload)[0]), {"operation": kwargs["operation"]}

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", transport)
    result, provenance = repair.review_article_with_codex(payload, config, tmp_path, tmp_path / "budget.json")
    assert result["units"] and provenance["operation"] == "published-repair-primary"


@pytest.mark.parametrize("overlap_only", [False, True])
def test_coordinator_parks_unchanged_exception_and_selects_next_article(tmp_path, monkeypatch, overlap_only):
    from typer.testing import CliRunner

    from processors import cli
    from processors.utils import write_json

    paths, _, concepts, videos, _ = bundle_fixture(tmp_path)
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    audit = build_published_audit(concepts, videos, paths.id)
    if overlap_only:
        for item in audit["items"]:
            item["decisions"] = {key: {"status": "supported", "note": "Prior review"} for key in item["decisions"]}
            item["overlap_review_pending"] = True
    monkeypatch.setattr(cli, "_published_audit_inputs", lambda _paths: (concepts, videos, audit))
    seen = []

    def blocked(audit, *_a, **_kw):
        assert all(d is None for d in audit["items"][0]["decisions"].values())
        cid = audit["items"][0]["concept_id"]
        seen.append(cid)
        write_json(paths.data("manifests") / "published-repair-plans.json",
                   {"items": {cid: {"status": "exceptions"}}})
        return {"calls": 0, "stopped": "no_pending_jobs", "parked_articles": 1}

    monkeypatch.setattr(cli, "run_repair_campaign", blocked)
    for _ in range(2):
        result = CliRunner().invoke(cli.app, ["continue-published-repairs", "--kb", paths.id])
        assert result.exit_code == 0, result.output
    assert len(set(seen)) == 2


@pytest.mark.parametrize("explicit", [False, True])
def test_coordinator_resumes_progressing_repair_and_discards_premature_park(tmp_path, monkeypatch, explicit):
    from typer.testing import CliRunner

    from processors import cli
    from processors.utils import write_json

    paths, _, concepts, videos, _ = bundle_fixture(tmp_path)
    audit = build_published_audit(concepts, videos, paths.id)
    first = audit["items"][0]
    workflow_path = paths.data("manifests") / "published-repair-workflow.json"
    write_json(workflow_path, {"parked": {first["concept_id"]: {
        "fingerprint": first["fingerprint"], "reason": "no_pending_jobs"}},
        "visits": {first["concept_id"]: {"fingerprint": "old-source", "count": 99}}})
    write_json(paths.data("manifests") / "published-repair-plans.json", {"items": {
        first["concept_id"]: {"fingerprint": "old-source", "stage_versions": {"draft": DRAFT_VERSION}}}})
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    monkeypatch.setattr(cli, "_published_audit_inputs", lambda _paths: (concepts, videos, audit))
    seen = []

    def progressing(selected, *_a, **_kw):
        cid = selected["items"][0]["concept_id"]
        seen.append(cid)
        write_json(paths.data("manifests") / "published-repair-plans.json", {"items": {
            cid: {"status": "exceptions", "repair_progress": True, "repair_rounds": 1}}})
        return {"calls": 3, "visited_articles": 1, "parked_articles": 0, "stopped": "no_pending_jobs"}

    monkeypatch.setattr(cli, "run_repair_campaign", progressing)
    for _ in range(2):
        args = ["continue-published-repairs", "--kb", paths.id]
        if explicit:
            args.extend(["--concept-ids", first["concept_id"]])
        result = CliRunner().invoke(cli.app, args)
        assert result.exit_code == 0, result.output
        assert not read_json(workflow_path)["parked"]
    assert seen == ([first["concept_id"]] * 2 if explicit else [a["concept_id"] for a in audit["items"]])


def test_coordinator_finishes_baseline_coverage_before_deep_repair_revisit(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from processors import cli
    from processors.utils import write_json

    paths, _, concepts, videos, _ = bundle_fixture(tmp_path)
    audit = build_published_audit(concepts, videos, paths.id)
    first, second = audit["items"]
    items = {a["concept_id"]: {"fingerprint": a["fingerprint"],
        "stage_versions": {"draft": DRAFT_VERSION}, "status": "pending"} for a in audit["items"]}
    items[first["concept_id"]]["baseline_verification"] = {"units": [{"key": key} for key in first["decisions"]]}
    items[second["concept_id"]]["baseline_verification"] = None
    write_json(paths.data("manifests") / "published-repair-plans.json", {"items": items})
    write_json(paths.data("manifests") / "published-repair-workflow.json", {"parked": {}, "visits": {
        a["concept_id"]: {"fingerprint": a["fingerprint"], "count": n} for a, n in [(first, 0), (second, 5)]}})
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    monkeypatch.setattr(cli, "_published_audit_inputs", lambda _paths: (concepts, videos, audit))
    selected = []

    def probe(chosen, *_a, **_kw):
        selected.extend(a["concept_id"] for a in chosen["items"])
        return {"calls": 0, "stopped": "call_limit"}

    monkeypatch.setattr(cli, "run_repair_campaign", probe)
    result = CliRunner().invoke(cli.app, ["continue-published-repairs", "--kb", paths.id])
    assert result.exit_code == 0, result.output
    assert selected == [second["concept_id"]]


def bundle_fixture(tmp_path):
    paths, config, _, dossiers = fixture_inputs(tmp_path)
    origin = Concept.model_validate(dossiers["concept-stance"]["concept"])
    from processors.models import TranscriptTrack, Video

    video = Video(
        id="video",
        title="Fixture",
        canonical_url="https://www.youtube.com/watch?v=video",
        duration_ms=9000,
        transcript=TranscriptTrack(
            video_id="video",
            language="English",
            language_code="en",
            is_generated=False,
            acquisition_method="fixture",
            segments=dossiers[origin.id]["sources"][0]["selected_rows"],
        ),
    )
    source = SourceSpan(
        video_id="video",
        start_ms=0,
        end_ms=3000,
        url="https://www.youtube.com/watch?v=video&t=0s",
        segment_ids=["video:00000"],
    )
    origin.evidence.append(
        ConceptEvidence(
            id="move",
            excerpt="Keep a stable stance.",
            reason="Maintain balance.",
            confidence=0.9,
            evidence_type="explanation",
            source=source,
        )
    )
    target = origin.model_copy(
        deep=True,
        update={
            "id": "concept-balance",
            "slug": "balance",
            "label": "Body balance",
            "short_definition": "Maintain a stable balanced body.",
            "evidence": [origin.evidence[0].model_copy(update={"id": "existing"})],
        },
    )
    for concept in [origin, target]:
        with (paths.content / "concepts" / f"{concept.slug}.yaml").open(
            "w", encoding="utf-8"
        ) as handle:
            YAML().dump(concept.model_dump(mode="json"), handle)
    concepts = [origin, target]
    dossier = audit_dossier(origin, {"video": video}, {c.id: c for c in concepts})
    units = unit_inputs(dossier, list(_units(origin)))
    proposal = _unchanged_draft(units)
    for unit in proposal["units"]:
        if unit["key"].endswith(":move"):
            unit.update(quarantine=True, status="needs_fix", destination_concept_id=target.id)
    audit = build_published_audit(concepts, [video], paths.id)
    item = {
        "concept_id": origin.id,
        "fingerprint": audit["items"][1]["fingerprint"],
        "status": "verified",
        "review_version": REPAIR_VERSION,
        "stage_versions": {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION},
        "identity": "fixture",
        "draft": proposal,
        "verification": verify({"units": units})[0],
    }
    item["fingerprint"] = next(
        a["fingerprint"] for a in audit["items"] if a["concept_id"] == origin.id
    )
    item["plan_hash"] = sha256_json({k: item[k] for k in ["identity", "draft", "verification"]})
    return paths, config, concepts, [video], {"items": {origin.id: item}}


def prepare_fixture(tmp_path, **kwargs):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    for _ in range(4):
        bundle, _ = prepare_repair_bundle(
            paths,
            plans,
            concepts,
            videos,
            ["concept-stance"],
            config,
            max_calls=20,
            verifier=verify,
            **kwargs,
        )
        if bundle["status"] == "verified":
            break
    assert bundle["status"] == "verified"
    review = deepcopy(bundle["review_template"])
    review.update(reviewer="Fixture source reviewer", ready_for_application=True)
    for decisions in review["decisions"].values():
        for key in decisions:
            decisions[key] = {"status": "supported", "note": "Actual fixture source read."}
    return paths, concepts, videos, bundle, review


def test_bundle_retains_instruction_applies_idempotently_and_rolls_back(tmp_path):
    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)
    before = {p: p.read_bytes() for p in (paths.content / "concepts").glob("*.yaml")}
    apply_repair_bundle(paths, bundle, review, concepts, videos)
    assert (
        next(
            e
            for e in read_yaml(paths.content / "concepts/stance.yaml")["evidence"]
            if e["id"] == "move"
        )["review_status"]
        == "unreviewed"
    )
    assert (
        next(
            e
            for e in read_yaml(paths.content / "concepts/balance.yaml")["evidence"]
            if e["id"] == "move"
        )["review_status"]
        == "approved"
    )
    apply_repair_bundle(paths, bundle, review, concepts, videos)
    current = [_eligible(read_yaml(p)) for p in before]
    audit = build_published_audit(current, videos, paths.id)
    updated = record_bundle_reviews(bundle, review, current, videos, audit)
    assert all(
        d and d["status"] == "supported" for a in updated["items"] for d in a["decisions"].values()
    )
    rollback_repair_bundle(paths)
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_bundle_interruption_resumes_same_transaction_after_destination_write(tmp_path):
    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)

    def interrupt(source, destination):
        if destination.name == "stance.yaml":
            raise OSError("Interrupted origin write")
        replace_with_retry(source, destination)

    with pytest.raises(OSError, match="Interrupted"):
        apply_repair_bundle(paths, bundle, review, concepts, videos, writer=interrupt)
    assert any(
        e["id"] == "move" for e in read_yaml(paths.content / "concepts/balance.yaml")["evidence"]
    )
    apply_repair_bundle(paths, bundle, review, concepts, videos)
    assert (
        read_json(paths.data("manifests") / "published-repair-bundle-transaction.json")["state"]
        == "applied"
    )


@pytest.mark.parametrize(
    "fault",
    ["no_review", "partial", "stale_review", "changed_source", "changed_target", "changed_other"],
)
def test_bundle_rejects_stale_or_incomplete_review_without_canonical_writes(tmp_path, fault):
    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)
    if fault == "no_review":
        review["ready_for_application"] = False
    if fault == "partial":
        review["decisions"]["concept-stance"].pop("field:label")
    if fault == "stale_review":
        review["bundle_hash"] = "old"
    if fault == "changed_source":
        videos[0].transcript.segments[0].text = "Different instruction."
    if fault == "changed_target":
        with (paths.content / "concepts/balance.yaml").open("a", encoding="utf-8") as f:
            f.write("\n# unrelated edit\n")
    if fault == "changed_other":
        (paths.content / "concepts/other.yaml").write_text("unrelated: edit\n", encoding="utf-8")
    before = {p: p.read_bytes() for p in (paths.content / "concepts").glob("*.yaml")}
    with pytest.raises(ValueError):
        apply_repair_bundle(paths, bundle, review, concepts, videos)
    assert all(p.read_bytes() == b for p, b in before.items())


def test_relocation_is_not_an_unverified_single_article_exclusion(tmp_path):
    paths, _, concepts, videos, plans = bundle_fixture(tmp_path)
    item = plans["items"]["concept-stance"]
    dossier = audit_dossier(concepts[0], {v.id: v for v in videos}, {c.id: c for c in concepts})
    with pytest.raises(ValueError, match="multi-article"):
        apply_reviewed_plan(paths, item, dossier, "Reviewer")
    units = unit_inputs(dossier, list(_units(concepts[0])))
    unit = RepairUnit(
        key="evidence:1:move",
        status="needs_fix",
        note="Misplaced.",
        supporting_segment_ids=[],
        quarantine=True,
        destination_concept_id="invented",
    ).model_dump()
    with pytest.raises(ValueError, match="supplied destination"):
        validate_units([unit], {unit["key"]: units[unit["key"]]}, draft=True)
    assert (
        relocation_candidates(units["evidence:1:move"]["value"], concepts[0].id, concepts)[0]["id"]
        == "concept-balance"
    )


def test_generated_status_covers_full_visual_inventory_and_only_updates_opted_in_regions(tmp_path):
    paths, _, concepts, videos, _ = bundle_fixture(tmp_path)
    audit = build_published_audit(concepts, videos, paths.id)
    audit["items"][0]["decisions"]["visual:0:proposed"] = None
    audit["items"][1]["decisions"]["visual:1:held"] = {
        "status": "needs_footage",
        "note": "Not watched.",
    }
    marker = "<!-- audit-status:fixture:start -->stale<!-- audit-status:fixture:end -->"
    (tmp_path / "README.md").write_text("Before " + marker + " after", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    untouched = tmp_path / "docs/other.md"
    untouched.write_text("Leave unchanged.", encoding="utf-8")
    status = write_audit_status(paths, audit)
    assert status["visual_windows"] == status["unverified_visual_windows"] == 2
    assert len(status["remaining_articles"]) == 2
    assert "2/2 actual visual windows unverified" in (tmp_path / "README.md").read_text(
        encoding="utf-8"
    )
    assert untouched.read_text() == "Leave unchanged."


def test_bundle_finite_jobs_resume_from_saved_checkpoints(tmp_path):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    before = {p: p.read_bytes() for p in (paths.content / "concepts").glob("*.yaml")}
    reports = []
    for _ in range(6):
        bundle, report = prepare_repair_bundle(
            paths, plans, concepts, videos, ["concept-stance"], config, max_calls=1, verifier=verify
        )
        reports.append(report)
        assert report["calls"] <= 1
        if bundle["status"] == "verified":
            break
    assert bundle["status"] == "verified"
    assert sum(r["calls"] for r in reports) == 2
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert bundle["review_template"]["ready_for_application"] is False


def test_rejected_destination_cannot_archive_origin(tmp_path):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    before = {p: p.read_bytes() for p in (paths.content / "concepts").glob("*.yaml")}

    def reject(payload, *_args, **_kwargs):
        result, provenance = verify(payload)
        for unit in result["units"]:
            if payload["article"]["id"] == "concept-balance" and unit["key"].endswith(":move"):
                unit.update(
                    status="needs_fix", note="This destination does not own the instruction."
                )
        return result, provenance

    def unchanged(payload, *_args, **_kwargs):
        return _unchanged_draft(payload["units"]), {}

    bundle, _ = prepare_repair_bundle(
        paths,
        plans,
        concepts,
        videos,
        ["concept-stance"],
        config,
        max_calls=10,
        verifier=reject,
        drafter=unchanged,
    )
    assert bundle["status"] != "verified"
    with pytest.raises(ValueError, match="primary review"):
        apply_repair_bundle(paths, bundle, bundle["review_template"], concepts, videos)
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_source_edit_during_bundle_write_keeps_recoverable_unapproved_journal(tmp_path):
    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)

    def edit_source(source, destination):
        replace_with_retry(source, destination)
        paths.data("normalized").mkdir(parents=True, exist_ok=True)
        (paths.data("normalized") / "changed.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="during application"):
        apply_repair_bundle(paths, bundle, review, concepts, videos, writer=edit_source)
    journal = read_json(paths.data("manifests") / "published-repair-bundle-transaction.json")
    assert journal["state"] == "prepared"
    rollback_repair_bundle(paths)


def test_bundle_retry_refuses_unrelated_edit_after_partial_write(tmp_path):
    paths, concepts, videos, bundle, review = prepare_fixture(tmp_path)

    def interrupt(source, destination):
        if destination.name == "stance.yaml":
            raise OSError("Interrupted")
        replace_with_retry(source, destination)

    with pytest.raises(OSError):
        apply_repair_bundle(paths, bundle, review, concepts, videos, writer=interrupt)
    path = paths.content / "concepts" / "balance.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n# user edit\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unrelated edit"):
        apply_repair_bundle(paths, bundle, review, concepts, videos)
    with pytest.raises(ValueError, match="Unrelated edit"):
        rollback_repair_bundle(paths)


def test_bundle_cli_applies_complete_review_and_exports_status(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from processors import cli
    from processors.utils import write_json

    paths, _, videos, bundle, review = prepare_fixture(tmp_path)
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)

    def snapshot(_paths):
        current = [_eligible(read_yaml(p)) for p in (paths.content / "concepts").glob("*.yaml")]
        ledger = paths.data("manifests") / "published-audit.json"
        return (
            current,
            videos,
            build_published_audit(
                current, videos, paths.id, read_json(ledger) if ledger.exists() else None
            ),
        )

    monkeypatch.setattr(cli, "_published_audit_inputs", snapshot)
    review_path = tmp_path / "review.json"
    write_json(review_path, review)
    result = CliRunner().invoke(
        cli.app,
        ["apply-published-repair-bundle", "--kb", paths.id, "--review-file", str(review_path)],
    )
    assert result.exit_code == 0, result.output
    status = read_json(paths.data("manifests") / "published-audit-status.json")
    assert status["summary"]["article_status"] == {"supported": 2}
    assert len(bundle["documents"]) == 2


def test_round_trip_bundle_retains_unrelated_yaml_comments(tmp_path):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    path = paths.content / "concepts" / "balance.yaml"
    path.write_text(
        "# Keep this editorial note.\n" + path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    for _ in range(4):
        bundle, _ = prepare_repair_bundle(
            paths,
            plans,
            concepts,
            videos,
            ["concept-stance"],
            config,
            max_calls=20,
            verifier=verify,
        )
        if bundle["status"] == "verified":
            break
    review = deepcopy(bundle["review_template"])
    review.update(reviewer="Fixture reader", ready_for_application=True)
    for decisions in review["decisions"].values():
        for key in decisions:
            decisions[key] = {"status": "supported", "note": "Source read."}
    apply_repair_bundle(paths, bundle, review, concepts, videos)
    assert path.read_text(encoding="utf-8").startswith("# Keep this editorial note.\n")


def test_changed_relation_target_brings_dependant_into_verification_bundle(tmp_path):
    from processors.models import ConceptRelation

    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    dependent = concepts[1].model_copy(
        deep=True, update={"id": "dependent", "slug": "dependent", "label": "Related stance"}
    )
    dependent.relations = [
        ConceptRelation(
            relation_type="related_to",
            target_concept_id="concept-stance",
            confidence=0.9,
            sources=[concepts[0].evidence[0].source],
        )
    ]
    with (paths.content / "concepts/dependent.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(dependent.model_dump(mode="json"), handle)
    concepts.append(dependent)
    item = plans["items"]["concept-stance"]
    dossier = audit_dossier(concepts[0], {v.id: v for v in videos}, {c.id: c for c in concepts})
    from processors.published_audit import AUDIT_VERSION

    item["fingerprint"] = sha256_json({"version": AUDIT_VERSION, "dossier": dossier})
    field = next(u for u in item["draft"]["units"] if u["key"] == "field:short_definition")
    field.update(
        status="needs_fix",
        edits=[
            {
                "field": "short_definition",
                "text": "Keep a balanced stable stance.",
                "strings": None,
                "facets": None,
            }
        ],
    )
    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    seen = set()
    prior_dossier = audit_dossier(dependent, {v.id:v for v in videos}, {c.id:c for c in concepts})
    prior_draft = _unchanged_draft(unit_inputs(prior_dossier, list(_units(dependent))))
    cue = next(u for u in prior_draft['units'] if u['key'].startswith('evidence:'))
    cue.update(status='needs_fix', edits=[{'field':'reason','text':'Keep a stable stance.',
                                         'strings':None,'facets':None}])
    plans['history'] = [{'concept_id':'dependent','fingerprint':sha256_json({'version':AUDIT_VERSION,'dossier':prior_dossier}),
                         'draft':prior_draft,'stage_versions':{'draft':'older','verification':'older'}}]
    retained_checks = []

    def tracked(payload, *_args, **_kwargs):
        seen.add(payload["article"]["id"])
        if payload['article']['id'] == 'dependent':
            retained_checks.extend(v['value']['reason'] for k,v in payload['units'].items() if k == cue['key'])
        return verify(payload)

    for _ in range(4):
        bundle, _ = prepare_repair_bundle(
            paths,
            plans,
            concepts,
            videos,
            ["concept-stance"],
            config,
            max_calls=20,
            verifier=tracked,
        )
        if bundle["status"] == "verified":
            break
    assert bundle["status"] == "verified"
    assert "dependent" in bundle["documents"] and "dependent" in seen
    assert retained_checks and retained_checks[0] == 'Keep a stable stance.'

def test_bundle_reuses_exact_origin_evidence_proof_after_projection(tmp_path):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    plans['items']['concept-stance']['planning_config'] = read_yaml(config)['codex']
    field = next(u for u in plans['items']['concept-stance']['draft']['units'] if u['key'] == 'field:short_definition')
    field['supporting_segment_ids'] = field['supporting_segment_ids'][:1]
    item = plans['items']['concept-stance']
    item['plan_hash'] = sha256_json({k:item[k] for k in ('identity','draft','verification')})
    seen = []
    def checking(payload, *_args, **_kwargs):
        if payload['article']['id'] == 'concept-stance':
            seen.extend(payload['units'])
        return verify(payload)
    bundle, _ = prepare_repair_bundle(paths, plans, concepts, videos, ['concept-stance'], config,
                                     max_calls=20, verifier=checking)
    assert 'evidence:0:e' not in seen
    assert bundle['source_proof_reuse']['concept-stance']['unit_proofs']
    assert any(key.startswith('field:') for key in seen)
    generated = read_json(paths.data('manifests')/'published-repair-bundle-plans.json')['items']['concept-stance']
    selected = next(u for u in generated['baseline_draft']['units'] if u['key'] == 'field:short_definition')
    assert selected['supporting_segment_ids'] == field['supporting_segment_ids']
    assert not selected['edits'] and not selected['quarantine']
    for _ in range(3):
        if bundle['status'] == 'verified':
            break
        bundle, _ = prepare_repair_bundle(paths, plans, concepts, videos, ['concept-stance'], config,
                                         max_calls=20, verifier=verify)
    assert bundle['status'] == 'verified'


def test_overlap_only_neighbour_is_not_subject_to_full_source_reaudit(tmp_path):
    paths, config, concepts, videos, plans = bundle_fixture(tmp_path)
    neighbour = concepts[0].model_copy(deep=True, update={'id':'neighbour','slug':'neighbour','label':'Brief stance cue'})
    neighbour.evidence = [concepts[0].evidence[-1].model_copy(deep=True)]
    neighbour.relations = []
    with (paths.content/'concepts/neighbour.yaml').open('w',encoding='utf-8') as f:
        YAML().dump(neighbour.model_dump(mode='json'),f)
    concepts.append(neighbour)
    item = plans['items']['concept-stance']
    from processors.published_audit import AUDIT_VERSION
    d = audit_dossier(concepts[0],{v.id:v for v in videos},{c.id:c for c in concepts})
    item['fingerprint'] = sha256_json({'version':AUDIT_VERSION,'dossier':d})
    item['plan_hash'] = sha256_json({k:item[k] for k in ('identity','draft','verification')})
    bundle, _ = prepare_repair_bundle(paths,plans,concepts,videos,['concept-stance'],config,
                                     max_calls=20,verifier=verify)
    assert 'neighbour' not in bundle['documents']


def test_bundle_eligibility_matches_public_fixture_exclusion(tmp_path):
    from processors.models import ConceptRelation
    _, _, concepts, _, _ = bundle_fixture(tmp_path)
    document = concepts[0].model_dump(mode='json')
    fixture = deepcopy(document['evidence'][0])
    fixture['id'] = 'demo-only'
    fixture['source']['video_id'] = 'demo'
    document['evidence'].append(fixture)
    document['relations'] = [ConceptRelation(relation_type='related_to', target_concept_id='other',
        confidence=.9, sources=[document['evidence'][0]['source'],fixture['source']]).model_dump(mode='json')]
    before = deepcopy(document)
    public = _eligible(document, {'demo'})
    assert all(e.source.video_id != 'demo' for e in public.evidence)
    assert len(public.relations[0].sources) == 1
    assert document == before
