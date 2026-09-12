# Bang Jo RAG Upgrade — Implementation Plan (EcoTraffic GIS)

Planning artifact for `docs/bangjo-rag-implementation-planning-prompt.md`. **No code changes
are made by this document**; it is the decision record + change list + contracts + test plan
required before implementation. Grounded against the current tree at branch `feat/improve-rag`.

Key facts verified in-repo:

- Postgres is `postgis/postgis:15-3.3` (`docker-compose.yml:3`) — **pgvector is not installed**.
- Migrations live in `backend/migrations/versions/` (Alembic; `CREATE EXTENSION` via `op.execute`).
- Bang Jo backend: `backend/app/api/routes/bangjo.py`, context builder
  `backend/app/services/bangjo_context.py`, tests `backend/tests/test_bangjo.py`.
- Frontend tests run with **no DOM/React harness**: `node --experimental-strip-types --test tests/*.test.mjs`
  (`frontend/package.json:11`).
- Bang Jo UI is mounted once at shell level (`DashboardShell.tsx:31`), the data panels are
  rendered inside `MapView.tsx:505-511`; `selectionStore` currently carries **only** the
  segment id (`frontend/src/utils/selectionStore.ts`).
- OpenRouter **does** expose an embeddings API (`POST /api/v1/embeddings`), so embeddings can
  reuse the already-configured provider/key/`httpx` client — **no new Python dependency**.

---

## 0. Current vs. target (corrected PRD framing)

| PRD Stage | Current status | This plan changes |
| --- | --- | --- |
| Dataset & Data Survey | Implemented (PostGIS models) | No change |
| Data CCTV | Implemented (`backend/cv`) | No change |
| Deteksi Kendaraan (YOLO) | Implemented | No change |
| Pengolahan Data | Implemented (`SegmentEmission`, REPLAY interpolation) | No change |
| Analisis Spasial (AHP) | Implemented (`ActivityGridHex`, stop `ahp_total_score`) | No change |
| **AI Model (LLM)** | LLM call grounded in a hand-built structured context; **no retrieval, no guardrails, reactive only** | Entity-resolution embeddings (§3), custom guardrail gate (§4), capability-cached round-trips (§6) |
| **Insight & Rekomendasi** | Answer schema renders in chat; **not surfaced on map click**; visually collides with data panel | Auto-insight on selection (§7) + panel dock fix (§8) |
| Retrieval over unstructured docs | **Does not exist** (no corpus) | Deferred; seam reserved (§3.3) |

---

## 1. Scope and non-goals

**In scope (phase 1–2):** entity/segment resolution retrieval, custom guardrail gate,
capability-cached latency reduction, auto-insight on map selection, panel-overlap fix,
optional citations field.

**Non-goals (deferred, with a reserved seam):** unstructured-document RAG (no corpus exists),
token streaming, auth/rate limiting, a markdown renderer, pgvector.

---

## 2. Bug fixes (independent of RAG work)

1. **UI overlap** — `.bangjo-fab`/`.bangjo-panel` are `position: fixed; right: 22px`
   (`globals.css:2267-2327`) while `.monitoring-panel` is an in-flow flex child flush right
   (`globals.css:828`). Fix in §8.
2. **Brittle segment resolution** — `_resolve_segment` (`bangjo.py:130`) is substring/token only.
   Fix in §3.
3. **Serial LLM round-trips** — structured probe + fallback + corrective re-ask = up to 3 serial
   calls (`bangjo.py:286-296`). Fix in §6.
4. **No caching** — identical questions/auto-insights recompute. Fix in §6/§7.
5. **No streaming** — accepted for now; mitigated by §6/§7. Decision in §9.
6. **No guardrail/scope layer** — including unsanitized client `history` (`bangjo.py:245`). Fix in §4.
7. **No auth/rate limiting** on `/api/chat/bangjo` — **stakeholder decision required** (§10).
8. **Free-tier default model** `nvidia/nemotron-3.5-lightning:free` (`config.py:73`) — **stakeholder decision required** (§10).

---

## 3. Retrieval design

### 3.1 What "retrieval" means here (decision)

Retrieval is **entity/segment resolution only** in phase 1: a small, structured corpus of
segment names + curated aliases. It is not free-text corpus RAG. Rationale: there is no document
corpus in the repo yet; a chunk/embed/index pipeline for content that does not exist is speculative
(YAGNI). The `retrieve()` seam is written so a document index can be added later without touching
the route.

### 3.2 Resolution layers

Resolution becomes a cascade; each layer falls through to the next and the existing string matcher
remains the final fallback:

