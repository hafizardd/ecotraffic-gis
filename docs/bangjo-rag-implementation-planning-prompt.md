# Planning Prompt — Bang Jo RAG Chatbot Upgrade (EcoTraffic GIS)

## 1. Ground truth: what exists today

**Stack:** FastAPI + SQLAlchemy(async) + PostGIS backend; Next.js/React (TypeScript) frontend; Celery/Redis for background jobs; YOLOv8 CV pipeline for vehicle detection; H3-based `ActivityGridHex` grid; AHP scoring for corridor/bus-stop priority.

**Chatbot ("Bang Jo") — backend**, `backend/app/api/routes/bangjo.py` + `backend/app/services/bangjo_context.py`:

- `POST /api/chat/bangjo` accepts `{ message, road_segment_id?, history[] }`.
- If no `road_segment_id` is supplied, `_resolve_segment()` tries to match the road name inside the free-text `message` using **string normalization + substring/token overlap** (`_normalize_name`, token intersection scoring) against `RoadSegment.name` rows pulled from the DB. There is **no semantic/embedding matching** — it's exact/fuzzy string matching only. Ambiguous or unmatched input returns `needs_selection: true` with candidate names.
- `build_context()` assembles a **deterministic, hand-built JSON context** per segment: primary road segment + emissions (`SegmentEmission`), intersecting `ActivityGridHex` cells (POI mix, AHP score, classification), nearby `SurveyStopObservation` bus stops within `K4_BUFFER_M`, a coverage-gap flag (high-potential hex with no stop nearby), an `intervention_hint` (`add_new_stop` / `improve_existing_stop` / `increase_frequency`, chosen by a fixed priority order), and a 24h REPLAY `hourly_series` (with an `is_interpolated` flag per hour). `_merge_contexts()` combines this across same-named road chunks into one corridor object.
- `_ask_llm()` sends the **entire context object as raw JSON** inline in the user turn (not retrieved — it's the _only_ context, always the full object for that segment) to an OpenRouter model (`settings.BANGJO_MODEL`, default `nvidia/nemotron-3.5-lightning:free`) via `httpx`. It tries structured JSON mode first, falls back to plain mode if the endpoint rejects `response_format`, and does one corrective re-ask if the reply doesn't parse. On timeout/HTTP error/parse failure/missing API key, it **never 500s** — it degrades to `_fallback_answer()`, a deterministic template built from the same context dict.
- Output parsing (`_parse_answer`) is a three-stage cascade: strict `json.loads` → regex-repaired JSON (smart quotes, comments, trailing commas) → tolerant per-field regex extraction (`_string_field` / `_list_field`). Final shape is always `{summary, drivers[], asi_category, recommendation, evidence[], source}`.
- **There is no retrieval step, no embeddings, no vector store, and no guardrails library anywhere in the codebase or `requirements.txt`.** "RAG" in the code comments means "grounded in a hand-assembled structured context object," not vector retrieval over a document corpus. There is nothing in `requirements.txt` for embeddings (no `sentence-transformers`, `pgvector`, `faiss`, `chromadb`, etc.) and nothing for guardrails (no `nemoguardrails`, `guardrails-ai`, etc.).
- No caching layer for repeated questions/contexts, no streaming response, no request-level auth/rate limit on `/api/chat/bangjo`.

**Chatbot — frontend:**

- `hooks/useBangJoChat.ts` calls `fetchBangJoReply()` (`services/api.ts`) with the last 6 turns of local history and the segment id from `utils/selectionStore.ts` (a plain module-level singleton updated when the user clicks a segment on the map — see `MapView.tsx`).
- `components/Chatbot/{BangJoWidget,BangJoFab,BangJoPanel,BangJoComposer,BangJoMessage,BangJoQuickQuestions}.tsx` render a floating action button + slide-in panel. `BangJoWidget` is mounted once, at the `DashboardShell` level (`components/Dashboard/DashboardShell.tsx`), as a sibling of the sidebar/main content — **outside** the map's own layout flow.
- The chatbot **only ever answers when the user types or taps a quick-question chip.** Clicking a road segment/hex/bus stop on the map only opens the relevant side panel (`SegmentPanel`, `SidePanel`, etc.); it does not call Bang Jo automatically. There is currently no "auto-insight-on-click" behavior anywhere in the frontend.

**Confirmed UI overlap bug** (`frontend/src/app/globals.css`):

- The data panel that opens on selection (`.monitoring-panel`, ~line 828) is a **normal flex child** of `.map-panel-layout`, flush against the right edge of the workspace (`flex: 0 0 min(430px, 35vw)`).
- The chatbot FAB and panel are **`position: fixed`** to the viewport (`.bangjo-fab`: `right: 22px; bottom: 22px; z-index: 40`; `.bangjo-panel`: `top: 84px; right: 22px; bottom: 22px; z-index: 41`, up to 384px wide).
- Because both sit at the same right-edge coordinate space with the fixed elements at a higher stacking context, opening Bang Jo while a segment/hex/camera/bus-stop panel is open **visually covers the top-right and bottom-right of that data panel**, and the FAB itself sits on top of panel content when Bang Jo is closed but the data panel extends under `bottom: 22px / right: 22px`. This matches the reported symptom exactly.

---

## 2. Anomalies / issues to fix regardless of the RAG work

List these explicitly in the plan as "bug fixes," separate from new features:

1. **UI overlap (root cause above).** The data panel and Bang Jo panel/FAB occupy the same screen real estate because one is in-flow and the other is `position: fixed` with no mutual awareness. Fix needs layout coordination (e.g., Bang Jo panel should dock to the _left_ of an open data panel, shrink/reflow the workspace, or the data panel and Bang Jo panel should share a z-index-aware layout manager rather than both claiming `right: 22px`).
2. **Segment resolution is brittle.** `_resolve_segment` only does substring/token matching on road names typed in free text; misspellings, synonyms ("Jl." vs "Jalan"), or references like "koridor tersibuk" will fail and fall through to `needs_selection`. This is the natural place embeddings/semantic matching should slot in — but scope it as _segment/entity resolution_, not full-corpus RAG, since there's no document corpus yet.
3. **Latency risk from serial LLM calls.** Worst case today is up to 2 HTTP calls to the model (structured attempt, then unstructured fallback) plus a corrective re-ask on parse failure — 3 sequential calls, each up to `BANGJO_TIMEOUT_SECONDS` (30s default). Flag this and require a plan for reducing round-trips (e.g., skip the structured-mode probe once you know the model doesn't support it, cache that capability, or default straight to prompt-only JSON with the existing regex fallback).
4. **No caching.** Identical questions about a static segment (or the same auto-generated insight) recompute context and re-call the LLM every time.
5. **No streaming.** The user waits for the full model response before seeing anything; combine with (3) this can feel slow.
6. **No guardrail/scope layer.** Nothing currently stops a user from sending off-topic or adversarial input (jailbreak attempts, prompt injection via `history` role/content fields, requests unrelated to traffic/emissions). The system prompt asks the model to stay grounded, but that's a suggestion to the model, not an enforced gate — and it only constrains the _answer_, not whether the query is processed at all.
7. **No auth/rate limiting** on `/api/chat/bangjo` — confirm whether this is intentional (internal dashboard) or needs addressing alongside the guardrail work.
8. **`BANGJO_MODEL` defaults to a free-tier model** (`nvidia/nemotron-3.5-lightning:free`) — note this as a latency/quality/availability risk worth a decision, not a silent assumption.

---

## 3. What to plan (in the order the stakeholder cares about)

For each item below, the plan must say: what changes, in which files, what new dependencies (if any) and why, and how it's tested — before any code is written.

### 3.1 Embeddings + knowledge retrieval (the actual "RAG" gap)

Today there is no corpus to retrieve from — context is 100% structured SQL results. Decide and document, explicitly, what retrieval should mean here, because "RAG" only earns its name if there's something to retrieve:

- **Entity/segment resolution retrieval**: replace/augment `_resolve_segment`'s string matching with embedding similarity over road segment names (+ aliases/synonyms) so paraphrased or misspelled references still resolve. This is retrieval over a small, structured corpus (segment names/metadata), not free text.
- **Unstructured knowledge retrieval (if in scope)**: if there is (or will be) unstructured material the chatbot should draw on — survey notes/descriptions (`SurveyStopObservation` free-text fields), the PRD/methodology docs, ASI framework explanations, glossary of metrics — plan a proper embedding index over that content (chunking strategy, embedding model choice, where vectors live: `pgvector` on the existing PostGIS/Postgres instance is the natural fit given the current stack, vs. a separate vector DB). State this as a distinct pipeline from the existing `build_context()` structured assembly, and specify how the two are merged before being sent to the LLM (structured facts stay authoritative/numeric; retrieved text supplies explanatory/definitional grounding, not numbers).
- Specify the retrieval flow end-to-end: query → embed → similarity search (top-k, threshold) → re-rank/filter (e.g., only chunks touching the resolved segment/corridor) → assembly alongside the existing structured context → prompt construction. Include a fallback path (skip retrieval, use structured-only context) so this never becomes a new single point of failure, consistent with the existing "never 500" philosophy in `bangjo.py`.
- Specify what "low latency" trade-off is acceptable here (e.g., embedding search budget in ms, caching embeddings for static content, precomputing segment-name embeddings at ingest/migration time rather than per-request).

### 3.2 Guardrails (scope + jailbreak handling)

- Decide: adopt NeMo Guardrails as a library, or implement an equivalent lightweight gate (classifier/prompt-based intent check + rule-based filters) given it's not currently a dependency and adds a Python service dependency. Document the trade-off (NeMo Guardrails brings weight/ops overhead + config format (Colang) vs. a simpler home-grown check that's easier to keep low-latency).
- Define what "in scope" means concretely for this app (traffic, emissions, corridors, bus stops, ASI/intervention questions, dashboard data) vs. out-of-scope (general chit-chat, unrelated advice, attempts to extract the system prompt, instruction-override attempts).
- Define the gate's position in the pipeline: it must run **before** `build_context()`/retrieval is invoked, so out-of-scope or adversarial queries never reach the LLM call or the DB context assembly (saves latency and avoids leaking context in a jailbreak).
- Define the rejected-query UX: what message the user sees, and that it's a normal (200) response, not an error, mirroring the existing `needs_selection` pattern in `BangJoReply`.
- Cover injection vectors already present in the code: the client-supplied `history` array (`role`/`content`) is trusted as-is and concatenated into the model conversation — the plan must address sanitizing/validating this, not just the live `message`.

### 3.3 Output parsing & formatting

- The existing three-stage parser (`_parse_answer` → `_normalize_answer`/`_regex_answer`) is solid; the plan should say whether it's kept as the final safety net (recommended) while retrieval/guardrails are added upstream, or whether the output schema needs to grow (e.g., a `citations`/`sources` field once retrieval is added, so the UI can show _what_ was retrieved, not just the structured evidence array that exists today).
- Specify how retrieved-text citations (if 3.1 is implemented) should be surfaced in the `BangJoAnswer` type (`frontend/src/types.ts`) and rendered in `BangJoMessage.tsx` without breaking the current `{summary, drivers, asi_category, recommendation, evidence}` contract that `useBangJoChat.ts`'s `formatAnswer()` depends on.
- Confirm formatting requirements for readability in `BangJoMessage.tsx` (currently plain-text `<div>` — no markdown/line-break rendering beyond the `\n\n` joins done client-side in `formatAnswer`). Decide whether to keep plain text or move to lightweight markdown rendering, and note this is a frontend change, not a backend one.

### 3.4 Latency

- Consolidate into concrete targets (e.g., "p50 response under Xs including retrieval + guardrail check") and map each existing latency source (guardrail check, retrieval, structured-mode probe + fallback, corrective re-ask, model choice) to a mitigation, per item 2.3/2.5 in Section 2.
- Address streaming: decide whether `/api/chat/bangjo` should stream tokens (SSE or chunked) to the frontend so the panel shows progressive output, and what that means for the current "parse whole JSON response" approach (streaming + strict JSON parsing are in tension — the plan must resolve this, e.g., stream the narrative fields but keep structured fields validated post-stream).

### 3.5 Automatic recommendation on visualization click

- New behavior: when the user clicks a road segment, hex cell, or bus stop on the map (i.e., whenever `MapView.tsx`'s `selectedSegmentId` / `selectedHexId` / `selectedStopId` changes and a panel opens), Bang Jo should proactively generate a recommendation **without the user typing a query**.
- This recommendation must be derived from the _full_ relevant dataset already assembled by `build_context()` plus whatever `activity_potential` (POI + population proxy via hex data), `bus_stops`, and emissions data apply — i.e., impact (emissions) + causes (vehicle volume, POI activity, population) + intervention points (bus stops: upgrade facilities / increase frequency / add new stops), matching the existing `intervention_hint` logic in `bangjo_context.py`, not a new invented data source.
- Specify the trigger mechanism precisely: does the frontend call a new endpoint (e.g., `POST /api/chat/bangjo/auto-insight` or reuse `/api/chat/bangjo` with a synthetic system-generated message) on panel open? Should it run through the _same_ guardrail from 3.2 (it should be exempt, since it's system-triggered, not user text, but must still hit the same context/retrieval/formatting pipeline)?
- Specify caching/debounce: rapid clicking across segments/hexes must not spam the LLM — define debounce and per-entity caching (e.g., cache the auto-insight per `road_segment_id`/`hex_id` for N minutes, matching that the underlying `SegmentEmission`/AHP data doesn't change every second).
- Specify where this appears in the UI: inline in the relevant panel (`SegmentPanel.tsx` / `SidePanel.tsx` / a new bus-stop detail view) versus pushed into the Bang Jo chat thread versus both — and how it interacts with 3.6 below (it must not be the thing that triggers the overlap bug).

### 3.6 Chatbot UI/UX — stop obscuring the visualization panel

- Fix the root cause identified in Section 1/2.1: `.bangjo-fab` / `.bangjo-panel` (`position: fixed`, `right: 22px`) versus `.monitoring-panel` (in-flow flex child, same right edge). Plan one of:
  - Make Bang Jo's open panel part of the same flex layout as the data panel (e.g., a resizable multi-pane workspace) so opening one visually pushes rather than covers the other, or
  - Reposition Bang Jo (e.g., dock left when a data panel is open, or reduce to a smaller docked drawer) with a z-index/layout rule keyed off `isAnyPanelOpen` (already computed in `MapView.tsx`) — this state needs to be lifted or communicated to `BangJoWidget`, which currently has zero awareness of panel state since it's mounted at the `DashboardShell` level, not inside `MapView`.
  - On small viewports, `.map-panel-layout.has-panel .map-area { display: none }` already exists for the map-vs-data-panel conflict — the plan should say whether Bang Jo needs an equivalent responsive rule, or whether it should auto-minimize when a data panel opens on narrow screens.
- The FAB itself blocking panel content when minimized/closed must also be resolved, not just the open panel.

---

## 4. Adjusted "Alur AI" — map the PRD workflow to current reality

Translate the original PRD stages against actual implementation status, and mark what this work stream changes:

| PRD Stage                    | Current status in this repo                                                                                                                                                                                                                 | What this implementation plan changes                                                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dataset & Data Survey        | Implemented — PostGIS-backed spatial models (`RoadSegment`, `ActivityGridHex`, `SurveyStopObservation`, etc.)                                                                                                                               | No change                                                                                                                                                                                   |
| Data CCTV                    | Implemented — CCTV ingestion referenced under `backend/cv`                                                                                                                                                                                  | No change                                                                                                                                                                                   |
| Deteksi Kendaraan (YOLO)     | Implemented — YOLOv8 pipeline under `backend/yolo` / `backend/cv`                                                                                                                                                                           | No change                                                                                                                                                                                   |
| Pengolahan Data              | Implemented — `SegmentEmission`, `pollutant_totals_g_h`, `volume_per_hour`, REPLAY interpolation flags                                                                                                                                      | No change                                                                                                                                                                                   |
| Analisis Spasial (incl. AHP) | Implemented — `ActivityGridHex.skor_total_ahp`, `klasifikasi_potensi`, stop `ahp_total_score`/`intervention_class`                                                                                                                          | No change                                                                                                                                                                                   |
| **AI Model (LLM)**           | Partially implemented: LLM call exists (`_ask_llm`), grounded in a **structured, hand-built context object**, not retrieval over embeddings; **no guardrails**; single reactive query/response, not proactive; latency not optimized        | **This is the work**: add embeddings-backed retrieval (3.1), scope/jailbreak guardrails (3.2), formatting guarantees (3.3), latency work (3.4), and proactive auto-insight generation (3.5) |
| **Insight & Rekomendasi**    | Partially implemented: answer schema (`summary/drivers/asi_category/recommendation/evidence`) exists and renders in chat; **not surfaced automatically in the map/panel UI on click**, and currently visually conflicts with the data panel | **This is the work**: wire auto-insight into panel selection (3.5) and fix the panel overlap (3.6) so insight and visualization coexist                                                     |

State this table (or your own corrected version of it) back to the stakeholder as the "current vs. target" framing before implementation starts, since the original PRD text describes the target end-state, not the current code.

---

## 5. What the plan must hand back

Require the planning pass to produce, before any implementation:

1. A decision record for every "decide" bullet above (embeddings model + where vectors live; NeMo Guardrails vs. custom gate; streaming vs. not; auto-insight trigger endpoint/mechanism; panel layout fix approach) with a one-line rationale each.
2. A file-by-file change list (backend: `bangjo.py`, `bangjo_context.py`, new retrieval/guardrail modules, `config.py`, `requirements.txt`; frontend: `BangJoWidget.tsx`, `useBangJoChat.ts`, `MapView.tsx`, `SegmentPanel.tsx`/`SidePanel.tsx`, `globals.css`, `types.ts`, `services/api.ts`).
3. New/changed API contracts (request/response shapes), especially for the auto-insight trigger and any new citations field.
4. A test plan that extends `backend/tests/test_bangjo.py` (guardrail rejection cases, retrieval fallback, auto-insight endpoint) and adds frontend coverage for the panel-overlap fix and auto-trigger behavior.
5. An explicit latency budget per stage (guardrail check, retrieval, LLM call, parse) and how it will be measured (logging already exists via `logger.info("bangjo_llm_call", ...)` in `bangjo.py` — extend it, don't replace it).
6. Rollout/fallback plan consistent with the existing design principle in the code's own docstring: _"Any LLM failure degrades to a deterministic summary built from the same context (never a 500)"_ — every new component (guardrail, retrieval) must degrade the same way, never becoming a new hard failure point.
