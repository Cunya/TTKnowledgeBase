# Legal and platform-policy review — YouTube knowledge pages

**Review date:** 2026-07-15  
**Project:** MomentGraph / TTKnowledgeBase  
**Scope:** The public static site, its transcript-derived analysis, YouTube links and embeds, automated transcript acquisition, and the future offline-media idea.

> This is a practical risk review, not legal advice. Copyright exceptions and privacy rules vary by country. For a commercial launch, a Finnish/EU technology lawyer should review the final workflow and wording.

## Executive summary

The current site is materially different from a video mirror: it publishes concept pages, original explanations, short evidence excerpts, source attribution, timestamp links, and standard YouTube embeds. That is a more defensible educational/commentary pattern than re-hosting the videos or publishing complete transcripts, but it is not automatically protected by an “educational use” label.

The highest risks are:

1. **Automated transcript acquisition.** YouTube’s website Terms restrict automated access such as scrapers except where an exception, permission, or applicable law applies.
2. **Copied expression.** Long verbatim transcript passages, screenshots, thumbnails, or other copied creative expression can create copyright exposure even when the underlying coaching idea is not protected.
3. **Offline video storage.** A genuinely private, non-sharing copy can have a different copyright analysis from public redistribution. It still must be obtained lawfully, without bypassing technical measures, and it remains subject to YouTube’s separate platform terms. Any public or shared offline feature requires permission/licensing.
4. **Platform control.** A creator can disable embedding, make the source unavailable, request removal, or send a copyright complaint to the hosting platform.

## What the current project actually publishes

The public corpus and Astro site currently contain:

- Video IDs, titles, channel names, thumbnails, durations, canonical YouTube URLs, and timestamp links.
- Concept definitions, relationships, editorial reasons, and short transcript-derived excerpts.
- Standard YouTube player embeds on video pages.
- No public raw transcript archive and no public video files.
- A private/local normalized transcript area used by the processing pipeline.

The project therefore has two separate questions:

1. **Copyright and related-rights question:** whether the text, images, or media reproduced on the site are used lawfully.
2. **YouTube contract/platform question:** whether acquisition and display methods comply with YouTube’s Terms and developer policies.

A use can be relatively defensible under copyright law and still violate a platform contract or lose access to YouTube services.

## Findings

### 1. Ideas and methods are different from their expression

The table-tennis techniques themselves—such as a backswing sequence, racket angle, or spin concept—are generally ideas, methods, or facts. Copyright generally does not protect those underlying ideas, although it can protect the creator’s particular wording, illustrations, footage, audio, and other original expression.

