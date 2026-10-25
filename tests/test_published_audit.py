from copy import deepcopy

import pytest

from processors.models import (
    Concept,
    ConceptEvidence,
    ConceptRelation,
    Segment,
    SourceSpan,
    TranscriptTrack,
    Video,
)
from processors.published_audit import (
    audit_dossier,
    audit_summary,
    build_published_audit,
    next_audit_items,
    record_audit_reviews,
)


def fixture():
    video = Video(
        id="audit-video", title="Audit", canonical_url="https://www.youtube.com/watch?v=audit-video",
        duration_ms=10000,
        transcript=TranscriptTrack(
            video_id="audit-video", language="English", language_code="en", is_generated=False,
            acquisition_method="fixture", segments=[
                Segment(id=f"audit-video:{i:05d}", video_id="audit-video", text=text, normalized_text=text,
                        start_ms=i*2000, duration_ms=2000)
                for i, text in enumerate(["First context.", "Keep the motion compact.", "Last context."])
            ],
        ),
    )
    source = SourceSpan(video_id=video.id, start_ms=2000, end_ms=4000,
                        url=video.canonical_url+"&t=2s", segment_ids=["audit-video:00001"])
    a = Concept(id="a", slug="a", label="A", short_definition="Keep the motion compact.",
                concept_type="technique", evidence=[ConceptEvidence(id="e", excerpt="Keep the motion compact.",
                reason="Compact motion.", confidence=0.9, evidence_type="explanation", source=source)])
    b = a.model_copy(deep=True, update={"id": "b", "slug": "b", "label": "B"})
    a.relations = [ConceptRelation(relation_type="related_to", target_concept_id="b", sources=[source], confidence=0.9)]
    return [a, b], [video]


def reviews_for(audit, status="supported"):
    return [{
        "concept_id": item["concept_id"], "fingerprint": item["fingerprint"], "reviewer": "fixture-editor",
        "decisions": {key: {"status": status, "note": "Reviewed selected audit-video:00001."}
                      for key in item["decisions"]},
    } for item in audit["items"]]


def test_overlap_change_preserves_claims_requires_separate_review():
    concepts, videos = fixture()
    concepts[0].relations = []
    concepts[1].aliases = [concepts[0].label]
    audit = build_published_audit(concepts, videos, "test")
    reviewed = record_audit_reviews(audit, reviews_for(audit))
    concepts[1].short_definition = "Changed related wording."
    current = build_published_audit(concepts, videos, "test", reviewed)
    a = current["items"][0]
    assert a["decisions"] == reviewed["items"][0]["decisions"]
    assert a["overlap_review_pending"]
    assert audit_summary(current)["overlap_reviews_pending"] == 1
    assert not audit_summary(current)["complete"]
    assert next_audit_items(current, 10)[0]["concept_id"] == "a"
    result = record_audit_reviews(current, [{"concept_id": "a", "fingerprint": a["fingerprint"],
        "reviewer": "Overlap editor", "overlap_only": True, "overlap_status": "supported",
        "note": "Distinct concepts; shared alias remains intentional."}])
    assert result["items"][0]["decisions"] == a["decisions"]
    assert not result["items"][0]["overlap_review_pending"]
    assert not audit_summary(result)["complete"]  # B's changed claim still needs review.


def test_actual_target_and_caption_changes_reopen_claims():
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, "test")
    reviewed = record_audit_reviews(audit, reviews_for(audit))
    concepts[1].short_definition = "Changed target claim."
    result = build_published_audit(concepts, videos, "test", reviewed)
    assert all(v is None for v in result["items"][0]["decisions"].values())
    concepts[1].short_definition = "Keep the motion compact."
    videos[0].transcript.segments[1].text = "Different caption."
    result = build_published_audit(concepts, videos, "test", reviewed)
    assert all(v is None for v in result["items"][0]["decisions"].values())


def test_context_refresh_does_not_discard_pending_advisory_overlap():
    concepts, videos = fixture()
    concepts[0].relations = []
    concepts[1].aliases = [concepts[0].label]
    reviewed = record_audit_reviews(build_published_audit(concepts, videos, 'test'),
        reviews_for(build_published_audit(concepts, videos, 'test')))
    concepts[1].short_definition = 'Changed related wording.'
    advisory = build_published_audit(concepts, videos, 'test', reviewed)
    assert advisory['items'][0]['overlap_review_pending']
    videos[0].transcript.segments[0].text = 'New actual surrounding condition.'
    refreshed = build_published_audit(concepts, videos, 'test', advisory)
    assert refreshed['items'][0]['overlap_review_pending']
    assert all(value is None for value in refreshed['items'][0]['decisions'].values())


