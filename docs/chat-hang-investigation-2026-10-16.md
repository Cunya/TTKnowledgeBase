# Chat hang investigation — 2026-10-16

Observed locally around16:29 Helsinki time. Scope: read-only app/runtime diagnosis and operational documentation. No new LLM audit calls,publication,app cache clearing,app database edits or installed-app patching.

## Evidence and timeline

- 15:46:26: the next20-article audit completed its bounded round normally.20 calls,433338 processor tokens,471.72seconds; stopped:call_limit. Eleven articles visited. Four machine-verified plans remain proposals; no additional publication occurred.
- 16:19:09,16:20:38,16:22:32: desktop pubsub connections closed,then reopened/subscribed about3.5seconds later. These were recovered interruptions,not proof of the later persistent symptom.
- 16:28:54 and16:29:04: Stop requests (`turn/interrupt`) for this exact chat were rejected with code-32600 and `thread not found`. Nearby attachment/config/model requests returned in1–4ms; the backend connection was responding.
- 16:29:11: old app transport shutdown; pending client/internal requests recorded aszero. Shutdown includes EPIPE warnings; do not mislabel those as an earlier crash.
- 16:29:25: new desktop process started after the user's restart.
- No Windows Application1000/1001/1002 event for ChatGPT/Codex/OpenAI was found in the checked precedingthree-hour interval. Absence of those events does not rule out a renderer/UI/session failure.
- Current audit ledger,repair plans and transaction JSON parse successfully. Last transaction remainsapplied; verified public audit remains103/377 supported,274 pending. Full semantic validation was not rerun for this app investigation.

## Diagnosis

The strongest evidence is stale conversation/session routing: the UI attempted to interrupt a conversation that the addressed backend said did not exist. This explains why Stop could fail despite a responsive backend. The exact initial trigger and whether a renderer stalled are unproven. The logs do not establish that audit CPU,quota,model latency or corrupted published content caused the chat symptom.

The agent also left the bounded audit in a long-lived interactive `python -i` terminal. After the planner returns at its calllimit,the interpreter staysopen at its prompt. That is an unsuitable lifecycle for an unattended bounded batch and may contribute to misleading running state. It is not proof that it caused the app's thread-not-found failure. Earlier Git review-summary logs also contain repeated hashing/diff failures; they are a separate observation,not a demonstrated cause of this hang.

## Mitigation and follow-up

Use the existing finite `python -m processors.cli plan-published-repairs` command with explicit IDs,call/article caps and a private log/checkpoint. Let the process exit and inspect its terminal checkpoint before claiming it is still running. Avoid interactive REPL/PTY background audit sessions. Resume saved work rather than restart the corpus. Keep the per-KB lock,quota guard and exact source/final-primary checks. A finite command is not a guarantee of surviving app termination; an independent OS-managed job would be separate future work if needed.

If the app symptom recurs,retain a short sanitized timeline of this chat's failed Stop request and process lifetime for an app bug report. Do not send logs externally without the user's instruction. Installed-client routing needs an app-side fix; this repository cannot establish or patch that rootcause.

Private evidence: desktop logs underLocalCache/Local/Codex/Logs/2026/10/16,oldprocess34344 t0/t1;media/audit-next20-round1-2026-10-16-15.log. Full app logs were not copied into the repository. Planning:[P1-51](prioritized-backlog-2026-07-15.md);[operations](operations.md);[session](Session%20Logs/2026-10-16-16.md). Official troubleshooting recommends separating server/component/client failures:[OpenAI documentation](https://developers.openai.com/plugins/deploy/troubleshooting).