Source: [U.S. Copyright Office — What Does Copyright Protect?](https://www.copyright.gov/help/faq/faq-protect.html)

**Project implication:** Re-express the coaching material in MomentGraph’s own language. Do not treat a transcript as free-to-copy text merely because the video is public.

### 2. Short quotations and source-linked analysis are safer than transcript publication, but not automatically exempt

EU copyright law recognizes quotation exceptions for purposes such as criticism or review when the work was lawfully made public, the source/author is identified where possible, the use follows fair practice, and the amount used is justified by the purpose. EU case law also recognizes that a hyperlink can be part of a quotation, but requires a close connection between the quoted material and the user’s own reflections.

Source: [EUR-Lex — quotation, criticism/review, attribution, and hyperlinks](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=ecli%3AECLI%3AEU%3AC%3A2019%3A625)

**Project implication:** Every excerpt should support a specific explanation, critique, comparison, or concept. Keep excerpts short, identify the video/channel, and avoid publishing enough transcript text to substitute for watching the source.

### 3. YouTube Terms create a separate scraping risk

YouTube’s Terms say users may view or listen to content for personal, non-commercial use and may show videos through the embeddable player. The same section restricts reproducing, downloading, distributing, modifying, or otherwise using service content except where specifically permitted, authorized in writing, or allowed by law. It also restricts automated access such as robots, bots, or scrapers except for specified cases, prior written permission, or applicable law.

Source: [YouTube Terms of Service](https://www.youtube.com/t/terms)

**Project implication:** The current `youtube-transcript-api`/automated acquisition path is the weakest platform-policy point. Copyright analysis of the final summaries does not by itself resolve whether automated transcript retrieval complied with YouTube’s access rules.

Safer options, in decreasing order of certainty, are:

1. Creator-provided or creator-authorized transcripts.
2. A written permission/license covering transcript retrieval and derived publication.
3. User-supplied transcript files where the user has the right to provide them.
4. An official YouTube data workflow for metadata and embeds, while separately confirming how transcript data may be obtained and stored.

### 4. Private offline use is a narrower, separate question

The Finnish Copyright Act’s unofficial English translation states in Section 12 that anyone may make single copies of a work that has been made public for private use, and that those copies may not be used for other purposes. Section 11 also says that a copyright limitation does not authorize copying a work that was made available unlawfully or whose technological protection measures were circumvented. The translation is expressly not legally binding; Finnish and Swedish are authoritative.

Source: [Finlex — Copyright Act 404/1961, Sections 11–12](https://www.finlex.fi/api/media/statute-foreign-language-translation/689238/mainPdf/main.pdf?timestamp=1961-07-07T22%3A00%3A00.000Z)

**Project implication:** A local-only personal database, never shared with others and never exposed through GitHub Pages, is materially less risky than a public mirror. It should still use a lawful acquisition route, avoid DRM or embed-restriction circumvention, exclude unlawfully uploaded sources, and remain separated from the public publishing pipeline. The private-copy argument does not automatically override YouTube’s Terms or make automated scraping acceptable.

### 5. Embedding is allowed only while the source and player remain eligible

YouTube supports adding videos to websites through its standard embedded player. Creators can turn off the “Allow embedding” setting, and videos may also stop playing when they become private, restricted, or removed. The player should remain a recognizable YouTube player and should not be covered by overlays that obscure its controls.

Sources: [YouTube — Embed videos and playlists](https://support.google.com/youtube/answer/171780?hl=en-EN) and [YouTube — embedded-player requirements](https://developers.google.com/youtube/terms/required-minimum-functionality)

**Project implication:** The site should treat an embed failure as an expected source state, not as something to bypass. Keep a direct “Watch on YouTube” link and mark the evidence unavailable when embedding is disabled.

### 6. YouTube API policies prohibit public/shared offline-copy behavior without permission

The YouTube API Developer Policies state that API clients must not download, import, back up, cache, or store copies of YouTube audiovisual content without prior written approval, or make that content available for offline playback. The policies also require attribution/YouTube branding and impose privacy and player-integrity requirements for API clients.

Source: [YouTube API Services — Developer Policies](https://developers.google.com/youtube/terms/developer-policies)

**Project implication:** Keep downloaded or transcoded media out of the public product and GitHub Pages artifact. A private personal mode can be considered separately, but it must not upload, sync, share, or serve the media to others and should not use an API/downloader path that violates the applicable terms.

### 7. A creator can intervene even without winning a copyright argument

A creator or rights holder can:

- Disable embedding for individual videos or a domain.
- Delete, privatize, or unlist the source video.
- Ask the project owner to remove a page, excerpt, thumbnail, or attribution.
- Submit a copyright removal request to YouTube for allegedly infringing material on YouTube.
- Submit a copyright complaint to GitHub concerning allegedly infringing repository/site content.

YouTube describes its copyright-removal process as a legal notice-and-takedown process. GitHub likewise provides a DMCA notice and counter-notice workflow for material hosted in repositories and associated services.

Sources: [YouTube copyright removal requests](https://support.google.com/youtube/answer/13823830?hl=en), [GitHub DMCA Takedown Policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy)

This does **not** mean a creator can automatically prevent every independent link or discussion of a public video. A complaint still needs a legal or policy basis, and generic ideas/methods are not the same as copied expression. It does mean the project should have a responsive removal process and should not assume that a public URL is permanent permission.

### 8. Embeds also create a privacy consideration

YouTube explains that an embedded player can share basic information with YouTube when it loads and more information when playback occurs. Its privacy-enhanced mode uses `youtube-nocookie.com` to reduce personalization from embedded views, but it does not eliminate all third-party processing.

Source: [YouTube — Embed videos and playlists / Privacy Enhanced Mode](https://support.google.com/youtube/answer/171780?hl=en-EN)

**Project implication:** Consider click-to-load players, privacy-enhanced embed URLs, a privacy notice, and a consent approach appropriate for the site’s visitors and jurisdiction. If the project later uses YouTube API Services, the API policies also require an accessible privacy policy and YouTube Terms link.

## Recommended safeguards before expanding the public corpus

### Editorial safeguards

- Rewrite explanations in original language.
- Keep transcript quotations short and directly tied to a specific analysis.
- Always show source video title, channel, author/creator where known, and canonical URL.
- Avoid reproducing full transcripts, long contiguous passages, thumbnails as decorative site art, or screenshots unless licensed or necessary for commentary.
- Label transcript-inferred material separately from visually verified demonstrations.
- Do not imply endorsement, sponsorship, or affiliation with YouTube or the creators.

### Platform safeguards

- Use the standard YouTube embed and preserve its visible source/branding controls.
- Never bypass an embed restriction or a removed/private video.
- Keep a direct YouTube link beside each embed.
- Track `available_online`, `private`, `removed`, and `embedding_disabled` states and regenerate affected pages.
- Avoid automated access patterns that are aggressive, high-volume, or designed to evade blocks.
- Do not publish downloaded or transcoded YouTube video files.

### Operator/legal safeguards

- Add a “Sources, permissions, and removal requests” page.
- Publish a contact email for creators and rights holders.
- Record the date and method of transcript acquisition internally.
- Preserve evidence of any creator permission or license.
- Define a prompt review/removal procedure for credible complaints.
- Add a privacy notice before broad public promotion.
- If using YouTube API Services, link to YouTube’s Terms and Google Privacy Policy and review the API policies before deploying credentials.

## Risk matrix for the current roadmap

| Feature | Relative risk | Recommendation |
| --- | --- | --- |
| Original concept pages with source links | Lower, if attribution is clear | Continue |
| Short transcript excerpts supporting analysis | Moderate and fact-specific | Keep concise and contextual |
| Standard YouTube embeds | Moderate/platform-dependent | Continue with direct fallback links |
| Automated transcript scraping | Significant Terms risk | Seek permission or redesign acquisition |
| Full transcript publication | High copyright risk | Do not publish by default |
| Downloading/transcoding videos | Very high without a license | Keep disabled |
| Paid access to a page whose main value is embedded YouTube content | Higher platform risk | Ensure the independent analysis is the value and review monetization terms |

## Practical conclusion

The core idea—an independent, source-grounded knowledge layer that explains concepts and links users to exact moments—is potentially workable. The defensible version is a commentary and study guide, not a transcript repository, video archive, or YouTube replacement.

The project should continue with original summaries, short attributed excerpts, standard embeds, and transparent source links. The automated transcript acquisition path should be treated as a platform-policy issue requiring further permission/alternatives research. A private personal offline mode may be evaluated as a separate, local-only capability; public or shared offline distribution should remain permission-only.

## Takedown-readiness and lawful personal continuity TODO

The project should be able to take a source offline quickly without losing its own editorial work. This is a continuity and compliance plan, not a mechanism for bypassing a valid takedown or continuing to redistribute a creator’s material publicly. A private personal copy, where lawful, must remain genuinely private and separate from the published site.

### Project-owned offline export

- [ ] Add a local-only export command for project-owned code, configuration, taxonomy, navigation, concept definitions written by the project, relationships, review decisions, provenance, and source IDs/URLs.
- [ ] Keep the export outside `app/public/` and outside GitHub Pages deployment.
- [ ] Encrypt personal backups and document who can access them.
- [ ] Record export date, corpus version, source status, and hashes for reproducibility.
- [ ] Keep raw video files, audio, thumbnails, and full transcript text out of the project-owned export unless a separate permission, license, or lawful private-use basis explicitly allows personal retention.

### Source withdrawal workflow

- [ ] Add a `withdrawn`/`quarantined` source state distinct from `removed` and `embedding_disabled`.
- [ ] Add a private removal-request record containing requester, source URL, date, claimed basis, affected assets, action taken, and follow-up date.
- [ ] Add a command that removes or masks affected public evidence, video pages, embeds, thumbnails, and transcript excerpts from the next build.
- [ ] Preserve only the minimum project-owned provenance needed to explain why an entry was withdrawn; do not keep a public mirror of disputed source material.
- [ ] Add a rebuild check that fails if quarantined source IDs still appear in `app/public/data/`.

### Personal offline media (private-only)

- [ ] Keep offline media local-only and disabled in production/public builds.
- [ ] Permit a personal copy only where the acquisition route is lawful, the source was lawfully made public, and no DRM or embed restriction is bypassed.
- [ ] Do not upload, sync, serve, or share personal offline media with other users.
- [ ] Keep personal media in an access-controlled local store; never copy it into the public static site or Git repository.
- [ ] Record source URL, acquisition date, rights basis, and whether the copy is personal-only.
- [ ] For any multi-user, redistributed, or transcoded offering, require explicit creator permission or a license and record scope, expiry, territory, transformations, and takedown contact.
- [ ] If permission expires or is withdrawn, disable access and delete or quarantine licensed media according to the license and applicable law.

### Public-site safeguards

- [ ] Add a visible source/permissions/removal page and a creator contact address.
- [ ] Provide a single operator command to disable a source and regenerate the public corpus.
- [ ] Continue linking to YouTube rather than replacing it with locally hosted copies.
- [ ] Run periodic checks for deleted/private/embed-disabled videos and show a neutral unavailable state.
- [ ] Add a deployment assertion that no raw transcript, audiovisual file, or quarantined source is present in the public artifact.

### Boundary to preserve

An offline personal database may retain the project’s own code, notes, concept model, provenance, permission records, and—where lawful—a genuinely private copy for the owner’s personal use. It must not expose that copy to others or use it to keep serving unlicensed video, audio, thumbnails, or full transcripts after a rights holder has requested removal. If a source is disputed, the public default should be withdrawal and private legal review; whether a lawful private copy must also be deleted is a separate, jurisdiction-specific question.

## Online now, private later: transition plan

The preferred operating model is to run the knowledge base publicly while source links and embeds are permitted, but keep a prepared local mode that can be activated without redesigning the corpus. The mode switch should be an operational/deployment decision, not a second copy of the knowledge model.

### Two modes

| Mode | Public exposure | Allowed source material | Deployment |
| --- | --- | --- | --- |
| `public` | GitHub Pages, source-linked pages, standard YouTube embeds | Sanitized concepts, short attributed excerpts, metadata, links, and permitted embeds | CI/Pages allowed |
| `private` | Local machine only, bound to localhost or an access-controlled private network | Project-owned analysis plus lawfully retained personal/permissioned material | GitHub Pages blocked |

### Planned controls

- [ ] Add an explicit `publication_mode: public|private` setting per knowledge base, defaulting to `public`.
- [ ] Add a source-level `public_status: published|withdrawn|quarantined` field so one creator’s request can move only the affected sources private.
- [ ] Keep stable concept IDs, relationships, provenance, and editorial notes across both modes.
- [ ] Make the public publisher exclude every withdrawn/quarantined source before writing `data/publish/` or `app/public/`.
- [ ] Make CI refuse a Pages deployment when the selected mode is `private` or when quarantined IDs appear in the public artifact.
- [ ] Add a local-only start command that binds the private site to `127.0.0.1`, never to all interfaces by default.
- [ ] Keep private transcripts/media in a separate ignored and access-controlled directory; never copy them into the public artifact or Git history.
- [ ] Add an export manifest showing mode, source status, corpus version, permissions, and hashes.
- [ ] Add a public rebuild verification step that checks routes, source links, embeds, thumbnails, transcript excerpts, and video IDs for withdrawn content.

### Transition runbook

1. **Receive and record:** log the request, source IDs, claimed basis, requester contact, and date in the private removal record.
2. **Quarantine immediately:** mark affected sources `quarantined` and stop new extraction/publication for them.
3. **Rebuild public output:** regenerate the sanitized corpus and confirm that affected concepts no longer expose the disputed source moments, embeds, thumbnails, or copied excerpts.
4. **Deploy the public change:** publish the removal commit or temporarily disable Pages if the scope is uncertain.
5. **Verify:** run the public-artifact allowlist and source-ID scan; check the deployed URL, not only the local build.
6. **Continue privately if lawful:** switch the local KB to `private` mode only for material that has a documented lawful personal-use or permission basis. Do not make that local store reachable through GitHub Pages.
7. **Review and resolve:** retain only the minimum provenance needed for the decision, and delete or quarantine licensed/private material when permission expires or a legal review requires it.

### Design principle

The public and private modes should share identifiers and editorial structure, but never share their storage boundary. Public mode is a sanitized publication. Private mode is a local personal database. A mode switch must not be implemented by simply exposing the private transcript/media directory through the existing static site.
