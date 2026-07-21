import type { Evidence } from '../types';

const words = (value: string) => new Set(value.toLowerCase().split(/[^a-z0-9]+/).filter((word) => word.length > 2));

export const evidenceRelevance = (evidence: Evidence, conceptLabel: string) => {
  const conceptWords = words(conceptLabel);
  const textWords = words(`${evidence.excerpt} ${evidence.reason}`);
  const overlap = conceptWords.size === 0 ? 0 : [...conceptWords].filter((word) => textWords.has(word)).length / conceptWords.size;
  const visual = evidence.visual_status === 'verified_visual_demo' && evidence.visual_source?.selection_method === 'manual_review' ? 1 : 0;
  return Math.round((Math.min(1, Math.max(0, evidence.confidence)) * 0.7 + overlap * 0.2 + visual * 0.1) * 100);
};

export const sortEvidenceByRelevance = (evidence: Evidence[], conceptLabel: string) => evidence
  .map((item, index) => ({ item, index, score: evidenceRelevance(item, conceptLabel) }))
  .sort((a, b) => b.score - a.score || a.index - b.index)
  .map(({ item }) => item);