- **Layer A — normalization/aliases (deterministic, no deps).** Extend `_normalize_name`
  (`bangjo.py:118`): `Jl./Jln./Jl → jalan`, `Gg → gang`, `Kor. → koridor`, whitespace/punctuation
  folding, plus a small curated alias map (e.g. colloquial corridor names → canonical names).
- **Layer B — embedding similarity.** Embed the query once via OpenRouter; compare cosine against
  precomputed segment-name+alias vectors; accept top-1 above threshold `T` (start `T≈0.82`), else
  fall through. Catches misspellings/paraphrases ("jalan malioboro" ↔ "Jl. Malioboro").
- **Layer C — intent routing (deterministic).** Superlative/ranking phrasings that are *not* names
  ("koridor tersibuk", "emisi tertinggi") must not be sent to name matching. Match a small keyword
  set and route to a deterministic top-corridors-by-emission query (reuse the existing analytics
  corridor query). This is explicitly **not** an embedding problem.

### 3.3 Unstructured-document RAG (deferred, seam reserved)

When a corpus exists (survey notes, PRD/methodology, ASI glossary), add a distinct pipeline:
chunk → embed → store → top-k (threshold + re-rank to resolved segment/corridor) → merge into the
prompt. Contract now: `app/services/bangjo_retrieval.py::retrieve(db, query, entity) -> list[Chunk]`,
returning `[]` while disabled. **Merge rule:** structured facts from `build_context()` stay
authoritative for every number; retrieved text supplies definitions/explanations only and is passed
in a separate `retrieved_knowledge` block the system prompt forbids citing for numeric claims.

### 3.4 Embedding provider and vector store (decision)

- **Provider:** OpenRouter `POST /api/v1/embeddings` with `openai/text-embedding-3-small`, reusing
  `OPENROUTER_API_KEY` + `httpx`. Zero new Python dependency. Only the **query** is embedded per
  request; document vectors are precomputed.
- **Store:** new table `road_segment_name_embeddings` (JSONB float array + `model` + `dim` +
  `content_hash` + `updated_at`). At request time load all rows (a few hundred) into an in-process
  cache and cosine in Python. **No pgvector**: avoids building a custom postgis+pgvector image for
  a corpus this small. Upgrade path: pgvector when the corpus exceeds ~10k vectors (documented, not built).
- **Backfill:** idempotent script re-embeds only rows whose `content_hash` changed. New Alembic
  migration under `backend/migrations/versions/`.

**Fallbacks:** embeddings disabled (`BANGJO_EMBEDDINGS_ENABLED=false`), no API key, HTTP error, or
threshold miss → Layer A/C and the existing string matcher. Embedding failure never 500s.

---

## 4. Guardrails (decision: custom gate, not NeMo)

**Decision:** a home-grown, deterministic gate. Rationale: NeMo Guardrails pulls a heavy
LangChain/Colang stack and its own LLM calls (extra latency + ops) for a single-domain internal
dashboard; a deterministic gate is lower-latency, dependency-free, and unit-testable.

**Gate position:** runs **before** `_resolve_segment` and `build_context` (route entry,
`bangjo.py:427`), so out-of-scope/adversarial input never reaches the DB or the LLM. Auto-insight
is system-triggered and **exempt** from the scope gate but still runs sanitization + context/parse.

**Two parts:**

1. **Scope gate** on the live `message`: length cap; topic allowlist (traffic, emisi/emissions,
   koridor/segmen, halte/bus stop, ASI, intervensi, dashboard metrics); injection blocklist
   ("ignore previous/above instructions", "system prompt", "kamu adalah", role spoofing,
   base64/encoded payloads). Ambiguous messages pass (fail-open) — this is a heuristic scope
   filter, not an auth boundary.
2. **History sanitizer** (`bangjo.py:245` currently trusts `role`/`content`): keep only
   `role ∈ {user, assistant}`, cap turn count and per-message length, strip control chars and
   injection patterns, drop empty turns.

**Rejected-query UX:** HTTP **200** with `{blocked: true, message: "<friendly Indonesian text>"}`,
mirroring the existing `needs_selection` pattern. Never an error. Frontend `formatAnswer`
(`useBangJoChat.ts:10`) renders `message`.

**Fail-open policy:** if the gate itself raises, log and allow the request (deterministic
sanitization still applies) so the guardrail never becomes a new hard failure point.

---

## 5. Output parsing & formatting

- **Keep** the three-stage parser (`_parse_answer` → `_normalize_answer`/`_regex_answer`,
  `bangjo.py:225`) as the final safety net, unchanged.
