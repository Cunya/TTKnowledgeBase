from copy import deepcopy
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from processors.models import Concept, ConceptEvidence, Segment, SourceSpan, TranscriptTrack, Video
from processors.published_audit import audit_dossier, build_published_audit
from processors.published_repair import (
    RepairUnit,
    VerifiedUnit,
    apply_reviewed_plan,
    article_payloads,
    reconcile_primary_reviews,
    render_repair_plans,
    rollback_repair_transaction,
    run_repair_campaign,
    source_coverage_corrections,
    summary_format_plan,
    timing_quarantine_plan,
    unit_inputs,
    validate_units,
    verification_payloads,
)
from processors.utils import read_json, read_yaml, sha256_json, write_json
from processors.workspace import KnowledgeBasePaths


def rating_plan_fixture(tmp_path):
    from processors.published_audit import AUDIT_VERSION, _units
    from processors.published_repair import (
        DRAFT_VERSION,
        REPAIR_VERSION,
        VERIFICATION_VERSION,
        _unchanged_draft,
    )

    paths, _, _, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    dossier["concept"]["difficulty"] = "intermediate"
    concept = Concept.model_validate(dossier["concept"])
    with (paths.content / "concepts/stance.yaml").open("w", encoding="utf-8") as f:
        YAML().dump(dossier["concept"], f)
    units = unit_inputs(dossier, list(_units(concept)))
    item = {"concept_id": concept.id, "identity": "fixture", "status": "exceptions",
            "fingerprint": sha256_json({"version": AUDIT_VERSION, "dossier": dossier}),
            "draft": _unchanged_draft(units), "concept": dossier["concept"], "workflow": "coverage-first",
            "review_version": REPAIR_VERSION, "stage_versions": {"draft": DRAFT_VERSION, "verification": VERIFICATION_VERSION},
            "verification": {"units": [VerifiedUnit(key=k, status="supported", note="Reviewed source.",
                supporting_segment_ids=v["allowed_segment_ids"]).model_dump() for k, v in units.items()]}}
    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    item["primary_review"] = {**primary_review(item, ready=False), "fingerprint": item["fingerprint"]}
    item["primary_review"]["decisions"]["field:difficulty"] = {"status": "needs_fix", "note": "Unsupported rating."}
    return paths, item, dossier


def test_reviewed_rating_removal_exact_delta_and_archive(tmp_path):
    from processors.published_repair import proposed_inputs, reviewed_rating_removal_plan

    paths, item, dossier = rating_plan_fixture(tmp_path)
    result = reviewed_rating_removal_plan(item, dossier, "Editor authorized removal")
    units = unit_inputs(dossier, [u["key"] for u in item["draft"]["units"]])
    before, after = proposed_inputs(units, item["draft"]), proposed_inputs(units, result["draft"])
    assert [k for k in before if before[k] != after[k]] == ["field:difficulty"]
    assert after["field:difficulty"]["value"] is None
    assert result["editorial_transform"]["model_calls"] == 0
    assert not item["primary_review"]["ready_for_application"]
    apply_reviewed_plan(paths, result, dossier, "Editor authorized removal")
    assert read_yaml(paths.content / "concepts/stance.yaml")["difficulty"] is None
    archive = read_yaml(paths.content / "annotations/published-repair-history.yaml")
    assert archive["repairs"][0]["previous_concept"]["difficulty"] == "intermediate"


@pytest.mark.parametrize("fault", ["stale_primary", "stale_source", "partial", "other_finding", "unreviewed_rating"])
def test_rating_removal_rejects_invalid_review(tmp_path, fault):
    from processors.published_repair import reviewed_rating_removal_plan

    _, item, dossier = rating_plan_fixture(tmp_path)
    if fault == "stale_primary":
        item["primary_review"]["plan_hash"] = "old"
    elif fault == "stale_source":
        dossier["sources"][0]["selected_rows"][0]["text"] = "Different source."
    elif fault == "partial":
        item["primary_review"]["decisions"].pop("field:label")
    elif fault == "other_finding":
        item["primary_review"]["decisions"]["field:label"]["status"] = "needs_fix"
    else:
        item["primary_review"]["decisions"]["field:difficulty"]["status"] = "needs_footage"
    with pytest.raises(ValueError, match="exact complete primary"):
        reviewed_rating_removal_plan(item, dossier, "Editor")


def test_rating_removal_keeps_other_machine_exception(tmp_path):
    from processors.published_repair import reviewed_rating_removal_plan

    _, item, dossier = rating_plan_fixture(tmp_path)
    item["verification"]["units"][0]["status"] = "uncertain"
    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    item["primary_review"]["plan_hash"] = item["plan_hash"]
    assert reviewed_rating_removal_plan(item, dossier, "Editor")["status"] == "exceptions"


