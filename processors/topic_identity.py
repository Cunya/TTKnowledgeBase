"""Cheap, conservative topic-identity triage; never positive source proof."""
from __future__ import annotations

import re


def topic_identity_findings(concept: dict, sources: list[dict], rules: list[dict]) -> list[dict]:
    def matches(pattern, text):
        return bool(re.search(pattern, text, re.IGNORECASE))

    findings = []
    heading = concept.get('label') or ''
    for index, evidence in enumerate(concept.get('evidence', [])):
        source = next((s for s in sources if s['source'] == evidence['source']), None)
        if not source:
            continue
        title = source['video'].get('title') or ''
        captions = ' '.join(r['text'] for r in source['selected_rows'] + source['context_rows'])
        claim = ' '.join(str(evidence.get(k) or '') for k in ('excerpt', 'reason'))
        for rule in rules:
            if not matches(rule['article_pattern'], heading) or not matches(rule['source_title_pattern'], title):
                continue
            if (rule.get('article_exclude_pattern') and matches(rule['article_exclude_pattern'], heading)
                    or rule.get('source_title_exclude_pattern') and matches(rule['source_title_exclude_pattern'], title)):
                continue
            if matches(rule['bridge_pattern'], captions):
                continue
            if any(matches(pattern, heading) and matches(pattern, captions)
                   for pattern in rule.get('caption_identity_patterns', [])):
                continue
            findings.append({'key': f"evidence:{index}:{evidence['id']}", 'rule': rule['id'],
                             'video_id': evidence['source']['video_id'], 'title': title,
                             'caption_names_action': matches(rule['article_pattern'], captions),
                             'note': 'Topic identity conflict: source lesson and article name different actions. '
                                     'Translated action words alone cannot resolve it; confirm the actual role from '
                                     'owned captions or complete footage. Title is a warning, not claim support.',
                             'claim': claim})
    return findings