- **Add optional `citations: [{label, source?}]`** to `BangJoAnswer` (`types.ts:460`). It is
  optional, so the existing `formatAnswer` contract is not broken; fallback answers emit `[]`.
  Retrieval citations are rendered as a small footnote list in `BangJoMessage.tsx` when present.
- **Formatting:** keep plain text. `.bangjo-msg` already uses `white-space: pre-wrap`
  (`globals.css:2396`) and `formatAnswer` joins with `\n\n`; a markdown renderer is an unnecessary
  dependency. This is a frontend-only concern.

---

## 6. Latency

- **Structured-capability cache:** on the first `400/404/422` from the structured probe
  (`bangjo.py:255`), set a process-level flag so later calls skip the structured attempt. Removes
  1 of up to 3 serial calls. Warm once per worker (no Redis required).
- **Redis caching** (existing dependency): auto-insight cached per entity with TTL; optional chat
  cache keyed by `hash(normalized_message, segment_ids, history_tail)`.
- **Embedding cache:** document vectors in memory; query embedded once per request.
- **Targets & measurement:** §9. Extend `logger.info("bangjo_llm_call", ...)` (`bangjo.py:297`)
  with per-stage timings; do not replace it.
- **Streaming:** **not in phase 1.** Streaming tokens conflicts with strict whole-JSON parsing and
  adds SSE plumbing; caching + fewer round-trips + auto-insight-on-click address perceived latency
  first. Revisit only if p50 exceeds target.

---

## 7. Automatic recommendation on visualization click

- **Endpoint:** new `POST /api/chat/bangjo/auto-insight` (§11). Explicit and typed; avoids
  polluting the chat thread with synthetic user messages.
- **Entity → context mapping:** segment uses `build_context` directly; hex → intersecting
  segment(s) (reverse of the intersection query at `bangjo_context.py:62`); stop → nearest segment
  within `K4_BUFFER_M`. All then reuse `build_context` + `_merge_contexts` + `_ask_llm` +
  `_parse_answer`. No new data source; uses existing emissions / AHP / POI / bus-stop /
  `intervention_hint` logic (`bangjo_context.py:119-126`).
- **Trigger & debounce:** frontend fires on selection change, debounced ~400 ms, with an in-memory
  per-entity cache; server also caches per entity (TTL ~5 min, matching data cadence).
- **Placement:** **inline card in the open panel** (`SegmentPanel.tsx` / hex panel / bus-stop
  panel) plus a "Tanya Bang Jo" button that promotes the entity into the chat thread. Not pushed
  into the thread automatically (avoids spam and the overlap bug).
- **State:** `selectionStore` is generalized to publish `{segmentId, hexId, stopId, cameraId,
  isPanelOpen}` from a single `useEffect` in `MapView.tsx`; `BangJoWidget` subscribes. This also
  feeds the dock fix (§8).

---

## 8. Panel-overlap fix (root cause)

**Decision:** dock Bang Jo to the **left** of an open data panel; least invasive given
`BangJoWidget` is mounted at shell level (`DashboardShell.tsx:31`).

- Publish panel state via `selectionStore` (§7); `BangJoWidget` toggles
  `data-data-panel="open"` on the document root.
- CSS: introduce `--data-panel-width` (default `min(430px, 35vw)`, overridden at the existing
  breakpoints `globals.css:1823`). `.bangjo-panel` and `.bangjo-fab` use
  `right: calc(var(--data-panel-width) + 34px)` when a panel is open, instead of `22px`.
- **Narrow viewports:** at `max-width: 760px` `.bangjo-panel` is already a full-screen overlay
  (`globals.css:2489`) and `.map-panel-layout.has-panel .map-area` is hidden
  (`globals.css:1887`); hide the FAB while a data panel is open there.
- The FAB blocking minimized panel content is fixed by the same offset rule.
- **Testable extraction:** `frontend/src/utils/bangjoLayout.ts` exports
  `bangjoDock({isPanelOpen, viewportWidth, panelWidth}) -> {offsetRight, docked, hideFab}` — pure,
  covered by the existing Node test harness. No DOM/React testing dependency added.

---

## 9. Latency budget

| Stage | p50 target | p95 target | Mitigation |
| --- | --- | --- | --- |
| Guardrail + history sanitize | < 5 ms | < 10 ms | pure Python, no I/O |
| Entity resolution | < 200 ms | < 600 ms | query embed (1 network call); doc vectors in memory; string fallback |
| `build_context` (+ merge) | < 150 ms | < 400 ms | existing queries; index review |
| LLM call | < 6 s | < 15 s | structured-capability cache; shorter prompt; model choice |
| Parse | < 5 ms | < 10 ms | existing three-stage parser |
| **End-to-end** | **< 7 s** | **< 16 s** | caching + auto-insight precomputed on click |