def fixture_inputs(tmp_path: Path, rows: int = 3):
    paths = KnowledgeBasePaths(tmp_path, "fixture", "Fixture", "Test")
    paths.config.mkdir(parents=True)
    paths.content.joinpath("concepts").mkdir(parents=True)
    paths.content.joinpath("annotations").mkdir()
    paths.config.joinpath("taxonomy.yaml").write_text("facets:\n  category: [fundamentals]\n", encoding="utf-8")
    config = tmp_path / "processors.yaml"
    config.write_text("codex:\n  default_model: fixture\n  max_segments_per_job: 80\n", encoding="utf-8")
    segments = [Segment(id=f"video:{i:05d}", video_id="video", text="Keep a stable stance.",
                        normalized_text="Keep a stable stance.", start_ms=i*3000, duration_ms=3000)
                for i in range(rows)]
    video = Video(id="video", title="Fixture", canonical_url="https://www.youtube.com/watch?v=video",
                  duration_ms=rows*3000, transcript=TranscriptTrack(video_id="video", language="English",
                  language_code="en", is_generated=False, acquisition_method="fixture", segments=segments))
    source = SourceSpan(video_id="video", start_ms=0, end_ms=rows*3000,
                        url=video.canonical_url+"&t=0s", segment_ids=[s.id for s in segments])
    concept = Concept(id="concept-stance", slug="stance", label="Stable stance", aliases=[],
                      short_definition="Keep a stable stance.", evidence_summary="Maintain balance before playing.",
                      concept_type="concept", facets={"category": ["fundamentals"]},
                      evidence=[ConceptEvidence(id="e", evidence_type="explanation", excerpt="Keep a stable stance.",
                      reason="Maintain balance.", confidence=0.9, visual_status="not_visual", source=source)])
    with (paths.content / "concepts/stance.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(concept.model_dump(mode="json"), handle)
    audit = build_published_audit([concept], [video], paths.id)
    dossier = audit_dossier(concept, {video.id: video}, {concept.id: concept})
    return paths, config, audit, {concept.id: dossier}


def draft(payload, *_args, **_kwargs):
    units = []
    for key, value in payload["units"].items():
        edits = []
        if key == "field:short_definition":
            edits = [{"field": "short_definition", "text": "A stable stance supports balance."}]
        units.append(RepairUnit(key=key, status="needs_fix" if edits else "supported", note="Fixture support inspected.",
                                supporting_segment_ids=value["allowed_segment_ids"][:1], edits=edits).model_dump())
    return {"units": units}, {"method": "fixture_draft"}


def verify(payload, *_args, **_kwargs):
    return {"units": [VerifiedUnit(key=key, status="supported", note="Separate selected-source check.",
                                  supporting_segment_ids=value["allowed_segment_ids"][:1]).model_dump()
                       for key, value in payload["units"].items()]}, {"method": "fixture_verify"}


def ready_plan(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    for key in audit["items"][0]["decisions"]:
        audit["items"][0]["decisions"][key] = {"status": "needs_fix" if key == "field:short_definition" else "supported", "note": "Fixture primary review."}
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    write_json(paths.data("manifests") / "published-audit.json", audit)
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=verify, repair_confirmed=True)
    assert result["article_states"] == {"verified": 1}
    saved = read_json(checkpoint)
    item = saved["items"]["concept-stance"]
    saved = reconcile_primary_reviews(saved, audit, [primary_review(item)])
    write_json(checkpoint, saved)
    return paths, saved["items"]["concept-stance"], dossiers["concept-stance"]


def source_plan_fixture(tmp_path):
    from processors.published_audit import AUDIT_VERSION
    from processors.published_repair import source_correction_dossier, source_correction_identity

    paths, item, dossier = ready_plan(tmp_path)
    concept = Concept.model_validate(dossier["concept"])
    video = Video(id="video", title="Fixture", canonical_url="https://www.youtube.com/watch?v=video", duration_ms=9000,
                  transcript=TranscriptTrack(video_id="video", language="English", language_code="en", is_generated=False,
                      acquisition_method="fixture", segments=dossier["sources"][0]["selected_rows"]))
    paths.data("normalized").mkdir(parents=True)
    write_json(paths.data("normalized") / "video.json", video.model_dump(mode="json"))
    source = concept.evidence[0].source.model_dump(mode="json")
    source.update(end_ms=6000, segment_ids=source["segment_ids"][:2])
    changes = [{"evidence_id": "e", "source": source}]
    proof = source_correction_dossier(dossier, changes, [video], [concept])
    item.update(scope="owned_source_correction", source_corrections=changes,
                source_proof_fingerprint=sha256_json({"version": AUDIT_VERSION, "dossier": proof}),
                identity=source_correction_identity(item["fingerprint"], changes, proof))
    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    item["primary_review"] = primary_review(item)
    return paths, item, dossier, ([video], [concept])


def test_source_completion_preserves_quarantined_original_source(tmp_path):
    paths, item, dossier, context = source_plan_fixture(tmp_path)
    target = paths.content / "concepts/stance.yaml"
    before = target.read_bytes()
    unit = next(unit for unit in item["draft"]["units"] if unit["key"].startswith("evidence:"))
    unit.update(quarantine=True, edits=[], note="Complete source review supports omission of this citation.")
    item["plan_hash"] = sha256_json({key: item[key] for key in ("identity", "draft", "verification")})
    item["primary_review"] = primary_review(item)
    apply_reviewed_plan(paths, item, dossier, "Source editor", source_context=context)
    record = read_yaml(target)["evidence"][0]
    assert record["review_status"] == "unreviewed"
    assert record["source"] == dossier["concept"]["evidence"][0]["source"]
    assert record["visual_source"] == dossier["concept"]["evidence"][0]["visual_source"]
    archive = read_yaml(paths.content / "annotations/published-repair-history.yaml")["repairs"]
    assert archive[0]["source_corrections"] == item["source_corrections"]
    rollback_repair_transaction(paths)
    assert target.read_bytes() == before


def test_source_correction_archives_original_and_resumes_transaction(tmp_path):
    from processors.utils import replace_with_retry

    paths, item, dossier, context = source_plan_fixture(tmp_path)
    target = paths.content / "concepts/stance.yaml"
    before = target.read_bytes()

    def interrupted(source, destination):
        if destination == target:
            raise OSError("Interrupted before canonical replacement")
        return replace_with_retry(source, destination)

    with pytest.raises(OSError, match="Interrupted"):
        apply_reviewed_plan(paths, item, dossier, "Source editor", writer=interrupted, source_context=context)
    assert target.read_bytes() == before
    apply_reviewed_plan(paths, item, dossier, "Source editor", source_context=context)
    document = read_yaml(target)
    assert document["evidence"][0]["source"]["end_ms"] == 6000
    assert document["evidence"][0]["visual_status"] == dossier["concept"]["evidence"][0]["visual_status"]
    archive = read_yaml(paths.content / "annotations/published-repair-history.yaml")["repairs"]
    assert len(archive) == 1 and archive[0]["previous_concept"]["evidence"][0]["source"]["end_ms"] == 9000
    assert archive[0]["source_corrections"] == item["source_corrections"]
    rollback_repair_transaction(paths)
    assert target.read_bytes() == before


@pytest.mark.parametrize("defect", ["missing_id", "other_video", "too_long", "padding", "url", "duplicate", "visual_field"])
def test_source_correction_rejects_invalid_metadata(tmp_path, defect):
    from processors.published_repair import source_correction_dossier

    _, item, dossier, context = source_plan_fixture(tmp_path)
    changes = deepcopy(item["source_corrections"])
    source = changes[0]["source"]
    if defect == "missing_id":
        source["segment_ids"] = ["video:missing"]
    elif defect == "other_video":
        source["video_id"] = "other"
    elif defect == "too_long":
        source["end_ms"] = 31000
    elif defect == "padding":
        source["end_ms"] = 8000
    elif defect == "url":
        source["url"] = "https://example.com"
    elif defect == "duplicate":
        changes.append(deepcopy(changes[0]))
    else:
        changes[0]["visual_source"] = {}
    with pytest.raises(ValueError):
        source_correction_dossier(dossier, changes, *context)


@pytest.mark.parametrize("defect", ["proof_changed", "incomplete_primary", "missing_context", "wrong_scope"])
def test_source_application_rejects_stale_or_incomplete_proof_without_writing(tmp_path, defect):
    paths, item, dossier, context = source_plan_fixture(tmp_path)
    before = (paths.content / "concepts/stance.yaml").read_bytes()
    if defect == "proof_changed":
        context[0][0].transcript.segments[0].text = "A different instruction."
    elif defect == "incomplete_primary":
        item["primary_review"]["decisions"].pop("field:label")
    elif defect == "missing_context":
        context = None
    else:
        item.pop("scope")
    with pytest.raises(ValueError):
        apply_reviewed_plan(paths, item, dossier, "Source editor", source_context=context)
    assert (paths.content / "concepts/stance.yaml").read_bytes() == before
    assert not (paths.content / "annotations/published-repair-history.yaml").exists()


@pytest.mark.parametrize("stored_corrected_concept", [False, True])
@pytest.mark.parametrize("stale_findings", [False, True])
def test_cli_source_application_maps_decisions_to_corrected_source(
        tmp_path, monkeypatch, stored_corrected_concept, stale_findings):
    import typer

    import processors.cli as cli
    from processors.published_repair import review_findings

    paths, item, dossier, context = source_plan_fixture(tmp_path)
    if stored_corrected_concept:
        from processors.published_repair import source_correction_dossier

        item["concept"] = source_correction_dossier(dossier, item["source_corrections"], *context)["concept"]
    _, _, audit = cli._published_audit_inputs(paths)
    item["previous_source_findings"] = review_findings(audit["items"][0])
    item["review_findings"] = {}
    if stale_findings:
        item["previous_source_findings"]["field:short_definition"] = "Different original finding."
    write_json(paths.data("manifests") / "published-repair-plans.json", {"items": {item["concept_id"]: item}})
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    if stale_findings:
        target = paths.content / "concepts/stance.yaml"
        before = target.read_bytes()
        with pytest.raises(typer.BadParameter, match="Review findings changed"):
            cli.apply_published_repairs("concept-stance", "Source editor", kb="fixture")
        assert target.read_bytes() == before
        return
    cli.apply_published_repairs("concept-stance", "Source editor", kb="fixture")
    fresh = read_json(paths.data("manifests") / "published-audit.json")
    assert all(d and d["status"] == "supported" for d in fresh["items"][0]["decisions"].values())
    assert read_yaml(paths.content / "concepts/stance.yaml")["evidence"][0]["source"]["end_ms"] == 6000


@pytest.mark.parametrize("original,replacement,allowed", [
    ("demonstration", "explanation", True),
    ("demonstration", "definition", False),
    ("explanation", "demonstration", False),
    ("definition", "explanation", False),
])
def test_reclassification_only_downgrades_demonstration_to_spoken_explanation(tmp_path, original, replacement, allowed):
    from processors.published_repair import proposed_inputs

    _, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    dossier["concept"]["evidence"][0]["evidence_type"] = original
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    proposal, _ = draft({"units": units})
    unit = next(u for u in proposal["units"] if u["key"].startswith("evidence:"))
    unit.update(status="needs_fix", edits=[
        {"field": "evidence_type", "text": replacement, "strings": None, "facets": None}])
    if not allowed:
        with pytest.raises(ValueError):
            validate_units(proposal["units"], units, draft=True)
        return
    validate_units(proposal["units"], units, draft=True)
    after = proposed_inputs(units, proposal)[unit["key"]]["value"]
    before = units[unit["key"]]["value"]
    assert after == {**before, "evidence_type": "explanation"}


def test_article_draft_coverage_bounded_and_verification_has_no_draft_verdict(tmp_path):
    _, _, audit, dossiers = fixture_inputs(tmp_path, rows=9)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    chunks = article_payloads(dossier, units, cap=4)
    assert len(chunks) == 3
    ids = [row["id"] for chunk in chunks for row in chunk["selected_rows"]]
    assert len(ids) == len(set(ids)) == 9
    assert all(len(chunk["selected_rows"])+len(chunk["context_rows"]) <= 4 for chunk in chunks)
    proposal, _ = draft({"units": units})
    payloads, exceptions = verification_payloads(dossier, units, proposal, cap=4)
    assert any(u["key"].startswith("evidence:") and u["status"] == "uncertain" for u in exceptions)
    assert all("edits" not in u and "note" not in u and "status" not in u
               for payload in payloads for u in payload["units"].values())


def select_field_proof(payload, *_args, **_kwargs):
    first = {u["key"]: u for u in payload.get("chunk_proposals", [{}])[0].get("units", [])}
    return {"units": [RepairUnit(key=key, status="uncertain", note="Select a citation proof; no approval.",
        supporting_segment_ids=first[key]["supporting_segment_ids"] if key in first
        else value["allowed_segment_ids"][:1]).model_dump()
        for key, value in payload["units"].items()]}, {"method": "fixture_proof_selection"}


@pytest.mark.parametrize("initial_limit", [3, 5, 20])
def test_large_field_selects_whole_citation_without_rewriting_and_resumes(tmp_path, initial_limit):
    paths, cfg, _, dossiers = fixture_inputs(tmp_path, rows=12)
    cfg.write_text("codex:\n  default_model: fixture\n  max_segments_per_job: 10\n")
    old = dossiers["concept-stance"]
    concept = Concept.model_validate(old["concept"])
    video = Video(id="video", title="Fixture", canonical_url="https://www.youtube.com/watch?v=video",
        duration_ms=36000, transcript=TranscriptTrack(video_id="video", language="English", language_code="en",
        is_generated=False, acquisition_method="fixture", segments=old["sources"][0]["selected_rows"]))
    second = concept.evidence[0].model_copy(deep=True)
    second.id = "second"
    concept.evidence[0].source = SourceSpan(video_id="video", start_ms=0, end_ms=18000,
        url=video.canonical_url+"&t=0s", segment_ids=[f"video:{i:05d}" for i in range(6)])
    second.source = SourceSpan(video_id="video", start_ms=18000, end_ms=36000,
        url=video.canonical_url+"&t=18s", segment_ids=[f"video:{i:05d}" for i in range(6, 12)])
    concept.evidence.append(second)
    dossier = audit_dossier(concept, {video.id: video}, {concept.id: concept})
    audit = build_published_audit([concept], [video], paths.id)
    checkpoint = tmp_path/"proofs.json"
    canonical = paths.content/"concepts/stance.yaml"
    before = canonical.read_bytes()
    seen = []

    def checked(payload, *args, **kwargs):
        assert len(payload["selected_rows"])+len(payload["context_rows"]) <= 10
        for key, value in payload["units"].items():
            if key.startswith("field:"):
                assert value["allowed_segment_ids"] == [f"video:{i:05d}" for i in range(6)]
                seen.append(key)
        return verify(payload, *args, **kwargs)

    args = (audit, {concept.id: dossier}, cfg, tmp_path, tmp_path/"budget.json", checkpoint)
    kwargs = {"repair_confirmed": True, "drafter": select_field_proof, "verifier": checked}
    if initial_limit == 20:
        run_repair_campaign(*args, max_calls=20, verifier=checked)
        saved = read_json(checkpoint)
        prior = saved["items"][concept.id]
        prior["repair_attempted"] = True
        definition = next(u for u in prior["draft"]["units"] if u["key"] == "field:short_definition")
        definition.update(status="needs_fix", edits=[{
            "field": "short_definition", "text": "Maintain a stable stance.", "strings": None, "facets": None}])
        definition["supporting_segment_ids"] = ["video:00006"]
        write_json(checkpoint, saved)
    first = run_repair_campaign(*args, max_calls=initial_limit, **kwargs)
    if initial_limit < 20:
        assert first["stopped"] == "call_limit"
        assert not read_json(checkpoint)["items"][concept.id].get("field_proof_attempted")
        resumed = run_repair_campaign(*args, max_calls=20, **kwargs)
        assert resumed["cached_jobs"] > 0
    item = read_json(checkpoint)["items"][concept.id]
    assert item["status"] == "verified" and item["field_proof_attempted"] and seen
    assert all(not u["quarantine"] for u in item["draft"]["units"])
    if initial_limit == 20:
        definition = next(u for u in item["draft"]["units"] if u["key"] == "field:short_definition")
        assert definition["edits"][0]["text"] == "Maintain a stable stance."
    else:
        assert all(not u["edits"] for u in item["draft"]["units"])
    assert canonical.read_bytes() == before and not item.get("primary_review")
    with pytest.raises(ValueError, match="primary"):
        apply_reviewed_plan(paths, item, dossier, "Fixture reviewer")


def test_field_selection_cannot_truncate_one_oversized_citation_and_parks(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path, rows=9)
    cfg.write_text("codex:\n  default_model: fixture\n  max_segments_per_job: 8\n")
    checkpoint = tmp_path/"proofs.json"
    args = (audit, dossiers, cfg, tmp_path, tmp_path/"budget.json", checkpoint)
    kwargs = {"max_calls": 20, "repair_confirmed": True, "drafter": select_field_proof, "verifier": verify}
    run_repair_campaign(*args, **kwargs)
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert item["status"] == "exceptions" and item["field_proof_attempted"]
    assert all(u["status"] == "uncertain" for u in item["verification"]["units"] if u["key"].startswith("field:"))
    assert run_repair_campaign(*args, **kwargs)["calls"] == 0


def test_campaign_resumes_separate_verification_without_approving_or_writing(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    canonical = paths.content / "concepts/stance.yaml"
    before = canonical.read_bytes()
    calls = []

    def tracked_draft(*args, **kwargs):
        calls.append("draft")
        return draft(*args, **kwargs)

    def tracked_verify(*args, **kwargs):
        calls.append("verify")
        return verify(*args, **kwargs)

    for cap in (1, 10, 10):
        run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                            max_calls=cap, drafter=tracked_draft, verifier=tracked_verify)
    assert calls == ["verify"]
    assert canonical.read_bytes() == before
    assert all(value is None for value in audit["items"][0]["decisions"].values())
    assert read_json(checkpoint)["items"]["concept-stance"]["status"] == "verified"


def test_uncertain_nonvisual_proposals_receive_exact_source_verification(tmp_path):
    _, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    proposal, _ = draft({"units": units})
    for unit in proposal["units"]:
        unit.update(status="uncertain", supporting_segment_ids=[])
    payloads, exceptions = verification_payloads(dossier, units, proposal, cap=80)
    assert not exceptions
    assert {key for payload in payloads for key in payload["units"]} == set(units)
    assert {row["id"] for payload in payloads for row in payload["selected_rows"]} == set(units["evidence:0:e"]["allowed_segment_ids"])
    assert all("status" not in value and "note" not in value for payload in payloads for value in payload["units"].values())


def test_verification_article_mirrors_proposed_values_and_labels_old_topic_as_context(tmp_path):
    _, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    proposal, _ = draft({"units": units})
    label = next(u for u in proposal["units"] if u["key"] == "field:label")
    label.update(status="needs_fix", edits=[{"field": "label", "text": "Balanced stance", "strings": None, "facets": None}])
    payloads, exceptions = verification_payloads(dossier, units, proposal, cap=80)
    assert not exceptions
    for payload in payloads:
        assert payload["article"]["id"] == dossier["concept"]["id"]
        assert payload["article"]["label"] == "Balanced stance"
        assert payload["article"]["short_definition"] == "A stable stance supports balance."
        assert payload["original_topic"]["label"] == "Stable stance"
        assert payload["original_topic"]["short_definition"] == "Keep a stable stance."
        assert payload["units"]["field:short_definition"]["value"] == payload["article"]["short_definition"]


def test_reducer_assembles_untrusted_proposals_instead_of_adjudicating_empty_rows(tmp_path, monkeypatch):
    import processors.published_repair as repair

    _, config, audit, dossiers = fixture_inputs(tmp_path)
    units = unit_inputs(dossiers["concept-stance"], list(audit["items"][0]["decisions"]))
    proposal, _ = draft({"units": units})
    payload = {"units": units, "selected_rows": [], "context_rows": [], "chunk_proposals": [proposal]}

    def assembled(prompt, schema, response_model, *_args, **_kwargs):
        assert _args[2] == sha256_json({"prompt": prompt, "version": repair.DRAFT_VERSION, "schema": schema})
        assert "proposal assembly, not transcript adjudication" in prompt
        assert "separate verification with actual selected captions" in prompt
        assert "Use only exact selected_rows as claim support" not in prompt
        response_units = schema["properties"]["units"]
        assert response_units["type"] == "object"
        assert set(response_units["required"]) == set(units)
        assert set(response_units["properties"]) == set(units)
        assert response_units["additionalProperties"] is False
        variants = [variant for entry in response_units["properties"].values() for variant in entry.get("anyOf", [entry])]
        for variant in variants:
            key = variant["properties"]["key"]["enum"][0]
            if key.startswith("field:"):
                assert variant["properties"]["edits"]["maxItems"] <= 1
            if key in {"field:aliases", "field:facets"}:
                representation = "strings" if key == "field:aliases" else "facets"
                active = variant["properties"]["edits"]["items"]["properties"][representation]
                assert active["type"] == "array"
                assert "anyOf" not in active
            if variant["properties"]["quarantine"]["enum"] == [True]:
                assert key.startswith(("evidence:", "relation:"))
                assert variant["properties"]["edits"]["maxItems"] == 0
        return response_model.model_validate({"units": {u["key"]: u for u in proposal["units"]}}), {"method": "fixture"}

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", assembled)
    result, _ = repair.draft_article_with_codex(payload, config, tmp_path, tmp_path / "budget.json")
    assert result["units"] == proposal["units"]


@pytest.mark.parametrize("mode", ["draft", "verify", "reduce"])
def test_repair_policy_corrects_headings_without_discarding_same_subject_evidence(tmp_path, monkeypatch, mode):
    import processors.published_repair as repair

    _, config, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    proposal, _ = draft({"units": units})
    payload = article_payloads(dossier, units, 80)[0]
    if mode == "verify":
        payload = verification_payloads(dossier, units, proposal, 80)[0][0]
    elif mode == "reduce":
        payload = {"units": units, "selected_rows": [], "context_rows": [], "chunk_proposals": [proposal]}

    def transport(prompt, _schema, response_model, *_args, **_kwargs):
        assert "Identifiers are opaque references, not topic proof" in prompt
        assert "obsolete labels" in prompt
        assert "do not switch to an unrelated topic" in prompt.lower()
        if mode == "reduce":
            assert "proposed corrections to erroneous headings" in prompt
            assert "Use only exact selected_rows as claim support" not in prompt
        else:
            assert "Correct an unsupported or" in prompt
            assert "Do not quarantine supported same-subject evidence" in prompt
            assert "missing topic identity stays uncertain" in prompt
            assert "context_rows are not support" in prompt
        response, provenance = verify(payload) if mode == "verify" else draft(payload)
        return response_model.model_validate(response), provenance

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", transport)
    call = repair.verify_article_with_codex if mode == "verify" else repair.draft_article_with_codex
    call(payload, config, tmp_path, tmp_path / "budget.json")


def test_keyed_response_rejects_mismatched_unit_identity():
    from processors.published_repair import ArticleVerificationResponse

    unit = VerifiedUnit(key="field:label", status="supported", note="Fixture.", supporting_segment_ids=[]).model_dump()
    with pytest.raises(ValueError, match="property must match"):
        ArticleVerificationResponse.model_validate({"units": {"field:aliases": unit}})


@pytest.mark.parametrize("defect", ["missing", "duplicate", "foreign_id", "wrong_field", "visual_upgrade"])
def test_plan_rejects_missing_units_foreign_ids_and_unauthorized_changes(tmp_path, defect):
    _, _, audit, dossiers = fixture_inputs(tmp_path)
    units = unit_inputs(dossiers["concept-stance"], list(audit["items"][0]["decisions"]))
    result, _ = draft({"units": units})
    if defect == "missing":
        result["units"].pop()
    elif defect == "duplicate":
        result["units"].append(result["units"][0])
    elif defect == "foreign_id":
        result["units"][0]["supporting_segment_ids"] = ["foreign:00000"]
    elif defect == "wrong_field":
        result["units"][0].update(status="needs_fix", edits=[{"field": "reason", "text": "No.", "strings": None, "facets": None}])
    else:
        units["visual:0:e"] = deepcopy(units["evidence:0:e"])
        result["units"].append(RepairUnit(key="visual:0:e", status="supported", note="Not watched.", supporting_segment_ids=[]).model_dump())
    with pytest.raises(ValueError):
        validate_units(result["units"], units, draft=True)


def test_independent_failure_stays_exception_and_cannot_be_applied(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)

    def unsupported(payload, *_args, **_kwargs):
        result, provenance = verify(payload)
        result["units"][0].update(status="needs_fix", note="Unsupported qualifier.")
        return result, provenance

    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=unsupported)
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert item["status"] == "exceptions"
    with pytest.raises(ValueError, match="verified plan"):
        apply_reviewed_plan(paths, item, dossiers["concept-stance"], "Fixture reviewer")


