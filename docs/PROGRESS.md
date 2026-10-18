# ThreatDesk – Progress Tracker

## Completed Phases

### Phase 0: Scaffold
- **Status**: Completed
- **Date**: 2026-10-18

### Phase 1: Connectivity check
- **Status**: Completed
- **Date**: 2026-10-18
- **Results**: Env vars set, Gemma models (`gemma-4-26b-a4b-it`, `gemma-4-31b-it`) successfully respond with JSON, Snowflake connection successful with admin role.

### Phase 2: Data Loader and Snowflake Setup
- **Status**: Completed
- **Date**: 2026-10-18
- **Results**: CISA KEV (1,748 records) and EPSS (390,724 records) downloaded and loaded into Snowflake tables (`CVE`, `KEV`, `EPSS`). Read-only role `THREAT_ANALYST` created and granted SELECT permissions. Verified row counts and sample rows. Created `docs/DATA_SOURCES.md`.

## Decisions Log

| Decision | Reason | Date |
|----------|--------|------|
| Apache-2.0 license | Required by instructions, matches PRD option | 2026-10-18 |
| google-genai SDK | PRD specifies Gemma via Gemini API | 2026-10-18 |
| sqlglot for validation | PRD specifies, reliable SQL parsing | 2026-10-18 |
| auto_create_table=True with write_pandas | Avoids column casing / type mismatch issues during data load | 2026-10-18 |

## Open VERIFY Items

- [x] CISA KEV catalogue licence/terms (Public domain / US Govt work)
- [x] EPSS (FIRST) data licence/terms (CC BY 4.0)
- [ ] Gemma model ID and exact licence terms (check official model card)
- [ ] Snowflake trial credit amount, expiry, and available features
- [ ] Our World in Data indicator table licence for second dataset
- [ ] Whether JSON-schema structured output works for Gemma via Gemini API

## Known Issues

_None yet._