Hard ceiling stays `BANGJO_TIMEOUT_SECONDS` (30 s). Extend `bangjo_llm_call` with
`guardrail_ms`, `resolve_ms`, `retrieval_ms`, `context_ms`, `llm_ms`, `parse_ms`, `cache_hit`,
`blocked`.

---

## 10. Decision record (one-line rationale each)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Retrieval meaning | Entity/segment resolution only (phase 1) | No document corpus exists; document RAG is speculative |
| Embedding provider | OpenRouter `/embeddings`, `openai/text-embedding-3-small` | Reuses existing key/httpx; zero new Python deps |
| Vector store | JSONB table + in-memory cosine | Few hundred vectors; avoids custom postgis+pgvector image |
| Unstructured RAG | Deferred behind `retrieve()` seam | YAGNI until a corpus is ingested |
| Guardrails | Custom deterministic gate + history sanitizer | Lower latency, no heavy Colang/LangChain dep, testable |
| Gate position | Before resolution/context; auto-insight exempt | Saves latency, prevents context leakage |
| Rejected UX | HTTP 200 `{blocked, message}` | Mirrors `needs_selection`; never an error |
| Output schema | Keep parser; add optional `citations` | Backward compatible; surfaces retrieval provenance |
| Markdown | Keep plain text | `pre-wrap` already works; renderer is an unneeded dep |
| Streaming | Not phase 1 | Conflicts with strict JSON parse; caching first |
| Structured probe | Cache "unsupported" per process | Removes 1 of up to 3 serial calls |
| Caching | Redis (existing) + in-process embedding cache | Reuses installed Redis |
| Auto-insight trigger | `POST /api/chat/bangjo/auto-insight`, 400 ms debounce | Typed, explicit, no synthetic chat messages |
| Auto-insight placement | Inline panel card + promote button | No thread spam; avoids overlap bug |
| Overlap fix | Dock left via CSS var + lifted panel state | Least invasive; keeps widget at shell level |
| Auth/rate limit | **Out of scope — stakeholder call** | Internal dashboard; product decision |
| Default model | **Stakeholder call** (move off `:free` for prod) | Latency/availability risk |

---

## 11. API contracts

### `POST /api/chat/bangjo` (existing; additive only)

Request unchanged: `{message, road_segment_id?, history[]}`.
Response gains optional fields (all additive, existing clients unaffected):

```jsonc
{
  "needs_selection": false,
  "answer": {
    "summary": "...", "drivers": ["..."], "asi_category": "...",
    "recommendation": "...", "evidence": ["..."],
    "citations": [{ "label": "Jalan Malioboro", "source": "segment_name" }], // NEW, optional
    "source": "llm"
  },
  "context_label": "Jalan Malioboro (SEG-0001)",
  "blocked": false,                 // NEW
  "message": null                   // NEW: friendly text when blocked=true
}
```

### `POST /api/chat/bangjo/auto-insight` (new)

```jsonc
// request — exactly one of the three
{ "road_segment_id": "SEG-0001" } | { "hex_id": 12345 } | { "stop_id": "STOP-1" }

// response
{
  "needs_selection": false,
  "answer": { "...": "...", "citations": [], "source": "llm" },
  "context_label": "Jalan Malioboro (SEG-0001)",
  "entity": { "type": "segment", "id": "SEG-0001" },  // NEW echo
  "cached": false                                     // NEW
}
```

Errors/unknown entities return 200 with `needs_selection: true` + `detail` (never 500), consistent
with the existing route.

### Frontend types (`types.ts`)

- `BangJoAnswer.citations?: { label: string; source?: string }[]`
- `BangJoReply.blocked?: boolean; message?: string`
- new `BangJoAutoInsightRequest` / response types in `services/api.ts`.

---

## 12. File-by-file change list

**Backend**

- `backend/app/api/routes/bangjo.py` — gate call at route entry; generalized resolution cascade;
  structured-capability cache; auto-insight route; citations pass-through; extended logging.
- `backend/app/services/bangjo_context.py` — entity→segment helpers (hex/stop), no numeric changes.
- `backend/app/services/bangjo_guardrails.py` — **new**: `screen_query`, `sanitize_history`.
- `backend/app/services/bangjo_retrieval.py` — **new**: embeddings client, cosine search,
  in-memory vector cache, `retrieve()` seam returning `[]` when disabled.
