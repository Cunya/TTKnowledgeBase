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
  const match = text.match(
    /^(?:the )?speaker\s+(?:(?:explicitly|repeatedly|directly|clearly|also|then)\s+)*(?:explains?|says?|states?|describes?|gives?|demonstrates?|identifies?|teaches?|argues?|warns?|recommends?|prescribes?|introduces?|contrasts?|links?|specifies?|corrects?|frames?|adds?|provides?|appears?|names?|shows?|tells?|breaks?|maps?|centers?|reduces?|turns?|uses?|ties?|mentions?|notes?|emphasizes?|distinguishes?|references?|asks?|does?|makes?|keeps?|moves?)\s+(.*)$/i,
  );
  const capitalize = (value: string) => value ? `${value[0].toUpperCase()}${value.slice(1)}` : value;
  if (match) return capitalize(match[1].trim());
  return capitalize(text.replace(/^(?:the )?speaker\s+/i, '').trim());
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
