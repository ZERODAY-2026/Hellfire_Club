# ThreatDesk UI Design System & Architecture

## Overview
ThreatDesk has been redesigned with a modern, premium, editorial aesthetic inspired by high-end publishing platforms like [Squarespace](https://squarespace.com). The design prioritizes confident oversized typography, generous whitespace, a restrained neutral palette, soft motion, and complete transparency (traceability) of all data queries.

---

## Design System & Tokens (`app/styles.css`)

Color and typography tokens are centralized as CSS custom properties on `:root` (with automatic dark mode adaptation via `@media (prefers-color-scheme: dark)`):

```css
:root {
  --bg-primary: #FAFAF8;          /* Warm near-white editorial background */
  --bg-surface: #FFFFFF;          /* Card and container background */
  --text-primary: #111111;        /* High-contrast near-black text */
  --text-secondary: #555550;      /* Muted grey for subtitles and metadata */
  --text-muted: #888880;          /* Subtle borders and hints */
  --accent: #2563EB;              /* Electric indigo primary accent */
  --accent-hover: #1D4ED8;        /* Accent hover state */
  --border-color: #E5E5DF;        /* Hairline border contrast */
  --card-bg: #FFFFFF;             /* Surface cards background */
  --code-bg: #F1F1ED;             /* Monospace code block background */
  --code-text: #111111;           /* Code text color */
  --shadow-sm: 0 4px 20px rgba(0, 0, 0, 0.03);
  --shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.02);
  --radius-lg: 20px;
  --radius-md: 16px;
  --radius-sm: 10px;
}
```

### Changing the Accent Color in One Place
To change the primary brand accent color across the entire application, update:
1. The `--accent` CSS variable in `app/styles.css`.
2. The `primaryColor` field in `.streamlit/config.toml`.

---

## Typography
- **Display & Body Font:** `Plus Jakarta Sans` (Google Fonts), providing clean geometric sans-serif legibility with editorial character.
- **Monospace Font:** `JetBrains Mono` for executed SQL queries, Snowflake Query IDs (SFQID), and technical metrics.

---

## Layout & Evidence Panel Architecture
- **Hero Section:** Centered headline (`"Ask your vulnerability data anything."`), concise subtitle explaining traceability, and a wide rounded search input with soft shadows.
- **Sample Question Chips:** Pill buttons below the hero that instantly populate the query input.
- **Always-Visible Evidence Panel:** Directly below every query result, containing:
  - **Proof Badges:** Runtime in seconds, total row count, Snowflake Query ID (SFQID), and database/schema path.
  - **Intelligence Report:** Grounded natural language summary synthesized by Gemma.
  - **Execution Results Table:** Clean table displaying up to 50 rows plus total count and CSV download option.
  - **Executed SQL Query:** Dark/styled rounded code block with monospaced font.
  - **Planner Reasoning & Safety Verification:** Detailed planner rationale and deterministic safety check status.

---

## Explicit States Handled
1. **Loading:** Live stage-by-stage status progression ("Planning the query with Gemma...", "Checking it is safe (Validator)...", "Running it in Snowflake...", "Writing the explanation...").
2. **Empty Result:** Illustrated inline SVG empty state card with `"No rows matched"` and suggestions to relax filters.
3. **Unsafe / Unsupported Request:** Calm alert card explaining why safety checks failed with suggested supported queries.
4. **Conversation History:** Compact horizontal scroll bar showing prior turn queries above the input.
5. **Errors:** Friendly error messages explaining what happened and how to retry, preventing stack trace exposure.

---

## Performance & Caching Architecture (`app/perf.py`, `app/runtime.py`)
- **Resource Caching:** `cached_load_config` caches dataset configuration loading using Streamlit's `st.cache_resource`.
- **Warehouse Warm-Up:** `warm_up_warehouse()` runs a lightweight `SELECT 1` query on session start to wake up the Snowflake warehouse without consuming extra credits.
- **Pipeline Cache:** In-memory `PipelineCache` caches full query execution bundles keyed by normalized query string, active config file, and computed data version hash (`get_data_version`).
- **Stage Timing Instrumentation:** Every stage (planner, validator, executor, explainer) is timed (`time.time()`) and logged asynchronously to `logs/timing.log` for observability.
- **Session State Persistence:** Results are stored in `st.session_state.last_result` so that UI interactions (downloading CSV, toggling SQL expander, filtering dataframes) do not trigger expensive pipeline re-execution.
- **Cache Hit Labeling:** Cached query results display an explicit `"⚡ Cached from earlier run"` badge in the proof bar.

---

## Screenshots Note
Because this environment runs headlessly without a browser window or desktop screenshot server running Streamlit, automated browser screenshots could not be generated. Verification was performed via pytest test suites and code inspection of `app/ui.py`, `app/styles.css`, and `.streamlit/config.toml`.