def test_reviewed_apply_archives_preserves_sources_and_recovers_partial_write(tmp_path):
    paths, item, dossier = ready_plan(tmp_path)
    canonical = paths.content / "concepts/stance.yaml"
    original = read_yaml(canonical)
    from processors.utils import replace_with_retry

    def interrupted(source, target):
        if target == canonical:
            raise PermissionError("Interrupted canonical write")
        replace_with_retry(source, target)

    with pytest.raises(PermissionError):
        apply_reviewed_plan(paths, item, dossier, "Fixture reviewer", writer=interrupted)
    assert read_yaml(canonical) == original
    journal = paths.data("manifests") / "published-repair-transaction.json"
    assert read_json(journal)["state"] == "prepared"
    apply_reviewed_plan(paths, item, dossier, "Fixture reviewer")
    apply_reviewed_plan(paths, item, dossier, "Fixture reviewer")
    revised = read_yaml(canonical)
    assert revised["short_definition"] == "A stable stance supports balance."
    assert revised["evidence"] == original["evidence"]
    assert revised["id"] == original["id"] and revised["slug"] == original["slug"]
    archive = read_yaml(paths.content / "annotations/published-repair-history.yaml")
    assert len(archive["repairs"]) == 1
    assert archive["repairs"][0]["previous_concept"] == original


def test_apply_rejects_tampered_plan_and_prepared_unrelated_edits(tmp_path):
    paths, item, dossier = ready_plan(tmp_path)
    invalid = deepcopy(item)
    invalid["draft"]["units"].pop()
    with pytest.raises(ValueError, match="hash"):
        apply_reviewed_plan(paths, invalid, dossier, "Fixture reviewer")
    invalid["plan_hash"] = sha256_json({k: invalid[k] for k in ("identity", "draft", "verification")})
    with pytest.raises(ValueError, match="each requested unit"):
        apply_reviewed_plan(paths, invalid, dossier, "Fixture reviewer")
    canonical = paths.content / "concepts/stance.yaml"

    def fail(*_args):
        raise PermissionError("Prepared only")

    with pytest.raises(PermissionError):
        apply_reviewed_plan(paths, item, dossier, "Fixture reviewer", writer=fail)
    canonical.write_text(canonical.read_text(encoding="utf-8")+"# unrelated editor change\n", encoding="utf-8")
    before = canonical.read_bytes()
    with pytest.raises(ValueError, match="changed during"):
        apply_reviewed_plan(paths, item, dossier, "Fixture reviewer")
    assert canonical.read_bytes() == before


def test_oversized_complete_proofs_stay_exceptions_without_reduction(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path, rows=9)
    cfg.write_text("codex:\n  default_model: fixture\n  max_segments_per_job: 4\n", encoding="utf-8")
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=20, drafter=draft, verifier=verify)
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert not item["jobs"]
    assert item["status"] == "exceptions"
    assert set(u["key"] for u in item["verification"]["units"]) == set(audit["items"][0]["decisions"])


def test_cli_apply_records_fresh_coverage_and_rejects_stale_plan(tmp_path, monkeypatch):
    import processors.cli as cli
    from processors.pipeline import load_reviewed_concepts

    paths, item, dossier = ready_plan(tmp_path)
    video = Video(id="video", title="Fixture", canonical_url="https://www.youtube.com/watch?v=video", duration_ms=9000,
                  transcript=TranscriptTrack(video_id="video", language="English", language_code="en", is_generated=False,
                  acquisition_method="fixture", segments=dossier["sources"][0]["selected_rows"]))
    monkeypatch.setattr(cli, "kb_paths", lambda *_args: paths)
    video_loads = []
    monkeypatch.setattr(cli, "load_videos", lambda *_args: video_loads.append(True) or [video])
    plans = paths.data("manifests") / "published-repair-plans.json"
    cli.apply_published_repairs(concept_ids="concept-stance", reviewer="Fixture reviewer", kb=paths.id)
    assert len(video_loads) == 1
    assert read_json(plans)["items"]["concept-stance"]["status"] == "applied"
    audit = read_json(paths.data("manifests") / "published-audit.json")
    assert all(d["status"] == "supported" for d in audit["items"][0]["decisions"].values())
    cli.apply_published_repairs(concept_ids="concept-stance", reviewer="Fixture reviewer", kb=paths.id)
    assert load_reviewed_concepts(paths.content / "concepts")[0].short_definition == "A stable stance supports balance."
    with (paths.content / "concepts/stance.yaml").open("a", encoding="utf-8") as stream:
        stream.write("# unrelated edit\n")
    revised = read_yaml(paths.content / "concepts/stance.yaml")
    revised["label"] = "Changed title"
    with (paths.content / "concepts/stance.yaml").open("w", encoding="utf-8") as stream:
        YAML().dump(revised, stream)
    import typer

    with pytest.raises(typer.BadParameter, match="changed"):
        cli.apply_published_repairs(concept_ids="concept-stance", reviewer="Fixture reviewer", kb=paths.id)


