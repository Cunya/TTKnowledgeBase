# Precedents for a YouTube knowledge-base project

**Review date:** 2026-07-15  
**Project:** MomentGraph / TTKnowledgeBase  
**Scope:** Public concept pages, transcript-derived analysis, timestamp links, YouTube embeds, and the planned private/offline mode.

> This is a research memo, not legal advice. The cases below are fact-specific, mostly from U.S. courts, and do not determine the law in Finland or every other country. A lawyer should review the final public workflow if the project is promoted, monetized, or receives a complaint.

## Bottom line

There is no reported case located in this review that decides the exact question “is a public YouTube coaching knowledge base allowed?”. The closest precedents draw a useful boundary:

- **Search, indexing, and original explanation can be defensible** when they add independent value and do not become a substitute for the source. *Authors Guild v. Google* upheld a book-search/indexing project with limited snippets.
- **Source-linked transcript search is not a blanket permission.** In *Fox News v. TVEyes*, the Second Circuit did not decide the challenged closed-caption text-search database, but rejected redistribution of clips that made too much of the source content available.
- **Embedding/linking is narrower than hosting a copy.** *Perfect 10 v. Amazon* treated inline linking on the facts before it as not a direct display by the linking site; this does not override YouTube’s own player, branding, API, or Terms requirements.
- **Full-copy public preservation is high risk.** *Hachette v. Internet Archive* rejected the defense for scanning and lending complete copyrighted books, affirmed an injunction, and the Archive did not pursue Supreme Court review.
- **YouTube’s contract/policy layer is independent of copyright.** YouTube’s Terms restrict downloading, reproducing, and automated scraping; the API policies expressly prohibit scraping and can suspend or terminate non-compliant API access.

The safest public shape for this project is therefore an independent study guide: original concept pages, short contextualized summaries, attribution, timestamps, and standard YouTube embeds/links. It should not be a transcript repository, a video mirror, or a substitute player. Keep any lawful personal copy separate and local-only.

## Precedent table

