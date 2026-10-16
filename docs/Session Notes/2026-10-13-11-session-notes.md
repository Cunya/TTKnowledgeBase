# Session notes — 2026-10-13 11:00 EEST

- Start currently doubles as apply; separate cooldown application before disabling Start during an active loop.
- Persist only the cooldown in ignored per-KB local settings; never persist/restart the running state.
- Enter while stopped must save the preference without starting processing. Polling must not overwrite unsaved input.
- Production monitor runs old loaded code until an idle restart; do not terminate active processing to load a UI change.

- Verified nine Node tests, Python suite, Ruff, isolated real HTTP/restart, and zero-diagnostic Astro build. P1-25 remains in progress only for production service reload; loop is still enabled.

- Chart SVG text scales with its viewBox; larger axis labels need wider left and vertical margins. Verified real four-digit count labels inside cards in a read-only preview.

- Production service reloaded safely between cycles; loop resumed with its original two-minute cooldown. Live output fills the panel and prior controls/chart updates are now served. User’s existing browser page still requires refresh.
