export type SourceSpan = {
  video_id: string;
  start_ms: number;
  end_ms: number;
  url: string;
  segment_ids: string[];
};

export type VisualSpan = {
  video_id: string;
  start_ms: number;
  end_ms: number;
  url: string;
  selection_method: 'nearby_visual_inference' | 'manual_review';
  note: string;
};

export type Evidence = {
  id: string;
  evidence_type: string;
  excerpt: string;
  reason: string;
  confidence: number;
  visual_status: string;
  source: SourceSpan;
  spoken_context_end_ms?: number;
  visual_source?: VisualSpan;
};

export type Relation = {
  relation_type: string;
  target_concept_id: string;
};

export type Concept = {
  id: string;
  slug: string;
  label: string;
  aliases: string[];
  short_definition: string;
  detailed_definition?: string;
  concept_type: string;
  facets: Record<string, string[]>;
  difficulty?: string;
  evidence: Evidence[];
  relations: Relation[];
  review_status: string;
};

export type Video = {
  id: string;
  title: string;
  canonical_url: string;
  channel_name: string;
  duration_ms: number;
  thumbnail_url?: string;
  availability: string;
};

export type TopicNode = {
  id: string;
  label: string;
  description?: string;
  concept_ids: string[];
  children: TopicNode[];
};

export type KnowledgeNavigation = {
  title: string;
  introduction: string;
  sections: TopicNode[];
};

export type Corpus = {
  generated_at: string;
  knowledge_base: { id: string; name: string; description: string };
  concepts: Concept[];
  videos: Video[];
  navigation?: KnowledgeNavigation;
};

export type CatalogEntry = { id: string; name: string; description: string; concept_count: number; video_count: number };