| Project or case | What happened | What it suggests here |
| --- | --- | --- |
| [Authors Guild v. Google, 2d Cir. (2015)](https://law.justia.com/cases/federal/appellate-courts/ca2/13-4829/13-4829-2015-10-16.html) | Google retained digital book copies to provide full-text search and limited snippets. The Second Circuit found the copying transformative and not a meaningful substitute for the books, and affirmed judgment for Google. | A searchable, source-grounded knowledge layer may be more defensible when the project’s own explanations are the point and the source remains the place to watch. It is not a license to publish full transcripts or books. |
| [Fox News Network v. TVEyes, 2d Cir. (2018)](https://law.justia.com/cases/federal/appellate-courts/ca2/15-3885/15-3885-2018-02-27.html) | TVEyes recorded television/radio channels and offered paid monitoring. The court rejected redistribution of downloadable/emailable ten-minute clips because it supplied too much of the desired content and harmed the licensing market. The court expressly did not decide the closed-caption text-search database because Fox did not appeal that part. | Search and indexing are materially different from giving users convenient copies of the audiovisual source. Keep moments short, contextual, and linked to YouTube; do not offer downloadable/re-hosted clips. |
| [Perfect 10 v. Amazon, 9th Cir. (2007)](https://law.justia.com/cases/federal/appellate-courts/ca9/06-55405/0655405-2011-02-26.html) | On the facts of that image case, inline linking/framing did not make Google the direct server displaying the images; the source server supplied them. | A standard YouTube iframe or direct link is preferable to copying the video. This is only an analogy: it does not remove YouTube Terms, API, copyright, trademark, privacy, or takedown duties. |
| [Hachette Book Group v. Internet Archive, 2d Cir. (2024)](https://law.justia.com/cases/federal/appellate-courts/ca2/23-1260/23-1260-2024-09-04.html) and [AP’s outcome report](https://apnews.com/article/e26a88496202b396015c555dca429b9b) | The Internet Archive scanned complete print books and made complete digital copies available through controlled digital lending. The Second Circuit affirmed the adverse fair-use ruling; a permanent injunction remained, and the Archive declined further Supreme Court review. | Nonprofit or preservation motives did not make a public full-copy service safe. A future public “download all related videos” or transcoded mirror would be much closer to this losing pattern than to Google Books. |
| [YouTube Terms of Service](https://www.youtube.com/t/terms) | The Terms permit viewing/listening for personal, non-commercial use and showing videos through the embeddable player, while restricting reproduction, downloading, distribution, alteration, and automated access such as scrapers except where permission or applicable law applies. | Copyright analysis is not enough. Acquisition and playback must also fit the platform contract; do not bypass blocks, embed restrictions, or deleted/private states. |
| [YouTube API Developer Policies](https://developers.google.com/youtube/terms/developer-policies) | The policies prohibit directly or indirectly scraping YouTube/Google applications, require attribution and player integrity, restrict copying/offline behavior, and state that API access can be suspended or terminated for non-compliance. | If the project uses API credentials, follow the API-specific storage, refresh, branding, privacy, and deletion rules. An API key is not permission to scrape transcripts or archive audiovisual files. |

## Similar-project evidence and its limits

Public tools such as downloaders, transcript sites, browser extensions, or alternative players remaining online are **not legal precedents**. Their continued availability may reflect geography, enforcement choices, user responsibility, licensing, or simply unresolved risk. GitHub hosting likewise does not certify that a repository complies with copyright or YouTube policy.

Recent lawsuits alleging large-scale YouTube scraping for AI training show that this area is actively contested, but an allegation or pending case is not a final ruling on this project. The absence of an on-point decision should be treated as uncertainty, not approval.

## Recommended boundary for MomentGraph

### Public mode

1. Publish project-authored definitions, relationships, drill notes, and comparisons.
2. Keep transcript-derived text short, rephrased, attributed, and tied to a specific explanation. Do not publish a complete transcript or long contiguous passages.
3. Link to the canonical YouTube URL and use the standard, recognizable player. Preserve YouTube attribution and a direct “Watch on YouTube” fallback.
4. Treat `removed`, `private`, `unlisted`, and `embedding_disabled` as normal source states. Quarantine affected evidence and rebuild; never bypass the restriction.
5. Keep raw transcripts, downloaded media, thumbnails, and audit artifacts out of `app/public/` and GitHub Pages.
6. Provide a creator contact/removal route and record decisions privately.

### Private mode

1. Make the site localhost-only and refuse GitHub Pages deployment when `publication_mode=private`.
2. Keep personal transcripts/media in a separate access-controlled store, with the acquisition method and rights basis recorded.
3. Do not upload, sync, serve, or share personal copies. Do not use private mode to continue a public redistribution after a valid request.
4. Do not circumvent DRM, geographic restrictions, embed settings, or other technical controls. Whether a particular personal copy is lawful is jurisdiction-specific.

## Decision guide for proposed features

| Feature | Precedent/policy signal | Default decision |
| --- | --- | --- |
| Concept summary + source link | Closest to transformative indexing/commentary | Keep public |
| Short paraphrased evidence with timestamp | Lower substitution risk, still fact-specific | Keep with editorial review |
| Full transcript search on the public site | More like a substitute for the spoken work | Do not publish by default |
| Official YouTube embed | Platform-supported presentation, subject to eligibility and policy | Keep with fallback link |
| Download/re-host/transcode all videos publicly | Closer to TVEyes redistribution and Internet Archive full-copy sharing | Require explicit permission/license |
| Personal local copy kept private | Narrower and jurisdiction-dependent; does not answer the Terms question automatically | Defer to documented lawful basis |

## Practical conclusion

The project can be designed around the more defensible precedent: original analysis that helps a reader discover and understand a source, while the source remains on YouTube. The project should explicitly decline the riskier precedent: public full-copy storage, complete transcript publication, or a replacement playback service. Add the precedent-informed controls to the backlog before expanding scraping or enabling offline media.

## Sources and review limits

- The court cases above are primary decisions or direct reports of their outcomes; they concern different works, jurisdictions, and technical facts.
- YouTube Terms and Developer Policies are current policy pages, not judicial decisions, and may change.
- This memo does not decide whether any existing transcript, thumbnail, video, or private copy is lawful. It identifies product constraints and questions for counsel.
