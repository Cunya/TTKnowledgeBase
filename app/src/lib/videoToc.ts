import type { Concept, Corpus, Evidence, Video } from '../types';

export type VideoTocMoment = { concept: Concept; item: Evidence };
export type VideoTocGroup = { concept: Concept; moments: VideoTocMoment[] };
export type VideoTocEntry = {
  video: Video;
  concepts: Concept[];
  moments: VideoTocMoment[];
  groups: VideoTocGroup[];
};

export const formatTime = (milliseconds: number) => {
  const total = Math.floor(milliseconds / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
};

export const momentAnchor = (evidenceId: string) => `moment-${evidenceId}`;

// Candidate extraction often uses a transcript-reporting lead such as
// “Speaker explains …”. Remove that lead so the remaining wording can stand
// alone as a moment title rather than repeating a narrator label.
export const editorialNarrative = (text: string) => {
  const capitalize = (value: string) => value ? `${value[0].toUpperCase()}${value.slice(1)}` : value;
  const cleanEnd = (value: string) => value.trim().replace(/[.]+$/, '');

  // Some candidate excerpts are grammatically valid but make poor TOC names
  // because they repeat the extraction verb and the full explanatory clause.
  // Keep this as a display-only transform: canonical excerpts remain unchanged
  // for provenance, review, and overlap auditing.
  const compactDefinition = text.match(
    /^defines?\s+(?:the\s+)?(.+?)\s+as\s+.+?\s+because\s+the\s+distance\s+from\s+takeback\s+to\s+contact\s+is\s+short\.?$/i,
  );
  if (compactDefinition) return 'Short takeback-to-contact distance';

  const peakTiming = text.match(
    /^specifies?\s+that\s+(?:the\s+)?(.+?)\s+should\s+be\s+executed\s+at\s+the\s+peak\s+of\s+the\s+bounce\.?$/i,
  );
  if (peakTiming) return 'Peak-of-bounce timing';

  const definitionLead = text.match(/^defines?\s+(?:the\s+)?(.+?)\s+as\s+(.+?)\s+because\s+(.+)$/i);
  if (definitionLead) return `${capitalize(cleanEnd(definitionLead[1]))}: ${cleanEnd(definitionLead[2])}`;

  const specifiesLead = text.match(/^specifies?\s+that\s+(?:the\s+)?(.+?)\s+should\s+be\s+(.+)$/i);
  if (specifiesLead) return `${capitalize(cleanEnd(specifiesLead[1]))}: ${cleanEnd(specifiesLead[2])}`;

  const bareEditorialLead = text.match(
    /^(?:defines?|specifies?|warns?|explains?|describes?|states?|shows?|teaches?|recommends?|prescribes?|introduces?|contrasts?|links?|corrects?|frames?|provides?|identifies?|names?|demonstrates?|emphasizes?|distinguishes?|compares?|connects?|outlines?|details?|reinforces?|highlights?|focuses?|organizes?|diagnoses?|mentions?|notes?|adds?)\s+(?:that\s+)?(.+)$/i,
  );
  if (bareEditorialLead) return capitalize(cleanEnd(bareEditorialLead[1]));

  const transcriptDefinition = text.match(
    /^(?:the )?transcript\s+(?:(?:explicitly|repeatedly|directly|clearly|also|then|specifically)\s+)*defines?\s+(.+?)\s+as\s+(.+)$/i,
  );
  if (transcriptDefinition) {
    return `${capitalize(transcriptDefinition[1].trim())}: ${transcriptDefinition[2].trim()}`;
  }
  const transcriptLead = text.match(
    /^(?:the )?transcript\s+(?:(?:explicitly|repeatedly|directly|clearly|also|then|specifically)\s+)*(?:defines?|explains?|says?|states?|describes?|gives?|demonstrates?|identifies?|teaches?|argues?|warns?|recommends?|prescribes?|introduces?|contrasts?|links?|specifies?|corrects?|frames?|adds?|provides?|appears?|names?|shows?|tells?|breaks?|maps?|centers?|reduces?|turns?|uses?|ties?|mentions?|notes?|emphasizes?|distinguishes?|references?|asks?|does?|makes?|keeps?|moves?|discusses?|details?|reinforces?|indicates?|highlights?|focuses?|outlines?|compares?|connects?)\s+(?:that\s+)?(.*)$/i,
  );
  if (transcriptLead) return capitalize(transcriptLead[1].trim());
  const speakerLead = text.match(
    /^(?:the )?speaker\s+(?:(?:explicitly|repeatedly|directly|clearly|also|then)\s+)*(?:defines?|explains?|says?|states?|describes?|gives?|demonstrates?|identifies?|teaches?|argues?|warns?|recommends?|prescribes?|introduces?|contrasts?|links?|specifies?|corrects?|frames?|adds?|provides?|appears?|names?|shows?|tells?|breaks?|maps?|centers?|reduces?|turns?|uses?|ties?|mentions?|notes?|emphasizes?|distinguishes?|references?|asks?|does?|makes?|keeps?|moves?)\s+(.*)$/i,
  );
  if (speakerLead) return capitalize(speakerLead[1].trim());
  return capitalize(text.replace(/^(?:the )?(?:speaker|transcript)\s+/i, '').trim());
};

export const buildVideoTocEntry = (corpus: Corpus, video: Video): VideoTocEntry => {
  const concepts = corpus.concepts.filter((concept) => concept.evidence.some((item) => item.source.video_id === video.id));
  const seen = new Set<string>();
  const moments = concepts.flatMap((concept) => concept.evidence
    .filter((item) => item.source.video_id === video.id)
    .map((item) => ({ concept, item })))
    .sort((a, b) => a.item.source.start_ms - b.item.source.start_ms || a.concept.label.localeCompare(b.concept.label))
    .filter(({ concept, item }) => {
      const key = `${concept.slug}:${video.id}:${Math.floor(item.source.start_ms / 1000)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  const groups = concepts.map((concept) => ({
    concept,
    moments: moments.filter((moment) => moment.concept.slug === concept.slug),
  }))
    .filter((group) => group.moments.length > 0)
    .sort((a, b) => a.moments[0].item.source.start_ms - b.moments[0].item.source.start_ms || a.concept.label.localeCompare(b.concept.label));
  return { video, concepts, moments, groups };
};

export const buildVideoTocEntries = (corpus: Corpus) => corpus.videos.map((video) => buildVideoTocEntry(corpus, video));