def test_sparse_citation_keeps_complete_clip_context_without_expanding_owned_ids():
    concepts, videos = fixture()
    concept, video = concepts[0], videos[0]
    video.duration_ms = 20000
    video.transcript.segments = [Segment(id=f'audit-video:{i:05d}', video_id=video.id,
        text='Keep the motion compact.' if i in {0, 9} else 'Intervening context.',
        normalized_text='Context.', start_ms=i*2000, duration_ms=2000) for i in range(10)]
    concept.relations = []
    concept.evidence[0].source = SourceSpan(video_id=video.id, start_ms=0, end_ms=20000,
        url=video.canonical_url+'&t=0s', segment_ids=['audit-video:00000', 'audit-video:00009'])
    dossier = audit_dossier(concept, {video.id: video}, {concept.id: concept})
    assert [r['id'] for r in dossier['sources'][0]['selected_rows']] == concept.evidence[0].source.segment_ids
    assert {r['id'] for r in dossier['sources'][0]['context_rows']} == {
        f'audit-video:{i:05d}' for i in range(1, 9)}
    reviewed = record_audit_reviews(build_published_audit([concept], [video], 'test'),
        reviews_for(build_published_audit([concept], [video], 'test')))
    video.transcript.segments[4].text = 'Unless the ball is high.'
    current = build_published_audit([concept], [video], 'test', reviewed)
    assert current['items'][0]['fingerprint'] != reviewed['items'][0]['fingerprint']
    assert all(value is None for value in current['items'][0]['decisions'].values())


def test_legacy_claim_cache_bootstraps_only_identical_inputs():
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, "test")
    reviewed = record_audit_reviews(audit, reviews_for(audit))
    for item in reviewed["items"]:
        item.pop("claim_fingerprint")
        item.pop("overlap_fingerprint")
    same = build_published_audit(concepts, videos, "test", reviewed)
    assert all(v for v in same["items"][0]["decisions"].values())
    concepts[0].short_definition = "Changed own claim."
    changed = build_published_audit(concepts, videos, "test", reviewed)
    assert all(v is None for v in changed["items"][0]["decisions"].values())


def test_full_coverage_order_context_and_unresolved_completion():
    concepts, videos = fixture()
    audit = build_published_audit(list(reversed(concepts)), videos, "test")
    assert [item["concept_id"] for item in next_audit_items(audit, 10)] == ["a", "b"]
    assert "relation:0" in audit["items"][0]["decisions"]
    assert all(f"field:{field}" in audit["items"][0]["decisions"] for field in ["label", "facets", "short_definition"])
    dossier = audit_dossier(concepts[0], {v.id: v for v in videos}, {c.id: c for c in concepts})
    assert [row["id"] for row in dossier["sources"][0]["selected_rows"]] == ["audit-video:00001"]
    assert len(dossier["sources"][0]["context_rows"]) == 2
    reviewed = record_audit_reviews(audit, reviews_for(audit, "needs_fix"))
    assert not audit_summary(reviewed)["complete"]
    assert len(next_audit_items(reviewed, 10)) == 2
    clean = record_audit_reviews(audit, reviews_for(audit))
    assert audit_summary(clean)["complete"]
    assert next_audit_items(clean, 10) == []
    assert all(value is None for value in audit["items"][0]["decisions"].values())


def test_unchanged_resume_changed_captions_targets_and_removed_history():
    concepts, videos = fixture()
    audit = record_audit_reviews(build_published_audit(concepts, videos, "test"), reviews_for(build_published_audit(concepts, videos, "test")))
    resumed = build_published_audit(concepts, videos, "test", audit)
    assert resumed["items"] == audit["items"]
    videos[0].transcript.segments[1].normalized_text = "Changed claim."
    changed = build_published_audit(concepts, videos, "test", audit)
    assert all(item["reviewer"] is None for item in changed["items"])
    assert len(changed["history"]) == 2
    _, fresh_videos = fixture()
    concepts[1].short_definition = "A different topic."
    changed_target = build_published_audit(concepts, fresh_videos, "test", audit)
    assert changed_target["items"][0]["reviewer"] is None
    removed = build_published_audit(concepts[:1], fresh_videos, "test", audit)
    assert any(row["reason"] == "no_longer_public" for row in removed["history"])
    with pytest.raises(ValueError, match="KB/version"):
        build_published_audit(concepts, videos, "other", audit)