def test_new_primary_findings_invalidate_cached_plans_and_block_application(tmp_path, monkeypatch):
    import typer

    import processors.cli as cli

    paths, config, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    run_repair_campaign(audit, dossiers, config, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=verify)
    audit["items"][0]["decisions"]["field:short_definition"] = {
        "status": "needs_fix", "note": "New primary review found a missing condition."
    }
    monkeypatch.setattr(cli, "kb_paths", lambda *_args: paths)
    monkeypatch.setattr(cli, "_published_audit_inputs", lambda *_args: ([], [], audit))
    before = paths.content.joinpath("concepts/stance.yaml").read_bytes()
    with pytest.raises(typer.BadParameter, match="Review findings changed"):
        cli.apply_published_repairs(concept_ids="concept-stance", reviewer="Fixture reviewer", kb=paths.id)
    assert paths.content.joinpath("concepts/stance.yaml").read_bytes() == before
    result = run_repair_campaign(audit, dossiers, config, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=verify, repair_confirmed=True)
    assert result["calls"] == 2
    plans = read_json(checkpoint)
    assert len(plans["history"]) == 1
    assert plans["items"]["concept-stance"]["review_findings"] == {
        "field:short_definition": "New primary review found a missing condition."
    }


def test_timing_plan_only_quarantines_measured_records_without_semantic_credit(tmp_path):
    paths, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    dossier["sources"][0]["video"]["duration_ms"] = 8999
    item = timing_quarantine_plan(audit["items"][0], dossier)
    assert item["scope"] == "duration_conflicts"
    assert len(item["draft"]["units"]) == 1
    before = read_yaml(paths.content / "concepts/stance.yaml")
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    payloads, exceptions = verification_payloads(dossier, units, item["draft"], cap=80)
    assert not exceptions
    proposed = payloads[0]["units"]["evidence:0:e"]["value"]
    assert proposed["review_status"] == "unreviewed"
    apply_reviewed_plan(paths, item, dossier, "Timing reviewer")
    after = read_yaml(paths.content / "concepts/stance.yaml")
    assert after["evidence"][0] == proposed
    assert after["evidence"][0]["review_status"] == "unreviewed"
    assert after["evidence"][0]["source"] == before["evidence"][0]["source"]
    assert after["short_definition"] == before["short_definition"]
    assert all(value is None for value in audit["items"][0]["decisions"].values())


def test_concept_type_edit_reaches_schema_validation_and_guarded_application(tmp_path, monkeypatch):
    import processors.published_repair as repair

    paths, item, dossier = ready_plan(tmp_path)
    unit = next(u for u in item["draft"]["units"] if u["key"] == "field:concept_type")
    unit.update(status="needs_fix", edits=[repair.RepairEdit(field="concept_type", text="tactic").model_dump()])
    units = unit_inputs(dossier, [u["key"] for u in item["draft"]["units"]])
    payload = article_payloads(dossier, {unit["key"]: units[unit["key"]]}, cap=80)[0]

    def transport(_prompt, schema, *_args, **_kwargs):
        edit = schema["properties"]["units"]["properties"][unit["key"]]["properties"]["edits"]["items"]
        assert edit["properties"]["field"]["enum"] == ["concept_type"]
        return repair.ArticleRepairResponse(units=[unit]), {}

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", transport)
    result, _ = repair.draft_article_with_codex(payload, tmp_path / "processors.yaml", tmp_path, tmp_path / "budget.json")
    assert result["units"] == [unit]
    validate_units(item["draft"]["units"], units, draft=True)
    assert repair.proposed_inputs(units, item["draft"])[unit["key"]]["value"] == "tactic"
    foreign = deepcopy(unit)
    foreign["edits"][0]["field"] = "label"
    with pytest.raises(ValueError, match="Unauthorized repair"):
        validate_units([foreign], payload["units"], draft=True)

    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    item["primary_review"] = primary_review(item)
    apply_reviewed_plan(paths, item, dossier, "Editor")
    assert read_yaml(paths.content / "concepts/stance.yaml")["concept_type"] == "tactic"
    archived = read_yaml(paths.content / "annotations/published-repair-history.yaml")["repairs"]
    assert archived[0]["previous_concept"]["concept_type"] == "concept"


def test_model_transport_uses_profile_schema_and_rejects_foreign_support_ids(tmp_path, monkeypatch):
    import json

    import processors.codex_engine as engine
    from processors.published_repair import verify_article_with_codex

    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, list(audit["items"][0]["decisions"]))
    payload = article_payloads(dossier, units, cap=80)[0]
    cfg.write_text(cfg.read_text(encoding="utf-8") + "  reasoning_effort: high\n", encoding="utf-8")
    monkeypatch.setattr(engine, "preflight", lambda _tier: ("codex", "fixture-cli"))

    def completed(command, **kwargs):
        assert "--ephemeral" in command and command[command.index("--sandbox")+1] == "read-only"
        assert command[command.index("--model")+1] == "fixture"
        assert 'model_reasoning_effort="high"' in command
        assert "unidentified subject/object" in kwargs["input"]
        assert "preceding complete independent instruction" in kwargs["input"]
        assert kwargs["timeout"] == 300
        schema = read_json(Path(command[command.index("--output-schema")+1]))
        assert any(name.startswith("SupportIds") and value["enum"] for name, value in schema["$defs"].items())
        for variant in schema["properties"]["units"]["properties"].values():
            assert set(variant["required"]) == set(variant["properties"])
        result, _ = verify(payload)
        result["units"][0]["supporting_segment_ids"] = ["foreign:00000"]
        Path(command[command.index("--output-last-message")+1]).write_text(json.dumps(result), encoding="utf-8")
        return engine.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(engine.subprocess, "run", completed)
    with pytest.raises(ValueError, match="Foreign"):
        verify_article_with_codex(payload, cfg, tmp_path / "private", tmp_path / "budget.json")
    assert list(tmp_path.joinpath("private").glob("*.repair.failure.json"))


@pytest.mark.parametrize("quarantined", [False, True])
@pytest.mark.parametrize("record_type", ["evidence", "relation"])
def test_source_verifier_receives_claims_without_prior_confidence_or_approval(tmp_path, monkeypatch, quarantined, record_type):
    import json

    import processors.published_repair as repair

    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    key = next(key for key in audit["items"][0]["decisions"] if key.startswith("evidence:"))
    units = unit_inputs(dossier, [key])
    if record_type == "relation":
        evidence = units[key]
        key = "relation:0"
        units = {key: {"value": {"relation_type": "used_with", "target_concept_id": "concept-footwork",
                                 "sources": evidence["source_spans"]},
                       "allowed_segment_ids": evidence["allowed_segment_ids"]}}
    units[key]["value"]["review_status"] = "unreviewed" if quarantined else "approved"
    units[key]["quarantine"] = quarantined
    payload = {"units": units, "selected_rows": dossier["sources"][0]["selected_rows"], "context_rows": []}
    before = json.loads(json.dumps(payload))
    captured = []

    def checked_transport(prompt, *_args, **_kwargs):
        sent = json.loads(prompt[prompt.index('{"units":'):])
        if quarantined:
            assert sent["units"][key]["value"] is None
            assert "when omission is justified" in prompt
            value = dict(sent["units"][key]["archived_original"])
        else:
            assert "archived_original" not in sent["units"][key]
            value = dict(sent["units"][key]["value"])
        assert "confidence" not in value and "review_status" not in value
        if record_type == "evidence":
            spans = sent["source_span_sets"][sent["units"][key]["source_spans_ref"]]
            assert spans == before["units"][key]["source_spans"]
            value["source"] = spans[0]
        assert value == {name: value for name, value in before["units"][key]["value"].items()
                         if name not in {"confidence", "review_status"}}
        assert sent["units"][key]["allowed_segment_ids"] == units[key]["allowed_segment_ids"]
        assert sent["units"][key]["quarantine"] is quarantined
        assert sent["selected_rows"] == [{k: v for k, v in row.items() if k != "normalized_text"}
                                         for row in before["selected_rows"]]
        captured.append(sent)
        return repair.ArticleVerificationResponse.model_validate(verify(sent)[0]), {"method": "fixture"}

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", checked_transport)
    result, _ = repair.verify_article_with_codex(payload, cfg, tmp_path / "private", tmp_path / "budget.json")
    assert captured and payload == before
    assert result["units"][0]["status"] == "supported"


@pytest.mark.parametrize(('outcome_text', 'condition_text'), [
    ('The racket head never whips; it stays dead.', 'If you break immediately,'),
    ('Up-down swings will kill your backhand.', 'A small elbow movement is okay, but big'),
])
def test_verification_keeps_relevant_late_condition_and_ignores_unrelated_context(
        tmp_path, outcome_text, condition_text):
    _, _, audit, dossiers = fixture_inputs(tmp_path, rows=1)
    dossier = dossiers['concept-stance']
    key = 'evidence:0:e'
    dossier['sources'][0]['selected_rows'][0]['text'] = outcome_text
    condition = {**dossier['sources'][0]['selected_rows'][0], 'id': 'video:condition',
                 'text': condition_text, 'start_ms': -1000}
    dossier['sources'][0]['context_rows'] = [condition]
    unrelated = deepcopy(dossier['sources'][0])
    unrelated['selected_rows'] = [{**condition, 'id': 'other:selected'}]
    unrelated['context_rows'] = [{**condition, 'id': f'a:{i}', 'text': 'Unrelated.'} for i in range(12)]
    dossier['sources'].append(unrelated)
    units = unit_inputs(dossier, [key])
    proposal, _ = draft({'units': units})
    payloads, exceptions = verification_payloads(dossier, units, proposal, 80)
    assert not exceptions
    assert payloads[0]['context_rows'] == [condition]
    assert condition['id'] not in payloads[0]['units'][key]['allowed_segment_ids']


def test_verification_defers_instead_of_dropping_required_context(tmp_path):
    _, _, _, dossiers = fixture_inputs(tmp_path, rows=1)
    dossier = dossiers['concept-stance']
    row = dossier['sources'][0]['selected_rows'][0]
    dossier['sources'][0]['context_rows'] = [{**row, 'id': f'context:{i}'} for i in range(4)]
    units = unit_inputs(dossier, ['evidence:0:e'])
    proposal, _ = draft({'units': units})
    payloads, exceptions = verification_payloads(dossier, units, proposal, 4)
    assert not payloads
    assert exceptions[0]['key'] == 'evidence:0:e'
    assert exceptions[0]['status'] == 'uncertain'
    assert 'context' in exceptions[0]['note']


def test_direct_verifier_rejects_oversized_context_before_transport(tmp_path, monkeypatch):
    import processors.published_repair as repair
    _, cfg, _, dossiers = fixture_inputs(tmp_path, rows=1)
    dossier = dossiers['concept-stance']
    units = unit_inputs(dossier, ['evidence:0:e'])
    row = dossier['sources'][0]['selected_rows'][0]
    payload = {'units': units, 'selected_rows': [row],
               'context_rows': [{**row, 'id': f'context:{i}'} for i in range(80)]}
    monkeypatch.setattr(repair, '_run_schema_constrained_codex',
                        lambda *a, **k: pytest.fail('Oversized proof reached transport'))
    with pytest.raises(ValueError, match='no context may be truncated'):
        repair.verify_article_with_codex(payload, cfg, tmp_path/'private', tmp_path/'budget.json')