- `backend/app/models/segment_name_embedding.py` — **new** model.
- `backend/migrations/versions/<rev>_add_segment_name_embeddings.py` — **new** migration.
- `backend/app/core/config.py` — `BANGJO_EMBEDDINGS_ENABLED`, `BANGJO_EMBEDDING_MODEL`,
  `BANGJO_RESOLUTION_THRESHOLD`, `BANGJO_AUTOINSIGHT_TTL_SECONDS`, `BANGJO_CACHE_TTL_SECONDS`.
- `backend/requirements.txt` — **no new deps** (OpenRouter embeddings over existing `httpx`).
- `backend/tests/test_bangjo.py` — extend (see §13).

**Frontend**

- `frontend/src/components/Chatbot/BangJoWidget.tsx` — subscribe to selection/panel state; dock class.
- `frontend/src/hooks/useBangJoChat.ts` — handle `blocked`/`message`; render citations.
- `frontend/src/components/Chatbot/BangJoMessage.tsx` — optional citations footnote.
- `frontend/src/components/Map/MapView.tsx` — single `useEffect` publishing selection + `isPanelOpen`.
- `frontend/src/utils/selectionStore.ts` — publish full `SelectionState` + subscribe.
- `frontend/src/utils/bangjoLayout.ts` — **new** pure dock function.
- `frontend/src/utils/autoInsight.ts` — **new** debounce + per-entity cache helper.
- `frontend/src/components/Panel/{SegmentPanel,SidePanel,BusStopPanel,ActivityGridPanel}.tsx` —
  inline auto-insight card + "Tanya Bang Jo" promote button.
- `frontend/src/services/api.ts` — `fetchBangJoAutoInsight`.
- `frontend/src/types.ts` — additive fields above.
- `frontend/src/app/globals.css` — `--data-panel-width`, docked `.bangjo-panel`/`.bangjo-fab`,
  narrow-viewport FAB rule, citations styling.

---

## 13. Test plan

**Backend — extend `backend/tests/test_bangjo.py`** (reuse `_FakeDB`/`_FakeClient` patterns):

- Guardrail: out-of-scope rejected; injection blocked; overlong rejected; in-scope accepted;
  `sanitize_history` drops `system` role, caps count/length, strips injection; gate exception
  fails open.
- Resolution: alias normalization; embedding path resolves a misspelling (mocked embed);
  embeddings disabled/error → string matcher; below-threshold → `needs_selection`; "koridor
  tersibuk" routes to intent branch.
- Auto-insight: hex→segment and stop→segment mapping; per-entity cache hit sets `cached: true`;
  unknown entity → 200 `needs_selection`, not 500; fallback answer when LLM unavailable.
- Latency: second `_ask_llm` call skips the structured probe after a cached 400/422 (assert call count).
- Parser: `citations` preserved; fallback emits `[]`.

**Frontend — extend `frontend/tests/*.test.mjs`** (pure modules, no DOM dep):

- `bangjoLayout.test.mjs`: dock offsets for wide/narrow × panel-open/closed; FAB hidden on narrow
  with panel open.
- `autoInsight.test.mjs`: debounce coalesces rapid selection changes; cache returns same entity
  without a second request; entity switch bypasses cache.

**Not added:** jsdom/React Testing Library — would introduce a new heavy dev dependency; logic is
extracted to pure modules to fit the existing harness.

**Commands:** `pytest backend/tests/test_bangjo.py` and `npm test` (frontend), plus `npm run lint`.

---

## 14. Rollout / fallback

Consistent with the code's own docstring ("Any LLM failure degrades to a deterministic summary …
never a 500"), every new component degrades:

- **Embeddings** unavailable/disabled/error/threshold-miss → Layer A/C + existing string matcher.
- **Guardrail** internal error → fail open (sanitization still applies); never a 500.
- **Retrieval** (future doc RAG) → skip; structured-only context.
- **Auto-insight** failure → `_fallback_answer()` from the same context.
- **Cache** (Redis) down → compute directly.
- **Migration optional at runtime:** the new table may be empty/absent; resolution falls back to
  string matching. No hard DB dependency.
- **Flags:** all new behavior behind `config.py` settings; ship with embeddings/gate on only after
  the test suite is green.

**Phasing:** Phase 0 bug fixes (dock, structured-probe cache, history sanitize) → Phase 1
guardrails + resolution embeddings → Phase 2 auto-insight + caching → Phase 3 deferred
(unstructured corpus RAG, streaming).

---

## 15. Stakeholder decisions required before Phase 1

1. **Auth/rate limiting** on `/api/chat/bangjo` — intentional internal-only, or add?
2. **Model default** — stay on `nvidia/nemotron-3.5-lightning:free` or move to a paid model for
   production latency/availability?
3. **Unstructured corpus** — is there any material to ingest now, or is deferral correct?