def test_topic_overlap_and_metadata_conflicts_block_unearned_completion():
    concepts, videos = fixture()
    concepts[1].aliases = [concepts[0].label]
    audit = build_published_audit(concepts, videos, "test")
    dossier = audit_dossier(concepts[0], {v.id: v for v in videos}, {c.id: c for c in concepts})
    assert dossier["topic_overlap_candidates"][0]["shared_terms"] == ["a"]
    videos[0].transcript.is_generated = True
    audit = build_published_audit(concepts, videos, "test")
    assert audit["source_metadata_findings"][0]["issue"] == "generated_track_declared_manual"
    reviewed = record_audit_reviews(audit, reviews_for(audit))
    assert not audit_summary(reviewed)["complete"]


def test_missing_saved_units_are_reopened_instead_of_credited():
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, "test")
    reviewed = record_audit_reviews(audit, reviews_for(audit))
    reviewed["items"][0]["decisions"].pop("evidence:0:e")
    refreshed = build_published_audit(concepts, videos, "test", reviewed)
    assert refreshed["items"][0]["reviewer"] is None
    assert "evidence:0:e" in refreshed["items"][0]["decisions"]
    assert not audit_summary(refreshed)["complete"]
    assert refreshed["history"][-1]["reason"] == "review_unit_coverage_changed"


def test_full_audit_gate_rejects_partial_and_invalid_saved_reviews(tmp_path, monkeypatch):
    import processors.cli as cli
    from processors.workspace import KnowledgeBasePaths

    concepts, videos = fixture()
    current = [build_published_audit(concepts, videos, "test")]
    paths = KnowledgeBasePaths(tmp_path, "test", "Test", "Test")
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    monkeypatch.setattr(cli, "_published_audit_inputs", lambda _paths: (concepts, videos, current[0]))
    with pytest.raises(cli.typer.Exit) as partial:
        cli.validate_published_audit("test")
    assert partial.value.exit_code == 1
    current[0] = record_audit_reviews(current[0], reviews_for(current[0]))
    cli.validate_published_audit("test")
    current[0]["items"][0]["decisions"]["field:label"]["note"] = ""
    with pytest.raises(cli.typer.BadParameter, match="Invalid saved"):
        cli.validate_published_audit("test")


def test_partial_stale_duplicate_and_invalid_decisions_fail_without_mutation():
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, "test")
    original = deepcopy(audit)
    for change in ("partial", "stale", "duplicate", "invalid"):
        reviews = reviews_for(audit)
        if change == "partial":
            reviews[0]["decisions"].pop("field:label")
        if change == "stale":
            reviews[0]["fingerprint"] = "stale"
        if change == "duplicate":
            reviews.append(deepcopy(reviews[0]))
        if change == "invalid":
            reviews[0]["decisions"]["field:label"]["status"] = "approved"
        with pytest.raises(ValueError):
            record_audit_reviews(audit, reviews)
        assert audit == original


def test_visual_support_requires_full_clip_and_structural_errors_block_completion():
    concepts, videos = fixture()
    concepts[0].evidence[0].visual_status = "verified_visual_demo"
    audit = build_published_audit(concepts, videos, "test")
    reviews = reviews_for(audit)
    with pytest.raises(ValueError, match="Full-clip"):
        record_audit_reviews(audit, reviews)
    reviews[0]["decisions"]["visual:0:e"]["status"] = "needs_footage"
    reviewed = record_audit_reviews(audit, reviews)
    assert not audit_summary(reviewed)["complete"]
    reviews[0]["decisions"]["visual:0:e"].update(status="supported", watched_full_clip=True)
    reviewed = record_audit_reviews(audit, reviews)
    assert reviewed["structural_errors"]  # verified claim lacks visual_source
    assert not audit_summary(reviewed)["complete"]