def test_quoted_flow_source_ids_remain_parseable_and_rollback_restores_exact_bytes(tmp_path):
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString

    paths, item, dossier = ready_plan(tmp_path)
    canonical = paths.content / "concepts/stance.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    document = yaml.load(canonical)
    source = document["evidence"][0]["source"]
    source["url"] = DoubleQuotedScalarString(source["url"])
    source.fa.set_flow_style()
    source["segment_ids"].fa.set_flow_style()
    source["segment_ids"] = [DoubleQuotedScalarString(sid) for sid in source["segment_ids"]]
    with canonical.open("w", encoding="utf-8") as stream:
        yaml.dump(document, stream)
    original = canonical.read_bytes()
    assert read_yaml(canonical)["evidence"][0]["source"]["segment_ids"]
    apply_reviewed_plan(paths, item, dossier, "Fixture reviewer")
    assert read_yaml(canonical)["evidence"][0]["source"] == read_yaml(
        paths.content / "annotations/published-repair-history.yaml"
    )["repairs"][0]["previous_concept"]["evidence"][0]["source"]
    rollback_repair_transaction(paths)
    assert canonical.read_bytes() == original
    assert read_json(paths.data("manifests") / "published-repair-transaction.json")["state"] == "rolled_back"


def test_failed_call_and_budget_deferral_preserve_checkpoint_without_repeated_calls(tmp_path):
    from processors.codex_engine import CodexError
    from processors.llm_budget import LLMBudgetExceeded

    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    calls = []

    def failed(*_args, **_kwargs):
        calls.append(1)
        raise CodexError("Invalid response")

    for _ in range(2):
        run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                            max_calls=10, drafter=draft, verifier=failed)
    assert calls == [1]

    def budget(*_args, **_kwargs):
        raise LLMBudgetExceeded("adjudication", 1, {"remaining_tokens": 0}, "Fixture cap")

    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, retry_failed=True, drafter=draft, verifier=budget)
    assert result["stopped"] == "budget" and result["calls"] == 0
    assert read_json(checkpoint)["items"]["concept-stance"]["jobs"]["audit:0"]["status"] == "budget_deferred"


def test_summary_format_only_deletes_known_generated_wrapper_without_semantic_approval(tmp_path):
    paths, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    prefix = "Stable stance brings together several connected ideas. "
    suffix = " Together, these principles show how the topic is applied in practice while preserving the relevant distinctions and constraints."
    body = "Keep a stable stance."
    dossier["concept"].update(evidence_summary=prefix+body+suffix,
                              evidence_summary_generator="deterministic", evidence_summary_source_hash="sha256:old")
    path = paths.content / "concepts/stance.yaml"
    with path.open("w", encoding="utf-8") as stream:
        YAML().dump(dossier["concept"], stream)
    item = summary_format_plan(audit["items"][0], dossier)
    assert item["scope"] == "summary_format"
    apply_reviewed_plan(paths, item, dossier, "Format reviewer")
    after = read_yaml(path)
    assert after["evidence_summary"] == body
    assert after["evidence_summary_source_hash"] == "sha256:old"
    assert after["evidence_summary_generator"] == "deterministic"
    assert all(value is None for value in audit["items"][0]["decisions"].values())
    dossier["concept"]["evidence_summary_generator"] = "codex"
    assert summary_format_plan(audit["items"][0], dossier) is None


def test_public_review_wording_is_rejected_and_reviewed_findings_are_repaired(tmp_path):
    from processors.published_repair import public_prose_findings

    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    assert public_prose_findings("evidence:0:e", {"reason": "This contiguous span matches the supplied concept.", "excerpt": "A stance."})
    assert not public_prose_findings("field:aliases", ["Balanced stance"])
    for key in audit["items"][0]["decisions"]:
        audit["items"][0]["decisions"][key] = {"status": "supported", "note": "Fixture review."}
    audit["items"][0]["decisions"]["field:short_definition"] = {"status": "needs_fix", "note": "Overstated causal link."}
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=verify, repair_confirmed=True)
    assert result["calls"] == 2 and result["article_states"] == {"verified": 1}


def test_supported_model_response_cannot_publish_review_scaffolding(tmp_path, monkeypatch):
    import processors.published_repair as repair

    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, ["evidence:0:e"])
    units["evidence:0:e"]["value"]["reason"] = "This contiguous span matches the existing concept."
    payload = article_payloads(dossier, units, 80)[0]
    response = repair.ArticleVerificationResponse.model_validate(verify(payload)[0])
    monkeypatch.setattr(repair, "_run_schema_constrained_codex", lambda *_args, **_kwargs: (response, {"method": "fixture"}))
    result, _ = repair.verify_article_with_codex(payload, cfg, tmp_path / "private", tmp_path / "budget.json")
    assert result["units"][0]["status"] == "needs_fix"
    assert "review scaffolding" in result["units"][0]["note"]


def test_audit_failure_gets_one_targeted_repair_and_feedback_is_hidden_from_final_verifier(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    checks = []
    drafts = []

    def tracked_draft(payload, *_args, **_kwargs):
        revising = any("verifier_feedback" in unit for unit in payload["units"].values())
        drafts.append(revising)
        result, provenance = draft(payload)
        if revising:
            assert set(payload["units"]) == {"evidence:0:e"}
            result["units"][0].update(status="needs_fix", edits=[{
                "field": "reason", "text": "Keep the stance stable.", "strings": None, "facets": None,
            }])
        return result, provenance

    def tracked_verify(payload, *_args, **_kwargs):
        assert all("verifier_feedback" not in unit and "mechanical_findings" not in unit
                   for unit in payload["units"].values())
        result, provenance = verify(payload)
        if not checks:
            next(u for u in result["units"] if u["key"] == "evidence:0:e").update(status="needs_fix", note="Revise this clause.")
        checks.append(set(payload["units"]))
        return result, provenance

    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=tracked_draft, verifier=tracked_verify, repair_confirmed=True)
    assert drafts == [True] and len(checks) == 2
    assert checks[1] == {"evidence:0:e"}
    assert read_json(checkpoint)["items"]["concept-stance"]["status"] == "verified"


@pytest.mark.parametrize("policy,expected_calls", [("VERIFICATION_VERSION", 1), ("REPAIR_VERSION", 0)])
def test_policy_refresh_reuses_unaffected_stages_and_blocks_old_application(tmp_path, monkeypatch, policy, expected_calls):
    import processors.published_repair as repair

    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=verify)
    old = read_json(checkpoint)["items"]["concept-stance"]
    monkeypatch.setattr(repair, policy, "next-policy")
    with pytest.raises(ValueError, match="version changed|stage policy changed"):
        apply_reviewed_plan(paths, old, dossiers["concept-stance"], "Fixture reviewer")
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=verify)
    assert result["calls"] == expected_calls
    assert result["cached_jobs"] == (0 if policy == "VERIFICATION_VERSION" else 1)
    fresh = read_json(checkpoint)["items"]["concept-stance"]
    assert fresh["status"] == "verified" and fresh["stage_versions"]["verification"] == repair.VERIFICATION_VERSION
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=verify)
    assert result["calls"] == 0 and result["parked_articles"] == 1


def test_changed_reason_rechecks_only_its_unit_and_retains_check_provenance(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "plans.json"
    checks = []

    def tracked_verify(payload, *args, **kwargs):
        checks.append(set(payload["units"]))
        return verify(payload, *args, **kwargs)

    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=tracked_verify)
    dossiers["concept-stance"]["concept"]["evidence"][0]["reason"] = "Keep the stance stable."
    audit["items"][0]["fingerprint"] = sha256_json(dossiers["concept-stance"])
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=tracked_verify)
    assert checks[1] == {"evidence:0:e"}
    assert result["cached_verification_units"] == len(checks[0]) - 1
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert set(item["jobs"]["audit:0"]["provenance"]["reused_units"]) == checks[0] - checks[1]
    assert set(u["key"] for u in item["verification"]["units"]) == checks[0]
    assert all(value is None for value in audit["items"][0]["decisions"].values())


@pytest.mark.parametrize("dependency", ["source", "topic", "definition", "target", "overlap", "metadata", "model", "effort"])
def test_verification_cache_invalidates_source_topic_target_and_model_changes(tmp_path, dependency):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "plans.json"
    checks = []

    def tracked_verify(payload, *args, **kwargs):
        checks.append(set(payload["units"]))
        return verify(payload, *args, **kwargs)

    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=tracked_verify)
    dossier = dossiers["concept-stance"]
    if dependency == "source":
        dossier["sources"][0]["selected_rows"][0]["text"] = "Keep the stance stable."
    elif dependency == "topic":
        dossier["concept"]["label"] = "Balanced stance"
    elif dependency == "definition":
        dossier["concept"]["detailed_definition"] = "Keep the stance stable."
        audit["items"][0]["decisions"]["field:detailed_definition"] = None
    elif dependency == "target":
        dossier["relation_targets"]["concept-footwork"] = {"label": "Footwork", "short_definition": "Move first."}
    elif dependency == "overlap":
        dossier["topic_overlap_candidates"] = [{"id": "other-stance", "label": "Stable stance"}]
    elif dependency == "metadata":
        dossier["sources"][0]["video"]["duration_ms"] += 1000
    elif dependency == "model":
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("default_model: fixture", "default_model: other"), encoding="utf-8")
    else:
        cfg.write_text(cfg.read_text(encoding="utf-8") + "  reasoning_effort: high\n", encoding="utf-8")
    audit["items"][0]["fingerprint"] = sha256_json(dossier)
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=tracked_verify)
    assert result["calls"] == 1 and result["cached_verification_units"] == 0
    assert checks[0] <= checks[1]


def test_noop_revision_and_unchanged_exception_do_not_repeat_verification(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "plans.json"
    checks = []

    def rejected(payload, *_args, **_kwargs):
        checks.append(set(payload["units"]))
        result, provenance = verify(payload)
        next(u for u in result["units"] if u["key"] == "evidence:0:e").update(status="needs_fix", note="Not supported.")
        return result, provenance

    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=rejected, repair_confirmed=True)
    assert result["calls"] == 2 and len(checks) == 1
    assert result["article_states"] == {"exceptions": 1}
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=10, drafter=draft, verifier=rejected)
    assert result["calls"] == 0 and result["parked_articles"] == 1


def test_compaction_preserves_all_text_timing_ownership_and_shared_spans(tmp_path):
    import json
    from copy import deepcopy

    from processors.published_repair import compact_model_payload

    _, _, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    dossier["sources"][0]["selected_rows"][0]["normalized_text"] = "A different normalization must stay."
    payload = article_payloads(dossier, unit_inputs(dossier, list(audit["items"][0]["decisions"])), cap=80)[0]
    before = deepcopy(payload)
    compact = compact_model_payload(payload)
    assert payload == before
    assert len(json.dumps(compact, separators=(",", ":"))) < len(json.dumps(payload)) * 0.8
    assert len(compact["source_span_sets"]) == 1
    for key, original in payload["units"].items():
        unit = compact["units"][key]
        spans = compact["source_span_sets"][unit["source_spans_ref"]]
        assert spans == original["source_spans"]
        assert unit["allowed_segment_ids"] == original["allowed_segment_ids"]
        value = deepcopy(unit["value"])
        if key.startswith("evidence:"):
            value["source"] = spans[0]
        assert value == original["value"]
    for name in ("selected_rows", "context_rows"):
        assert len(compact[name]) == len(payload[name])
        for old, new in zip(payload[name], compact[name], strict=True):
            assert all(new[key] == old[key] for key in ("id", "text", "start_ms", "duration_ms"))
    assert compact["selected_rows"][0]["normalized_text"] == "A different normalization must stay."


