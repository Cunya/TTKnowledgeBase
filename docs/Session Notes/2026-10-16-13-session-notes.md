
## 2026-10-16 13:10 — Read-only throughput diagnosis

- Investigated actual saved logs andread-onlycProfile; no modelcalls/canonicalchanges. Tenreleasegates:28.7min Pythontests alone;sixcoveragebatches120calls/2.90Mtokens/50.3min/113visits. Two difficulty-only batches16calls/306505tokens/sixappliedarticles. Fullaudit rebuild7.855s underprofiler,archive load/render9.68s,allrepeated perarticle. Profiledoesnotfullyattribute multi-minuteapplicationlatency.
- Previous55–60h estimate mixesupfrontcoverage/repairs andisnotreliableforecast. Proposed P1-51 priorities:typedreviewedoptional-nullremoval,20–30articlebatchedrelease,incrementaldependency/applicationreuse,advisoryoverlapfingerprintseparation,representative20articlebenchmark. Source/footage/archive/freshness controlsremainmandatory. Report docs/audit-throughput-diagnosis-2026-10-16.md;planning/surfacesupdatedbeforestudycomplete.