def test_cli_private_inventory_excludes_quarantine_and_resumes(tmp_path, monkeypatch):
    import processors.cli as cli
    from processors.utils import read_json, write_json
    from processors.workspace import KnowledgeBasePaths

    paths = KnowledgeBasePaths(tmp_path, "test", "Test", "Test")
    concepts, videos = fixture()
    directory = paths.content / "concepts"
    directory.mkdir(parents=True)
    for concept in concepts:
        cli.roundtrip_yaml.dump(concept.model_dump(mode="json"), directory / f"{concept.slug}.yaml")
    quarantined = concepts[0].model_copy(deep=True, update={"id": "c", "slug": "c", "review_status": "unreviewed"})
    cli.roundtrip_yaml.dump(quarantined.model_dump(mode="json"), directory / "c.yaml")
    write_json(paths.data("normalized") / "audit-video.json", videos[0])
    monkeypatch.setattr(cli, "kb_paths", lambda _kb: paths)
    cli.prepare_published_audit("test", markdown_output=tmp_path / "coverage.md")
    ledger = read_json(paths.data("manifests") / "published-audit.json")
    assert len(ledger["items"]) == 2
    cli.next_published_audit("test", limit=1)
    output = paths.data("manifests") / "published-audit-next.json"
    exported = read_json(output)
    assert exported["dossiers"][0]["concept"]["id"] == "a"
    exported["reviews"] = reviews_for(ledger)[:1]
    write_json(output, exported)
    cli.record_published_audit(output, "test")
    cli.next_published_audit("test", limit=1)
    assert read_json(output)["dossiers"][0]["concept"]["id"] == "b"
    stale_export = read_json(output)
    current = read_json(paths.data("manifests") / "published-audit.json")
    stale_export["reviews"] = reviews_for(current)[1:]
    write_json(output, stale_export)
    checkpoint = (paths.data("manifests") / "published-audit.json").read_bytes()
    videos[0].transcript.segments[1].normalized_text = "Changed after exporting."
    write_json(paths.data("normalized") / "audit-video.json", videos[0])
    with pytest.raises(cli.typer.BadParameter, match="Stale"):
        cli.record_published_audit(output, "test")
    assert (paths.data("manifests") / "published-audit.json").read_bytes() == checkpoint

@pytest.mark.parametrize('returned', [['a', 'b'], ['a'], ['a', 'a']])
def test_overlap_proposals_one_call_exact_coverage_and_no_claim_approval(tmp_path, monkeypatch, returned):
    from processors.published_audit import propose_overlap_reviews
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, 'fixture')
    for item in audit['items']:
        item['overlap_review_pending'] = True
    original = deepcopy(audit)
    calls = []
    def model(prompt, schema, response_model, *_args, **_kwargs):
        calls.append(prompt)
        assert 'Review ONLY advisory topic overlap' in prompt
        assert 'selected_rows' not in prompt and 'decisions' not in prompt
        return response_model.model_validate({'reviews': [
            {'concept_id': cid, 'status': 'supported', 'note': 'Distinct scope.'} for cid in returned]}), {}
    monkeypatch.setattr('processors.codex_engine._run_schema_constrained_codex', model)
    if returned != ['a', 'b']:
        with pytest.raises(ValueError, match='exactly once'):
            propose_overlap_reviews(audit, concepts, videos, tmp_path/'config.yaml', tmp_path, tmp_path/'budget.json')
    else:
        proposal = propose_overlap_reviews(audit, concepts, videos, tmp_path/'config.yaml', tmp_path, tmp_path/'budget.json')
        assert proposal['calls'] == 1
        assert all(r['reviewer'] == '' and r['overlap_only'] and 'decisions' not in r for r in proposal['reviews'])
        with pytest.raises(ValueError, match='reviewer'):
            record_audit_reviews(audit, proposal['reviews'])
    assert len(calls) == 1 and audit == original


def test_overlap_proposals_no_pending_work_costs_no_calls(tmp_path, monkeypatch):
    from processors.published_audit import propose_overlap_reviews
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, 'fixture')
    def forbidden(*args, **kwargs):
        pytest.fail('No pending overlaps must not invoke model')
    monkeypatch.setattr('processors.codex_engine._run_schema_constrained_codex', forbidden)
    result = propose_overlap_reviews(audit, concepts, videos, tmp_path/'config.yaml', tmp_path, tmp_path/'budget.json')
    assert result['calls'] == 0 and result['reviews'] == []

def test_overlap_cli_reuses_identical_scope_proposals(tmp_path, monkeypatch):
    from test_published_repair import fixture_inputs
    from typer.testing import CliRunner

    import processors.cli as cli

    paths, _, _, _ = fixture_inputs(tmp_path)
    concepts, videos = fixture()
    audit = build_published_audit(concepts, videos, 'fixture')
    for item in audit['items']:
        item['overlap_review_pending'] = True
    monkeypatch.setattr(cli, 'kb_paths', lambda kb: paths)
    monkeypatch.setattr(cli, '_published_audit_inputs', lambda p: (concepts, videos, audit))
    calls = []
    def proposer(*args, **kwargs):
        calls.append(True)
        return {'knowledge_base': 'fixture', 'reviews': [], 'calls': 1}
    monkeypatch.setattr('processors.published_audit.propose_overlap_reviews', proposer)
    runner = CliRunner()
    first = runner.invoke(cli.app, ['propose-published-overlaps', '--kb', 'fixture'])
    second = runner.invoke(cli.app, ['propose-published-overlaps', '--kb', 'fixture'])
    assert first.exit_code == second.exit_code == 0
    assert 'cached_overlap_proposals' in second.output and len(calls) == 1