def test_revision_source_chunks_include_every_requested_row_without_unrelated_rows(tmp_path):
    _, _, audit, dossiers = fixture_inputs(tmp_path, rows=9)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, ["evidence:0:e"])
    units["evidence:0:e"]["allowed_segment_ids"] = ["video:00003", "video:00004"]
    chunks = article_payloads(dossier, units, cap=4)
    assert len(chunks) == 1
    assert [row["id"] for row in chunks[0]["selected_rows"]] == ["video:00003", "video:00004"]


def test_cached_foreign_support_ids_fail_closed_without_canonical_writes(tmp_path):
    from processors.utils import write_json

    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = paths.data("manifests") / "plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=10, drafter=draft, verifier=verify)
    saved = read_json(checkpoint)
    saved["items"]["concept-stance"]["baseline_verification"]["units"][0]["supporting_segment_ids"] = ["foreign:00000"]
    saved["items"]["concept-stance"].update(status="pending", jobs={})
    write_json(checkpoint, saved)
    before = (paths.content / "concepts/stance.yaml").read_bytes()
    with pytest.raises(ValueError, match="Foreign"):
        run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                            max_calls=10, drafter=draft, verifier=verify)
    assert (paths.content / "concepts/stance.yaml").read_bytes() == before


@pytest.mark.parametrize("key,value,representation", [
    ("field:difficulty", None, "text"),
    ("field:detailed_definition", None, "text"),
    ("field:short_definition", "Keep a stable stance.", "text"),
    ("field:aliases", ["Stable stance"], "strings"),
    ("field:facets", {"category": ["fundamentals"]}, "facets"),
    ("evidence:0:e", {"excerpt": "Keep a stable stance.", "reason": "Maintain balance."}, "text"),
])
def test_draft_wire_disallows_unused_edit_channels_and_keeps_nullable_clears(
    tmp_path, monkeypatch, key, value, representation,
):
    import processors.published_repair as repair

    _, cfg, _, _ = fixture_inputs(tmp_path)
    payload = {"units": {key: {"value": value, "allowed_segment_ids": []}}, "selected_rows": []}

    def checked_transport(_prompt, schema, *_args, **_kwargs):
        variant = schema["properties"]["units"]["properties"][key]
        if "anyOf" in variant:
            variant = next(v for v in variant["anyOf"] if v["properties"]["edits"].get("maxItems") != 0)
        properties = variant["properties"]["edits"]["items"]["properties"]
        for unused in {"text", "strings", "facets"} - {representation}:
            assert properties[unused] == {"type": "null"}
        edits = []
        if key == "field:difficulty":
            assert {"type": "null"} in properties["text"]["anyOf"]
            edits = [{"field": "difficulty", "text": None, "strings": None, "facets": None}]
        unit = repair.RepairUnit(key=key, status="needs_fix" if edits else "supported",
                                note="Fixture source review.", supporting_segment_ids=[], edits=edits)
        return repair.ArticleRepairResponse(units=[unit]), {"method": "fixture"}

    monkeypatch.setattr(repair, "_run_schema_constrained_codex", checked_transport)
    result, _ = repair.draft_article_with_codex(payload, cfg, tmp_path / "private", tmp_path / "budget.json")
    assert result["units"][0]["key"] == key


@pytest.mark.parametrize("successful_article,visited,expected_calls", [(None, 3, 3), (1, 5, 5)])
def test_campaign_stops_after_three_consecutive_transport_failures_and_success_resets(
    tmp_path, successful_article, visited, expected_calls,
):
    from copy import deepcopy

    from processors.codex_engine import CodexError

    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    original_article = audit["items"][0]
    original_dossier = dossiers["concept-stance"]
    audit["items"] = []
    dossiers = {}
    for index in range(6):
        cid = f"concept-stance-{index}"
        article = deepcopy(original_article)
        article["concept_id"] = cid
        audit["items"].append(article)
        dossier = deepcopy(original_dossier)
        dossier["concept"]["id"] = cid
        dossiers[cid] = dossier

    def transport(payload, *args, **kwargs):
        if payload["article"]["id"] != f"concept-stance-{successful_article}":
            raise CodexError("Fixture transport unavailable")
        return verify(payload, *args, **kwargs)

    checkpoint = tmp_path / "plans.json"
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, drafter=draft, verifier=transport)
    assert result["stopped"] == "transport_failure_circuit" and result["calls"] == expected_calls
    saved = read_json(checkpoint)
    assert len(saved["items"]) == visited
    assert sum(job["status"] == "failed" for item in saved["items"].values()
               for job in item["jobs"].values()) == visited - (successful_article is not None)
    assert all(value is None for article in audit["items"] for value in article["decisions"].values())
    resumed = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                  max_calls=20, retry_failed=True, drafter=draft, verifier=verify)
    assert resumed["article_states"] == {"verified": 6}
    assert resumed["calls"] == 6 - (successful_article is not None)


def test_coverage_first_clean_article_needs_no_draft_and_no_repeat(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path / "plans.json"
    def no_draft(*_args, **_kwargs):
        pytest.fail("A clean article must not be rewritten")
    first = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                               max_calls=20, drafter=no_draft, verifier=verify)
    second = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, drafter=no_draft, verifier=verify)
    assert first["calls"] == 1 and second["calls"] == 0
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert all(not u["edits"] and not u["quarantine"] for u in item["draft"]["units"])
    assert read_yaml(paths.content / "concepts/stance.yaml")["short_definition"] == "Keep a stable stance."


def test_targeted_repair_resumes_at_call_cap_and_clears_only_nullable_rating(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossiers["concept-stance"]["concept"]["difficulty"] = "intermediate"
    audit["items"][0]["decisions"]["field:difficulty"] = None
    checks = []
    drafts = []
    def audit_check(payload, *_args, **_kwargs):
        checks.append(set(payload["units"]))
        result, provenance = verify(payload)
        for u in result["units"]:
            if u["key"] == "field:difficulty" and payload["units"][u["key"]]["value"]:
                u.update(status="needs_fix", note="No difficulty rating in these owned captions.")
        return result, provenance
    def clear_rating(payload, *_args, **_kwargs):
        drafts.append(set(payload["units"]))
        assert set(payload["units"]) == {"field:difficulty"}
        u = RepairUnit(key="field:difficulty", status="needs_fix", note="Clear unsupported rating.",
                       supporting_segment_ids=[], edits=[{"field": "difficulty", "text": None}])
        return {"units": [u.model_dump()]}, {"method": "fixture"}
    checkpoint = tmp_path / "plans.json"
    for cap in (1, 1, 1):
        run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                            max_calls=cap, repair_confirmed=True, drafter=clear_rating, verifier=audit_check)
    assert drafts == [{"field:difficulty"}]
    assert checks[1:] == [{"field:difficulty"}]
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert item["status"] == "verified" and item["repair_attempted"]
    assert not any("reduce" in key or "revision" in key for key in item["jobs"])
    assert all(d is None for d in audit["items"][0]["decisions"].values())


def test_complete_proof_packing_shares_rows_without_cross_citation_ownership(tmp_path):
    _, _, audit, dossiers = fixture_inputs(tmp_path, rows=9)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, ["evidence:0:e"])
    units["evidence:0:e"]["allowed_segment_ids"] = ["video:00000", "video:00001"]
    units["relation:0"] = {**deepcopy(units["evidence:0:e"]), "allowed_segment_ids": ["video:00001", "video:00002"]}
    proposal = {"units": [RepairUnit(key=key, status="uncertain", note="Pending.", supporting_segment_ids=[]).model_dump() for key in units]}
    payloads, exceptions = verification_payloads(dossier, units, proposal, 12)
    assert not exceptions and len(payloads) == 1
    assert {r["id"] for r in payloads[0]["selected_rows"]} == {"video:00000", "video:00001", "video:00002"}
    assert len(payloads[0]['selected_rows']) + len(payloads[0]['context_rows']) == 9
    assert payloads[0]["units"]["relation:0"]["allowed_segment_ids"] == ["video:00001", "video:00002"]
    bad = verify(payloads[0])[0]["units"]
    bad[0]["supporting_segment_ids"] = ["video:00002"]
    with pytest.raises(ValueError, match="Foreign"):
        validate_units(bad, payloads[0]["units"], draft=False)


def test_nullable_rating_change_reuses_independent_citation_cache(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path / "plans.json"
    checks = []
    def tracked(payload, *_args, **_kwargs):
        checks.append(set(payload["units"]))
        return verify(payload)
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=20, verifier=tracked)
    dossiers["concept-stance"]["concept"]["difficulty"] = "easy"
    audit["items"][0]["decisions"]["field:difficulty"] = None
    audit["items"][0]["fingerprint"] = sha256_json(dossiers)
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, verifier=tracked)
    assert checks[1] == {"field:difficulty"}
    assert result["cached_verification_units"] == len(checks[0])


def test_cached_sibling_rows_remain_negative_context_for_pending_citation(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers['concept-stance']
    source = deepcopy(dossier['sources'][0])
    source['selected_rows'] = source['selected_rows'][-1:]
    source['context_rows'] = dossier['sources'][0]['selected_rows'][:-1]
    source['source'].update(start_ms=6000, url='https://www.youtube.com/watch?v=video&t=6s',
                            segment_ids=['video:00002'])
    evidence = {**deepcopy(dossier['concept']['evidence'][0]), 'id': 'e2', 'source': source['source']}
    dossier['concept']['evidence'].append(evidence)
    dossier['sources'].append(source)
    audit['items'][0]['decisions']['evidence:1:e2'] = None
    audit['items'][0]['fingerprint'] = sha256_json(dossier)
    seen = []
    def tracked(payload, *_args, **_kwargs):
        seen.append(deepcopy(payload))
        return verify(payload)
    checkpoint = tmp_path/'plans.json'
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path/'budget.json', checkpoint,
                        max_calls=20, verifier=tracked)
    evidence['excerpt'] = 'Keep a stable stance and balance.'
    audit['items'][0]['fingerprint'] = sha256_json(dossier)
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path/'budget.json', checkpoint,
                        max_calls=20, verifier=tracked)
    assert set(seen[-1]['units']) == {'evidence:1:e2'}
    assert [r['id'] for r in seen[-1]['selected_rows']] == ['video:00002']
    assert {r['id'] for r in seen[-1]['context_rows']} == {'video:00000', 'video:00001'}


def coverage_fixture(tmp_path):
    paths, cfg, _, dossiers = fixture_inputs(tmp_path)
    original = dossiers['concept-stance']
    video = Video(id='video', title='Fixture', canonical_url='https://www.youtube.com/watch?v=video',
                  duration_ms=9000, transcript=TranscriptTrack(video_id='video', language='English',
                  language_code='en', is_generated=False, acquisition_method='fixture',
                  segments=original['sources'][0]['selected_rows']))
    concept = Concept.model_validate(original['concept'])
    concept.evidence[0].source.segment_ids = ['video:00000', 'video:00002']
    with (paths.content/'concepts/stance.yaml').open('w', encoding='utf-8') as handle:
        YAML().dump(concept.model_dump(mode='json'), handle)
    dossier = audit_dossier(concept, {video.id: video}, {concept.id: concept})
    audit = build_published_audit([concept], [video], paths.id)
    return paths, cfg, concept, video, dossier, audit


