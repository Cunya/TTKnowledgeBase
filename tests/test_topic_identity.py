from copy import deepcopy
from pathlib import Path

from test_published_repair import fixture_inputs, read_json, run_repair_campaign

from processors.topic_identity import topic_identity_findings
from processors.utils import read_yaml

RULES = read_yaml(Path('config/kbs/table-tennis/taxonomy.yaml'))['topic_identity_rules']


def fixture_dossier(tmp_path):
    _, cfg, audit, dossiers = fixture_inputs(tmp_path)
    d = dossiers['concept-stance']
    d['concept']['label'] = 'Hook push'
    d['concept']['short_definition'] = 'A sideways push.'
    d['sources'][0]['video']['title'] = 'Easy Perfect Hook Serve in 4 Steps'
    for row in d['sources'][0]['selected_rows']:
        row['text'] = 'Next step hook push. Looks like a push. Add weight transfer.'
    return cfg, audit, dossiers, d


def test_translated_hook_push_cannot_override_serving_context(tmp_path):
    _, _, _, dossier = fixture_dossier(tmp_path)
    findings = topic_identity_findings(dossier['concept'], dossier['sources'], RULES)
    assert len(findings) == 1 and findings[0]['caption_names_action']
    assert findings[0]['key'] == 'evidence:0:e'


def test_explicit_receive_role_is_not_misclassified(tmp_path):
    _, _, _, dossier = fixture_dossier(tmp_path)
    dossier['sources'][0]['selected_rows'][0]['text'] = 'Receive a short serve using a hook serve motion.'
    assert not topic_identity_findings(dossier['concept'], dossier['sources'], RULES)


def test_corrected_serve_heading_and_other_domains_are_not_held(tmp_path):
    _, _, _, dossier = fixture_dossier(tmp_path)
    assert not topic_identity_findings(dossier['concept'], dossier['sources'], [])
    dossier['concept']['label'] = 'Hook serve brushing'
    dossier['concept']['short_definition'] = 'A hook serve progression.'
    assert not topic_identity_findings(dossier['concept'], dossier['sources'], RULES)


def test_conflict_stops_before_any_model_call_and_persists_findings(tmp_path):
    cfg, audit, dossiers, dossier = fixture_dossier(tmp_path)
    original = deepcopy(dossier)
    def forbidden(*args, **kwargs):
        raise AssertionError('Conflict must not spend tokens')
    checkpoint = tmp_path/'plans.json'
    result = run_repair_campaign(audit, dossiers, cfg, tmp_path, tmp_path/'budget.json', checkpoint,
                                max_calls=20, verifier=forbidden, drafter=forbidden,
                                topic_identity_rules=RULES)
    assert result['calls'] == 0 and result['parked_articles'] == 1
    assert read_json(checkpoint)['topic_identity_holds']['concept-stance']
    assert dossier == original

def test_generic_mechanics_does_not_assign_every_source_to_every_action(tmp_path):
    _, _, _, d = fixture_dossier(tmp_path)
    d['concept']['label'] = 'Generating spin at contact'
    d['concept']['short_definition'] = 'Looping, flicking and serving examples.'
    assert not topic_identity_findings(d['concept'], d['sources'], RULES)


def test_rally_loop_after_serve_is_distinct_from_serve_backswing(tmp_path):
    _, _, _, d = fixture_dossier(tmp_path)
    d['concept']['label'] = 'Forehand loop swing path'
    d['sources'][0]['video']['title'] = 'How to Serve to Set Up Your Next Attack'
    for r in d['sources'][0]['selected_rows']:
        r['text'] = 'Keep the racket horizontal. Large vertical motion makes a high slow serve.'
    assert topic_identity_findings(d['concept'], d['sources'], RULES)
    d['sources'][0]['selected_rows'][0]['text'] = 'On the forehand side choose to loop after the serve.'
    assert not topic_identity_findings(d['concept'], d['sources'], RULES)


def test_final_review_conflict_cannot_spend_or_be_marked_ready(tmp_path):
    from test_published_repair_bundle import prepare_fixture

    from processors.published_repair_bundle import _bundle_hash, review_repair_bundle
    paths, _, _, bundle, _ = prepare_fixture(tmp_path)
    taxonomy = paths.config/'taxonomy.yaml'
    from ruamel.yaml import YAML
    yaml = YAML()
    with taxonomy.open('w', encoding='utf-8') as f:
        yaml.dump({'topic_identity_rules': RULES}, f)
    d = next(iter(bundle['dossiers'].values()))
    d['concept']['label'] = 'Hook push'
    for s in d['sources']:
        s['video']['title'] = 'Easy Perfect Hook Serve'
        for r in s['selected_rows'] + s['context_rows']:
            r['text'] = 'Hook push, sideways brushing.'
    bundle["bundle_hash"] = _bundle_hash(bundle)
    def forbidden(*args, **kwargs):
        raise AssertionError('No paid review on unresolved topic conflict')
    review, report = review_repair_bundle(paths, bundle, tmp_path/'processors.yaml',
                                         max_calls=20, reviewer=forbidden)
    assert report == {'calls': 0, 'stopped': 'topic_identity_hold'}
    assert not review['ready_for_application'] and review['topic_identity_holds']