@pytest.mark.parametrize('invalid', ['padding', 'missing_old_id', 'unreviewed'])
def test_source_coverage_never_trims_bounds_drops_ids_or_restores_exclusions(tmp_path, invalid):
    _, _, concept, video, _, _ = coverage_fixture(tmp_path)
    if invalid == 'padding':
        concept.evidence[0].source.end_ms = 9500
        video.duration_ms = 12000
    elif invalid == 'missing_old_id':
        concept.evidence[0].source.segment_ids.append('video:missing')
    else:
        concept.evidence[0].review_status = 'unreviewed'
    assert source_coverage_corrections(concept, {video.id: video}) == []


def test_completed_source_planning_verifies_new_owned_proof_and_requires_primary(tmp_path):
    paths, cfg, concept, video, dossier, audit = coverage_fixture(tmp_path)
    checkpoint = tmp_path/'plans.json'
    canonical = paths.content/'concepts/stance.yaml'
    before = canonical.read_bytes()
    for key in audit['items'][0]['decisions']:
        audit['items'][0]['decisions'][key] = {'status': 'needs_fix', 'note': 'Old incomplete proof.'}
    seen = []
    def tracked(payload, *_args, **_kwargs):
        seen.append(deepcopy(payload))
        assert set(payload['units']['evidence:0:e']['allowed_segment_ids']) == {
            'video:00000', 'video:00001', 'video:00002'}
        return verify(payload)
    result = run_repair_campaign(audit, {concept.id: dossier}, cfg, tmp_path, tmp_path/'budget.json',
        checkpoint, max_calls=3, verifier=tracked, source_context=([video], [concept]))
    assert result['calls'] == 1 and len(seen) == 1
    saved = read_json(checkpoint)
    item = saved['items'][concept.id]
    assert item['scope'] == 'owned_source_correction' and item['status'] == 'verified'
    assert 'Added caption IDs: video:00001; spoken bounds unchanged.' in render_repair_plans(saved)
    assert item['review_findings'] == {} and item['previous_source_findings']
    assert canonical.read_bytes() == before
    assert concept.evidence[0].source.segment_ids == ['video:00000', 'video:00002']
    with pytest.raises(ValueError, match='fresh complete primary'):
        apply_reviewed_plan(paths, item, dossier, 'Reviewer', source_context=([video], [concept]))
    review = primary_review(item)
    saved = reconcile_primary_reviews(saved, audit, [review])
    apply_reviewed_plan(paths, saved['items'][concept.id], dossier, 'Reviewer',
                        source_context=([video], [concept]))
    applied = read_yaml(canonical)
    assert applied['evidence'][0]['source']['segment_ids'] == ['video:00000', 'video:00001', 'video:00002']
    assert applied['evidence'][0]['source']['start_ms'] == 0
    assert applied['evidence'][0]['source']['end_ms'] == 9000
    assert applied['short_definition'] == concept.short_definition


def test_completed_source_plan_resumes_and_refreshes_changed_profile(tmp_path):
    _, cfg, concept, video, dossier, audit = coverage_fixture(tmp_path)
    checkpoint = tmp_path/'plans.json'
    kwargs = {'max_calls': 3, 'verifier': verify, 'source_context': ([video], [concept])}
    args = (audit, {concept.id: dossier}, cfg, tmp_path, tmp_path/'budget.json', checkpoint)
    assert run_repair_campaign(*args, **kwargs)['calls'] == 1
    assert run_repair_campaign(*args, **kwargs)['calls'] == 0
    cfg.write_text('codex:\n  default_model: fixture\n  reasoning_effort: high\n  max_segments_per_job: 80\n')
    assert run_repair_campaign(*args, **kwargs)['calls'] == 1
    assert read_json(checkpoint)['items'][concept.id]['planning_config']['reasoning_effort'] == 'high'


def test_source_completion_keeps_exact_ready_plan_before_proposing_metadata_changes(tmp_path):
    _, cfg, concept, video, dossier, audit = coverage_fixture(tmp_path)
    checkpoint = tmp_path/'plans.json'
    args = (audit, {concept.id: dossier}, cfg, tmp_path, tmp_path/'budget.json', checkpoint)
    run_repair_campaign(*args, max_calls=3, verifier=verify)
    saved = read_json(checkpoint)
    saved = reconcile_primary_reviews(saved, audit, [primary_review(saved['items'][concept.id])])
    write_json(checkpoint, saved)
    result = run_repair_campaign(*args, max_calls=3, verifier=verify, source_context=([video], [concept]))
    assert result['calls'] == 0
    assert read_json(checkpoint)['items'][concept.id] == saved['items'][concept.id]


def test_source_coverage_adds_only_actual_rows_fully_inside_original_window(tmp_path):
    _, _, concept, video, _, _ = coverage_fixture(tmp_path)
    outside = video.transcript.segments[-1].model_copy(update={'id': 'video:00003', 'start_ms': 9000})
    video.transcript.segments.append(outside)
    video.duration_ms = 12000
    before = concept.model_dump(mode='json')
    corrections = source_coverage_corrections(concept, {video.id: video})
    assert corrections[0]['source'] == {**before['evidence'][0]['source'],
                                       'segment_ids': ['video:00000', 'video:00001', 'video:00002']}
    assert concept.model_dump(mode='json') == before


def test_verification_uses_full_configured_budget_when_no_context_is_missing(tmp_path):
    _, _, _, dossiers = fixture_inputs(tmp_path, rows=8)
    dossier = dossiers['concept-stance']
    units = unit_inputs(dossier, ['evidence:0:e'])
    proposal, _ = draft({'units': units})
    payloads, exceptions = verification_payloads(dossier, units, proposal, cap=8)
    assert not exceptions and len(payloads) == 1
    assert len(payloads[0]['selected_rows']) == 8 and payloads[0]['context_rows'] == []


@pytest.mark.parametrize('other_citation', [False, True])
def test_field_support_seed_keeps_whole_owned_citation_and_its_condition(tmp_path, other_citation):
    _, _, _, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers['concept-stance']
    dossier['sources'][0]['selected_rows'][0].update(
        text='If you break immediately, the', normalized_text='If you break immediately, the')
    dossier['sources'][0]['selected_rows'][1].update(
        text='racket head stays dead.', normalized_text='racket head stays dead.')
    if other_citation:
        other = deepcopy(dossier['sources'][0])
        other['source'] = {'video_id': 'other', 'start_ms': 0, 'end_ms': 3000,
                          'url': 'https://www.youtube.com/watch?v=other&t=0s', 'segment_ids': ['other:0']}
        other['selected_rows'] = [{**other['selected_rows'][0], 'id': 'other:0', 'video_id': 'other'}]
        other['context_rows'] = []
        other['video'] = {**other['video'], 'id': 'other'}
        dossier['sources'].append(other)
        dossier['concept']['evidence'].append({**deepcopy(dossier['concept']['evidence'][0]),
                                               'id': 'e2', 'source': other['source']})
    units = unit_inputs(dossier, ['field:short_definition'])
    proposal, _ = draft({'units': units})
    proposal['units'][0]['supporting_segment_ids'] = ['video:00001']
    payloads, exceptions = verification_payloads(dossier, units, proposal, cap=80)
    assert not exceptions and len(payloads) == 1
    assert set(payloads[0]['units']['field:short_definition']['allowed_segment_ids']) == {
        'video:00000', 'video:00001', 'video:00002'}
    assert {row['id'] for row in payloads[0]['selected_rows']} == {
        'video:00000', 'video:00001', 'video:00002'}


def primary_review(item, ready=True):
    return {"concept_id": item["concept_id"], "plan_hash": item["plan_hash"], "fingerprint": item["fingerprint"],
            "reviewer": "Fixture primary reviewer", "ready_for_application": ready,
            "decisions": {u["key"]: {"status": "supported", "note": "Exact captions inspected."}
                          for u in item["draft"]["units"]}}


def test_rejected_proposal_quarantine_requires_primary_before_reauthoring(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path/"plans.json"
    before = (paths.content/"concepts/stance.yaml").read_bytes()

    def initial_check(payload, *_args, **_kwargs):
        result, provenance = verify(payload)
        for unit in result["units"]:
            if unit["key"].startswith("evidence:"):
                unit.update(status="needs_fix", note="Use direct supported prose; omission is not justified.")
        return result, provenance

    def exclude(payload, *_args, **_kwargs):
        return {"units": [RepairUnit(key=key, status="needs_fix", note="Proposed exclusion.",
            supporting_segment_ids=value["allowed_segment_ids"], quarantine=True).model_dump()
            for key, value in payload["units"].items()]}, {"method": "fixture_draft"}

    args = (audit, dossiers, cfg, tmp_path, tmp_path/"budget.json", checkpoint)
    run_repair_campaign(*args, max_calls=20, repair_confirmed=True, drafter=exclude, verifier=initial_check)
    saved = read_json(checkpoint)
    item = saved["items"]["concept-stance"]
    evidence = next(u for u in item["draft"]["units"] if u["key"].startswith("evidence:"))
    assert evidence["quarantine"] and item["status"] == "exceptions"
    assert run_repair_campaign(*args, max_calls=20, repair_confirmed=True,
                              drafter=exclude, verifier=initial_check)["calls"] == 0
    review = primary_review(item, ready=False)
    review["decisions"][evidence["key"]] = {"status": "needs_fix",
        "note": "Retain the valid selected-caption instruction; replace its reason with direct prose."}
    write_json(checkpoint, reconcile_primary_reviews(saved, audit, [review]))
    seen = []

    def retain(payload, *_args, **_kwargs):
        seen.extend(payload["units"])
        return {"units": [RepairUnit(key=key, status="needs_fix", note="Primary-requested retained instruction.",
            supporting_segment_ids=value["allowed_segment_ids"], edits=[{
                "field": "reason", "text": "Keep a stable stance.", "strings": None, "facets": None}]).model_dump()
            for key, value in payload["units"].items()]}, {"method": "fixture_primary_repair"}

    result = run_repair_campaign(*args, max_calls=20, repair_confirmed=True, drafter=retain, verifier=verify)
    current = read_json(checkpoint)["items"]["concept-stance"]
    restored = next(u for u in current["draft"]["units"] if u["key"] == evidence["key"])
    assert result["calls"] >= 2 and seen == [evidence["key"]]
    assert not restored["quarantine"] and current["status"] == "verified"
    assert current["primary_review"]["plan_hash"] != current["plan_hash"]
    with pytest.raises(ValueError, match="[Pp]rimary"):
        apply_reviewed_plan(paths, current, dossiers["concept-stance"], "Fixture reviewer")
    assert (paths.content/"concepts/stance.yaml").read_bytes() == before


def test_primary_import_is_atomic_stale_safe_and_blocks_rejected_application(tmp_path):
    paths, item, dossier = ready_plan(tmp_path)
    saved = read_json(paths.data("manifests") / "published-repair-plans.json")
    audit = read_json(paths.data("manifests") / "published-audit.json")
    good = primary_review(item)
    bad = {**good, "plan_hash": "stale"}
    before = deepcopy(saved)
    with pytest.raises(ValueError, match="Stale"):
        reconcile_primary_reviews(saved, audit, [bad])
    assert saved == before
    rejected = primary_review(item, ready=False)
    rejected["decisions"]["field:short_definition"] = {"status": "needs_fix", "note": "Missing a condition."}
    result = reconcile_primary_reviews(saved, audit, [rejected])
    assert result["items"][item["concept_id"]]["status"] == "exceptions"
    with pytest.raises(ValueError, match="verified plan"):
        apply_reviewed_plan(paths, result["items"][item["concept_id"]], dossier, "Primary reviewer")
    assert saved == before
    assert reconcile_primary_reviews(saved, audit, [good])["items"][item["concept_id"]]["primary_review"] == good


def test_legacy_verified_and_exception_plans_are_not_replayed(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path / "plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=20, verifier=verify)
    saved = read_json(checkpoint)
    item = saved["items"]["concept-stance"]
    item.pop("workflow")
    item["status"] = "exceptions"
    original = deepcopy(item)
    write_json(checkpoint, saved)
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, verifier=verify)
    assert result["calls"] == 0 and read_json(checkpoint)["items"]["concept-stance"] == original


def test_batch_article_limit_releases_work_without_losing_remaining_items(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    other = deepcopy(audit["items"][0])
    other["concept_id"] = "concept-other"
    audit["items"].append(other)
    dossiers["concept-other"] = deepcopy(dossiers["concept-stance"])
    dossiers["concept-other"]["concept"]["id"] = "concept-other"
    checkpoint = tmp_path / "plans.json"
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, max_articles=1, verifier=verify)
    assert result["stopped"] == "article_limit" and result["calls"] == 1
    second = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, max_articles=1, verifier=verify)
    assert second["calls"] == 1
    assert len(read_json(checkpoint)["items"]) == 2


def test_facet_vocabulary_is_in_schema_and_runtime_rejects_unknown_values(tmp_path, monkeypatch):
    import json

    import processors.published_repair as repair
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    units = unit_inputs(dossier, ["field:facets"])
    payload = article_payloads(dossier, units, 80)[0]
    payload["facet_vocabulary"] = {"category": ["fundamentals"]}
    def transport(prompt, schema, response_model, *_args, **_kwargs):
        assert json.loads(prompt[prompt.index('{"article":'):])["facet_vocabulary"] == payload["facet_vocabulary"]
        item = schema["properties"]["units"]["properties"]["field:facets"]
        facets = item["properties"]["edits"]["items"]["properties"]["facets"]["items"]["anyOf"]
        assert facets[0]["properties"]["values"]["items"]["enum"] == ["fundamentals"]
        return response_model.model_validate(draft(payload)[0]), {"method": "fixture"}
    monkeypatch.setattr(repair, "_run_schema_constrained_codex", transport)
    repair.draft_article_with_codex(payload, cfg, tmp_path, tmp_path / "budget.json")
    audit["items"][0]["decisions"]["field:facets"] = {"status": "needs_fix", "note": "Incorrect category."}
    def invalid(payload, *_args, **_kwargs):
        result, provenance = draft(payload)
        for u in result["units"]:
            if u["key"] == "field:facets":
                u.update(status="needs_fix", edits=[{"field": "facets", "text": None, "strings": None,
                                                     "facets": [{"name": "category", "values": ["invented"]}]}])
        return result, provenance
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", tmp_path / "plans.json",
                                max_calls=20, repair_confirmed=True, drafter=invalid, verifier=verify,
                                facet_vocabulary=payload["facet_vocabulary"])
    assert result["stopped"] == "failed_job"


def test_cli_rejects_unbounded_audit_before_any_model_call():
    from typer.testing import CliRunner

    from processors.cli import app
    result = CliRunner().invoke(app, ["plan-published-repairs", "--max-calls", "2000"])
    assert result.exit_code != 0 and "20" in result.output


def test_imported_rejection_repairs_proposed_value_and_requires_new_final_review(tmp_path):
    paths, item, dossier = ready_plan(tmp_path)
    checkpoint = paths.data("manifests") / "published-repair-plans.json"
    audit = read_json(paths.data("manifests") / "published-audit.json")
    review = primary_review(item, ready=False)
    review["decisions"]["evidence:0:e"] = {"status": "needs_fix", "note": "Rewrite the reason directly."}
    write_json(checkpoint, reconcile_primary_reviews(read_json(checkpoint), audit, [review]))
    calls = []
    def repair(payload, *_args, **_kwargs):
        calls.append(set(payload["units"]))
        assert set(payload["units"]) == {"evidence:0:e"}
        result, provenance = draft(payload)
        result["units"][0].update(status="needs_fix", edits=[{"field": "reason", "text": "Keep the stance stable.", "strings": None, "facets": None}])
        return result, provenance
    run_repair_campaign(audit, {item["concept_id"]: dossier}, paths.root / "processors.yaml", tmp_path,
                        tmp_path / "budget.json", checkpoint, max_calls=20, repair_confirmed=True,
                        drafter=repair, verifier=verify)
    final = read_json(checkpoint)["items"][item["concept_id"]]
    assert calls == [{"evidence:0:e"}] and final["status"] == "verified"
    assert final["plan_hash"] != review["plan_hash"]
    with pytest.raises(ValueError, match="Primary review"):
        apply_reviewed_plan(paths, final, dossier, "Fixture")


def test_new_ready_primary_review_rechecks_exception_without_redrafting(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path / "plans.json"
    def reject(payload, *_args, **_kwargs):
        result, provenance = verify(payload)
        next(u for u in result["units"] if u["key"] == "evidence:0:e").update(status="needs_fix", note="Ambiguous.")
        return result, provenance
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=20, verifier=reject)
    saved = read_json(checkpoint)
    review = primary_review(saved["items"]["concept-stance"])
    write_json(checkpoint, reconcile_primary_reviews(saved, audit, [review]))
    def no_draft(*_args, **_kwargs):
        pytest.fail("Primary-ready proposal should receive source verification, not rewriting")
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, repair_confirmed=True, drafter=no_draft, verifier=verify)
    assert result["calls"] == 1 and result["article_states"] == {"verified": 1}


def test_missing_owned_caption_ids_are_parked_without_model_or_source_invention(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    dossier = dossiers["concept-stance"]
    dossier["sources"][0]["selected_rows"] = []
    def no_model(*_args, **_kwargs):
        pytest.fail("Missing source proof must be reconciled before model repair")
    checkpoint = tmp_path / "plans.json"
    report = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                                max_calls=20, repair_confirmed=True, drafter=no_model, verifier=no_model)
    assert report["calls"] == 0 and report["article_states"] == {"exceptions": 1}
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert all(not u["edits"] and not u["quarantine"] for u in item["draft"]["units"])
    assert all(u["status"] == "needs_fix" for u in item["verification"]["units"])


def test_new_machine_verified_plan_cannot_apply_without_exact_final_primary_review(tmp_path):
    paths, cfg, audit, dossiers = fixture_inputs(tmp_path)
    checkpoint = tmp_path / "plans.json"
    run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint,
                        max_calls=20, verifier=verify)
    item = read_json(checkpoint)["items"]["concept-stance"]
    assert item["status"] == "verified"
    before = (paths.content / "concepts/stance.yaml").read_bytes()
    with pytest.raises(ValueError, match="exact final primary review"):
        apply_reviewed_plan(paths, item, dossiers["concept-stance"], "Declared reviewer alone")
    assert before == (paths.content / "concepts/stance.yaml").read_bytes()


def test_primary_can_allow_nonvisual_changes_while_footage_remains_unreviewed(tmp_path):
    paths, item, _ = ready_plan(tmp_path)
    audit = read_json(paths.data("manifests") / "published-audit.json")
    item["draft"]["units"].append(RepairUnit(key="visual:0:e", status="needs_footage", note="Not watched.", supporting_segment_ids=[]).model_dump())
    item["verification"]["units"].append(VerifiedUnit(key="visual:0:e", status="needs_footage", note="Not watched.", supporting_segment_ids=[]).model_dump())
    item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
    review = primary_review(item)
    review["decisions"]["visual:0:e"] = {"status": "needs_footage", "note": "No footage inspected; visual claim remains pending."}
    saved = {"items": {item["concept_id"]: item}}
    result = reconcile_primary_reviews(saved, audit, [review])
    assert result["items"][item["concept_id"]]["verification"]["units"][-1]["status"] == "needs_footage"
    review["decisions"]["visual:0:e"]["status"] = "supported"
    with pytest.raises(ValueError, match="Invalid primary"):
        reconcile_primary_reviews(saved, audit, [review])

@pytest.mark.parametrize("external_edit", [False, True])
def test_batch_snapshot_reuse_and_external_write_guard(tmp_path, monkeypatch, external_edit):
    import typer

    import processors.cli as cli
    from processors.pipeline import load_reviewed_concepts
    from processors.published_audit import AUDIT_VERSION
    from processors.published_repair import reviewed_rating_removal_plan

    paths, template, dossier = rating_plan_fixture(tmp_path)
    other = deepcopy(template["concept"])
    other.update(id="concept-other", slug="other", label="Other topic")
    with (paths.content / "concepts/other.yaml").open("w", encoding="utf-8") as f:
        YAML().dump(other, f)
    video = Video(id="video", title="Fixture", canonical_url="https://www.youtube.com/watch?v=video", duration_ms=9000,
                  transcript=TranscriptTrack(video_id="video", language="English", language_code="en", is_generated=False,
                  acquisition_method="fixture", segments=dossier["sources"][0]["selected_rows"]))
    concepts = load_reviewed_concepts(paths.content / "concepts")
    concept_map = {c.id: c for c in concepts}
    plans = {"items": {}}
    for concept in concepts:
        current = audit_dossier(concept, {video.id: video}, concept_map)
        item = deepcopy(template)
        item.update(concept_id=concept.id, concept=current["concept"], identity=concept.id,
                    fingerprint=sha256_json({"version": AUDIT_VERSION, "dossier": current}))
        item["plan_hash"] = sha256_json({k: item[k] for k in ("identity", "draft", "verification")})
        item["primary_review"].update(plan_hash=item["plan_hash"], fingerprint=item["fingerprint"])
        plans["items"][concept.id] = reviewed_rating_removal_plan(item, current, "Fixture editor")
    write_json(paths.data("manifests") / "published-repair-plans.json", plans)
    monkeypatch.setattr(cli, "kb_paths", lambda *_args: paths)
    monkeypatch.setattr(cli, "load_videos", lambda *_args: [video])
    original = cli._published_audit_inputs
    loads = []

    def tracked(*args):
        result = original(*args)
        loads.append(True)
        if external_edit and len(loads) == 2:
            with (paths.content / "concepts/other.yaml").open("a", encoding="utf-8") as f:
                f.write("\n# external editor write\n")
        return result

    monkeypatch.setattr(cli, "_published_audit_inputs", tracked)
    if external_edit:
        with pytest.raises(typer.BadParameter, match="changed after application"):
            cli.apply_published_repairs(concept_ids="concept-stance,concept-other", reviewer="Fixture editor", kb=paths.id)
        assert read_yaml(paths.content / "concepts/other.yaml")["difficulty"] == "intermediate"
    else:
        cli.apply_published_repairs(concept_ids="concept-stance,concept-other", reviewer="Fixture editor", kb=paths.id)
        assert len(loads) == 3  # One initial read, one post-application read per article.
        assert all(c.difficulty is None for c in load_reviewed_concepts(paths.content / "concepts"))


def test_repair_report_separates_primary_and_machine_pending_work(tmp_path):
    from processors.published_repair import render_repair_plans

    _, item, _ = rating_plan_fixture(tmp_path)
    item["verification"]["units"][-1]["status"] = "uncertain"
    item["verification"]["units"].append({"key": "visual:0:e", "status": "needs_footage"})
    report = render_repair_plans({"items": {item["concept_id"]: item}})
    assert "Text and metadata (1): concept-stance" in report
    assert "Citations and relations (1): concept-stance" in report
    assert "Footage (1): concept-stance" in report
    item.pop("verification")
    assert "Citations and relations (1): concept-stance" in render_repair_plans({"items": {item["concept_id"]: item}})
    item["status"] = "applied"
    assert "Text and metadata (0): (none)" in render_repair_plans({"items": {item["concept_id"]: item}})
