# Sprint 21c — The Debrief Page (Full Scope)

> **Sprint 21c** | Est. 10 sessions + 2 code reviews | Target: ~50 new pytest + ~30 new Vitest
> Post-sprint totals: ~1608 pytest + ~130 Vitest

---

## Part 1: Implementation Spec

### Scope — What's Included

The Debrief page is ARGUS's institutional knowledge layer. Three pillars:

1. **Daily Briefings** — Pre-market and end-of-day structured reports with template-based creation, full markdown editing, status management (draft/final/ai_generated), and rich reading via DocumentModal.

2. **Research Library** — Unified view of all project documentation. Hybrid source: filesystem docs (read-only, auto-discovered from repo) + database docs (full CRUD with categories and tags).

3. **Learning Journal** — Typed entries (observation, trade_annotation, pattern_note, system_note) with inline creation, inline editing, tag autocomplete, trade linking via search component, and comprehensive filtering.

**Cross-cutting:**
- Full-text search via comprehensive LIKE queries across title/content/tags (DEC-200)
- 7th page in navigation (DEC-199), GraduationCap icon, keyboard shortcuts 1–7
- Responsive at all breakpoints (phone/tablet/desktop)
- Skeleton loading, Framer Motion animations, contextual empty states
- Dev mode with realistic mock data

### Database Schema

#### New: `briefings` table

```sql
CREATE TABLE IF NOT EXISTS briefings (
    id TEXT PRIMARY KEY,                    -- ULID
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    briefing_type TEXT NOT NULL,            -- 'pre_market' or 'eod'
    status TEXT NOT NULL DEFAULT 'draft',   -- 'draft', 'final', 'ai_generated'
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',       -- Markdown
    metadata TEXT,                          -- JSON: structured data (watchlist, regime, etc.)
    author TEXT NOT NULL DEFAULT 'user',    -- 'user' or 'claude'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, briefing_type)
);

CREATE INDEX IF NOT EXISTS idx_briefings_date ON briefings(date);
CREATE INDEX IF NOT EXISTS idx_briefings_type ON briefings(briefing_type);
CREATE INDEX IF NOT EXISTS idx_briefings_status ON briefings(status);
```

#### Updated: `journal_entries` table (replace existing — never populated)

```sql
DROP TABLE IF EXISTS journal_entries;

CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,                    -- ULID
    entry_type TEXT NOT NULL,               -- 'observation', 'trade_annotation', 'pattern_note', 'system_note'
    title TEXT NOT NULL DEFAULT '',          -- Short summary for list display
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',    -- 'user' or 'claude'
    linked_strategy_id TEXT,
    linked_trade_ids TEXT,                  -- JSON array of trade IDs
    tags TEXT,                              -- JSON array
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_journal_type ON journal_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_journal_author ON journal_entries(author);
CREATE INDEX IF NOT EXISTS idx_journal_created ON journal_entries(created_at);
```

#### New: `documents` table

```sql
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,                    -- ULID
    category TEXT NOT NULL,                 -- 'research', 'strategy', 'backtest', 'ai_report'
    title TEXT NOT NULL,
    content TEXT NOT NULL,                  -- Markdown
    author TEXT NOT NULL DEFAULT 'user',    -- 'user' or 'claude'
    tags TEXT,                              -- JSON array
    metadata TEXT,                          -- JSON: optional extra data
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);
```

### Service Layer

**File: `argus/analytics/debrief_service.py`**

`DebriefService` class takes `DatabaseManager`, provides all CRUD + query methods. Follows TradeLogger pattern (async, uses `generate_id()` for ULIDs).

**Briefing methods:**
- `create_briefing(date, briefing_type, title?, content?)` — Generates template content if content is empty. Returns briefing dict.
- `get_briefing(briefing_id)` → dict | None
- `list_briefings(briefing_type?, status?, date_from?, date_to?, limit=50, offset=0)` → list[dict]
- `update_briefing(briefing_id, title?, content?, status?, metadata?)` → dict | None
- `delete_briefing(briefing_id)` → bool
- `_generate_pre_market_template()` → str — Returns markdown template with section headers (Market Overview, Key Levels, Watchlist, Catalysts, Game Plan)
- `_generate_eod_template()` → str — Returns markdown template (Session Summary, Trades Review, What Worked, What Didn't, Lessons, Tomorrow's Focus)

**Journal methods:**
- `create_journal_entry(entry_type, title, content, linked_strategy_id?, linked_trade_ids?, tags?)` → dict
- `get_journal_entry(entry_id)` → dict | None
- `list_journal_entries(entry_type?, strategy_id?, tag?, search?, date_from?, date_to?, limit=50, offset=0)` → list[dict]
- `update_journal_entry(entry_id, title?, content?, entry_type?, linked_strategy_id?, linked_trade_ids?, tags?)` → dict | None
- `delete_journal_entry(entry_id)` → bool
- `get_journal_tags()` → list[str] — Extracts and deduplicates tags from all journal entries' JSON arrays.

**Document methods (database docs):**
- `create_document(category, title, content, tags?, metadata?)` → dict
- `get_document(document_id)` → dict | None  
- `list_documents(category?)` → list[dict]
- `update_document(document_id, title?, content?, category?, tags?, metadata?)` → dict | None
- `delete_document(document_id)` → bool

**Filesystem document discovery:**
- `discover_filesystem_documents()` → list[dict] — Scans `docs/research/`, `docs/strategies/`, `docs/backtesting/` for `.md` files. Returns dicts with id=`fs_{category}_{filename}`, category inferred from directory, title extracted from first `#` heading or filename, word_count, reading_time_min, last_modified from file stat. IDs are stable (filename-based).

**Search method:**
- `search_all(query, scope='all')` → dict — Searches across briefings (title+content), journal entries (title+content+tags), and documents (title+content+tags) using LIKE '%term%'. Returns `{briefings: [...], journal: [...], documents: [...]}`. `scope` can be 'all', 'briefings', 'journal', or 'documents'.

### API Routes

#### `argus/api/routes/briefings.py`

```
POST   /api/v1/debrief/briefings          — Create briefing (from template)
GET    /api/v1/debrief/briefings          — List briefings (filters: type, status, date_from, date_to, limit, offset)
GET    /api/v1/debrief/briefings/{id}     — Get single briefing
PUT    /api/v1/debrief/briefings/{id}     — Update briefing (title, content, status, metadata)
DELETE /api/v1/debrief/briefings/{id}     — Delete briefing
```

Pydantic models:
- `CreateBriefingRequest(date: str, briefing_type: Literal['pre_market', 'eod'], title: str | None = None)`
- `UpdateBriefingRequest(title: str | None, content: str | None, status: str | None, metadata: dict | None)`
- `BriefingResponse(id, date, briefing_type, status, title, content, metadata, author, created_at, updated_at, word_count: int, reading_time_min: int)`
- `BriefingsListResponse(briefings: list, total: int)`

#### `argus/api/routes/documents.py`

```
GET    /api/v1/debrief/documents          — List all documents (filesystem + DB, category filter)
GET    /api/v1/debrief/documents/{id}     — Get single document (handles fs_ prefix for filesystem)
POST   /api/v1/debrief/documents          — Create database document
PUT    /api/v1/debrief/documents/{id}     — Update database document
DELETE /api/v1/debrief/documents/{id}     — Delete database document (rejects fs_ IDs)
GET    /api/v1/debrief/documents/tags     — List all unique document tags
```

Pydantic models:
- `CreateDocumentRequest(category, title, content, tags: list[str] | None = None)`
- `UpdateDocumentRequest(title?, content?, category?, tags?)`
- `DocumentResponse(id, category, title, content, author, tags, word_count, reading_time_min, source: Literal['filesystem', 'database'], is_editable: bool, created_at, updated_at)`
- `DocumentsListResponse(documents: list, total: int)`

#### `argus/api/routes/journal.py`

```
POST   /api/v1/debrief/journal            — Create journal entry
GET    /api/v1/debrief/journal            — List entries (filters: type, strategy_id, tag, search, date_from, date_to, limit, offset)
GET    /api/v1/debrief/journal/tags       — List all unique tags (for autocomplete)
GET    /api/v1/debrief/journal/{id}       — Get single entry
PUT    /api/v1/debrief/journal/{id}       — Update entry
DELETE /api/v1/debrief/journal/{id}       — Delete entry
```

Pydantic models:
- `CreateJournalEntryRequest(entry_type, title, content, linked_strategy_id?, linked_trade_ids?: list[str], tags?: list[str])`
- `UpdateJournalEntryRequest(title?, content?, entry_type?, linked_strategy_id?, linked_trade_ids?, tags?)`
- `JournalEntryResponse(id, entry_type, title, content, author, linked_strategy_id, linked_trade_ids, tags, created_at, updated_at)`
- `JournalEntriesListResponse(entries: list, total: int)`
- `JournalTagsResponse(tags: list[str])`

#### `argus/api/routes/debrief_search.py`

```
GET    /api/v1/debrief/search             — Search across all debrief content (query, scope)
```

#### Router registration

All four routers mounted under `/debrief` prefix tag in `routes/__init__.py`:
```python
api_router.include_router(briefings_router, prefix="/debrief/briefings", tags=["debrief"])
api_router.include_router(documents_router, prefix="/debrief/documents", tags=["debrief"])
api_router.include_router(journal_router, prefix="/debrief/journal", tags=["debrief"])
api_router.include_router(search_router, prefix="/debrief", tags=["debrief"])
```

#### AppState update

Add `debrief_service: DebriefService | None = None` to AppState dataclass. Wire in `dev_state.py` and `main.py`.

### Dev Mode Mock Data

**5 mock briefings** (added in `dev_state.py`):
1. Pre-market 2 days ago (status=final) — bullish SPY, 5-symbol watchlist, catalyst notes
2. EOD 2 days ago (status=final) — 8 trades, $342 profit, 62.5% win rate, VWAP lesson
3. Pre-market 1 day ago (status=final) — low-conviction choppy day
4. EOD 1 day ago (status=final) — 5 trades, -$127, overtrading lesson
5. Pre-market today (status=draft) — partially filled template

**3 mock database documents:**
1. "VWAP Entry Timing Research" (category=research, tags=[vwap, timing, entry])
2. "ORB Gap Size Analysis" (category=research, tags=[orb, gaps, statistics])
3. "AI Scoring Calibration Notes" (category=ai_report, tags=[ai, scoring, calibration])

**10 mock journal entries** (mixed types, spanning 2 weeks):
- 3 observations (regime timing, VWAP gap patterns, afternoon momentum timing)
- 2 trade_annotations with linked_trade_ids (TSLA early exit, AMD low-volume)
- 2 pattern_notes (ORB gap threshold, regime-based sizing)
- 2 system_notes (throttle threshold, RegimeClassifier lag)
- 1 observation (earnings vs momentum catalysts)

Tags: regime-change, timing, early-exit, patience, gap-day, false-breakout, low-volume, discipline, momentum, throttle, earnings, catalyst

### Frontend Architecture

#### Types (`argus/ui/src/api/types.ts` additions)

```typescript
// Briefings
export interface Briefing {
  id: string;
  date: string;
  briefing_type: 'pre_market' | 'eod';
  status: 'draft' | 'final' | 'ai_generated';
  title: string;
  content: string;
  metadata: Record<string, unknown> | null;
  author: string;
  created_at: string;
  updated_at: string;
  word_count: number;
  reading_time_min: number;
}

export interface BriefingsListResponse {
  briefings: Briefing[];
  total: number;
}

// Research Documents
export interface ResearchDocument {
  id: string;
  category: 'research' | 'strategy' | 'backtest' | 'ai_report';
  title: string;
  content: string;
  author: string;
  tags: string[];
  word_count: number;
  reading_time_min: number;
  source: 'filesystem' | 'database';
  is_editable: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentsListResponse {
  documents: ResearchDocument[];
  total: number;
}

// Journal
export type JournalEntryType = 'observation' | 'trade_annotation' | 'pattern_note' | 'system_note';

export interface JournalEntry {
  id: string;
  entry_type: JournalEntryType;
  title: string;
  content: string;
  author: string;
  linked_strategy_id: string | null;
  linked_trade_ids: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface JournalEntriesListResponse {
  entries: JournalEntry[];
  total: number;
}

export interface JournalTagsResponse {
  tags: string[];
}

// Debrief Search
export interface DebriefSearchResponse {
  briefings: Briefing[];
  journal: JournalEntry[];
  documents: ResearchDocument[];
}
```

#### API Client additions (`argus/ui/src/api/client.ts`)

New functions for all debrief endpoints. Follow existing `fetchWithAuth` pattern.

#### TanStack Query Hooks

**`useBriefings.ts`:**
- `useBriefings(filters?)` — useQuery, 30s polling
- `useBriefing(id)` — useQuery, enabled when id is truthy
- `useCreateBriefing()` — useMutation, invalidates ['briefings']
- `useUpdateBriefing()` — useMutation, invalidates ['briefings'] + ['briefing', id]
- `useDeleteBriefing()` — useMutation, invalidates ['briefings']

**`useDocuments.ts`:**
- `useDocuments(category?)` — useQuery, 60s polling
- `useDocument(id)` — useQuery, enabled when id is truthy
- `useCreateDocument()` — useMutation, invalidates ['documents']
- `useUpdateDocument()` — useMutation, invalidates ['documents'] + ['document', id]
- `useDeleteDocument()` — useMutation, invalidates ['documents']
- `useDocumentTags()` — useQuery, staleTime 5 min

**`useJournal.ts`:**
- `useJournalEntries(filters?)` — useQuery, 30s polling
- `useJournalEntry(id)` — useQuery
- `useCreateJournalEntry()` — useMutation with optimistic update, invalidates ['journal']
- `useUpdateJournalEntry()` — useMutation, invalidates ['journal'] + ['journal-entry', id]
- `useDeleteJournalEntry()` — useMutation, invalidates ['journal']
- `useJournalTags()` — useQuery, staleTime 5 min

**`useDebriefSearch.ts`:**
- `useDebriefSearch(query, scope?)` — useQuery with 300ms debounce, enabled when query.length >= 2

#### Zustand Store

**`stores/debriefUI.ts`:**
```typescript
interface DebriefUIState {
  activeSection: 'briefings' | 'research' | 'journal';
  setActiveSection: (section) => void;

  // Briefings
  editingBriefingId: string | null;
  setEditingBriefingId: (id: string | null) => void;
  readingBriefingId: string | null;
  setReadingBriefingId: (id: string | null) => void;

  // Research
  researchCategoryFilter: string | null;
  setResearchCategoryFilter: (cat: string | null) => void;
  editingDocumentId: string | null;
  setEditingDocumentId: (id: string | null) => void;
  readingDocumentId: string | null;
  setReadingDocumentId: (id: string | null) => void;

  // Journal
  journalDraftExpanded: boolean;
  setJournalDraftExpanded: (expanded: boolean) => void;
  editingJournalEntryId: string | null;
  setEditingJournalEntryId: (id: string | null) => void;
  journalFilters: {
    type: JournalEntryType | null;
    strategy_id: string | null;
    tag: string | null;
    search: string;
  };
  setJournalFilter: (key, value) => void;
  clearJournalFilters: () => void;
}
```

#### Feature Components

**`argus/ui/src/features/debrief/`**

```
debrief/
├── index.ts                    # Barrel exports
├── DebriefSkeleton.tsx         # Loading skeleton for all 3 tabs
├── briefings/
│   ├── BriefingList.tsx        # Reverse-chrono feed + "New Briefing" button
│   ├── BriefingCard.tsx        # Date, type badge, status badge, title, preview, reading time
│   └── BriefingEditor.tsx      # Full markdown editor (title + textarea + status + save/cancel)
├── research/
│   ├── ResearchLibrary.tsx     # Category filter + grid of docs + "Add Document" button
│   ├── ResearchDocCard.tsx     # Title, category badge, tags, word count, source badge
│   └── DocumentEditor.tsx      # Create/edit database doc (title + category + content + tags)
├── journal/
│   ├── JournalList.tsx         # Inline form at top + filter row + reverse-chrono entries
│   ├── JournalEntryCard.tsx    # Type badge, title, preview, tags, timestamp, edit/delete
│   ├── JournalEntryForm.tsx    # Collapsed (input) → expanded (full form w/ type, tags, content, trade links)
│   ├── JournalTagInput.tsx     # Tag input with autocomplete dropdown
│   └── TradeSearchInput.tsx    # Search trades by symbol/date, select to link, display as chips
└── __tests__/
    ├── BriefingCard.test.tsx
    ├── BriefingEditor.test.tsx
    ├── ResearchDocCard.test.tsx
    ├── JournalEntryCard.test.tsx
    ├── JournalEntryForm.test.tsx
    ├── JournalTagInput.test.tsx
    └── TradeSearchInput.test.tsx
```

**Component Details:**

**BriefingList** — Shows briefings newest-first. "New Briefing" button opens a dropdown (Pre-Market / End of Day), creates via API with template, then opens BriefingEditor. Each card: click to read (DocumentModal), edit icon to edit (BriefingEditor), delete icon with ConfirmModal.

**BriefingEditor** — Not a modal; replaces the list view when editing. Title input, large markdown textarea (min-height 400px), MarkdownRenderer preview toggle, status dropdown (draft/final), save/cancel buttons. Unsaved changes warning.

**ResearchLibrary** — SegmentedTab filter (All / Research / Strategy / Backtest / AI Reports). Grid of ResearchDocCard. "Add Document" button (visible for database docs). Click card to read (DocumentModal). Edit/delete icons only on database docs (is_editable=true).

**DocumentEditor** — Slide-in panel or full-view (matches BriefingEditor pattern). Title, category dropdown, content textarea with preview toggle, JournalTagInput for tags, save/cancel.

**JournalList** — JournalEntryForm at top (collapsed by default). Filter row: type dropdown, strategy dropdown, tag dropdown (from useJournalTags), search input. Below: reverse-chrono JournalEntryCards.

**JournalEntryCard** — Shows type badge (color-coded), title (bold), content preview (2-line clamp), tags as small badges, linked trade count badge (clickable), timestamp, edit/delete icons. Click edit → card transforms into JournalEntryForm (pre-filled). Delete → ConfirmModal.

**JournalEntryForm** — Two states:
- *Collapsed*: Single-line text input with placeholder "What did you observe?" + expand button
- *Expanded*: Title input, type selector (4 radio-style buttons), content textarea, JournalTagInput, TradeSearchInput (for linking), linked strategy dropdown, save/cancel

**JournalTagInput** — Text input. On keystroke, queries useJournalTags for autocomplete matches. Dropdown below input shows matching tags. Enter or click adds tag. Tags display as removable chips below input.

**TradeSearchInput** — Text input for symbol search. Queries GET /trades with symbol filter. Shows matching trades in dropdown (symbol, date, P&L, strategy). Click adds to linked list. Linked trades display as removable chips (symbol + date). Clicking a linked trade chip opens TradeDetailPanel.

#### Navigation Update

**Sidebar.tsx** — Add 7th nav item: `{ to: '/debrief', icon: GraduationCap, label: 'The Debrief' }` after Orchestrator, before System. Import GraduationCap from lucide-react. Keyboard shortcuts 1–7.

**MobileNav.tsx** — Add 7th item: `{ to: '/debrief', icon: GraduationCap, label: 'Debrief' }`. Reduce text size to fit 7 items.

**App.tsx** — Add route: `<Route path="/debrief" element={<DebriefPage />} />`

#### Badge Color Coding

| Item | Color |
|------|-------|
| Entry type: observation | blue |
| Entry type: trade_annotation | green |
| Entry type: pattern_note | amber |
| Entry type: system_note | gray |
| Briefing: pre_market | blue |
| Briefing: eod | amber |
| Status: draft | gray |
| Status: final | green |
| Status: ai_generated | purple |
| Category: research | blue |
| Category: strategy | green |
| Category: backtest | amber |
| Category: ai_report | purple |
| Source: filesystem | gray outline |
| Source: database | blue outline |

---

## Part 2: Session Breakdown

| Session | Focus | New Files | Modified Files | Est. Tests |
|---------|-------|-----------|----------------|------------|
| 1 | Schema + DebriefService | debrief_service.py | schema.sql | — |
| 2 | API routes + AppState | 4 route files | dependencies.py, routes/__init__.py | — |
| 3 | Dev mock data + pytest | test_debrief_service.py, test_briefings_api.py, test_documents_api.py, test_journal_api.py | dev_state.py | ~50 pytest |
| **CR1** | **Code Review 1** | | | |
| 4 | Frontend scaffold + Nav | types.ts additions, client.ts additions, 3 hook files, debriefUI.ts, DebriefPage.tsx, DebriefSkeleton.tsx | Sidebar.tsx, MobileNav.tsx, App.tsx, hooks/index.ts | — |
| 5 | Briefings tab | BriefingList, BriefingCard, BriefingEditor | — | — |
| 6 | Research Library tab | ResearchLibrary, ResearchDocCard, DocumentEditor | — | — |
| 7 | Journal tab | JournalList, JournalEntryCard, JournalEntryForm, JournalTagInput | — | — |
| 8 | Journal enhancements | TradeSearchInput | JournalEntryCard (inline edit mode), JournalEntryForm (trade linking section) | — |
| 9 | Polish + responsive | — | All debrief components (skeleton, animations, responsive, empty states, keyboard shortcuts) | — |
| 10 | Vitest + cleanup | 7 test files in __tests__/ | Gap-fill any pytest | ~30 Vitest |
| **CR2** | **Code Review 2** | | | |

---

## Part 3: Copy-Paste Prompts

### Session 1: Schema + DebriefService

```
ARGUS Sprint 21c — Session 1: Schema + DebriefService

CONTEXT: Building The Debrief page (7th page). This session creates the database schema and service layer for three content types: briefings, journal entries, and documents.

REFERENCE FILES (read these first):
- argus/db/schema.sql (current schema — you'll add to this)
- argus/analytics/trade_logger.py (follow this pattern for service layer: async, DatabaseManager, generate_id())
- argus/db/manager.py (DatabaseManager interface)

TASK 1: Update schema.sql

Add three table definitions at the end of schema.sql (before the commented-out system_health table):

1. `briefings` table:
   - id TEXT PRIMARY KEY (ULID)
   - date TEXT NOT NULL (YYYY-MM-DD)
   - briefing_type TEXT NOT NULL ('pre_market' or 'eod')
   - status TEXT NOT NULL DEFAULT 'draft' ('draft', 'final', 'ai_generated')
   - title TEXT NOT NULL
   - content TEXT NOT NULL DEFAULT ''
   - metadata TEXT (JSON)
   - author TEXT NOT NULL DEFAULT 'user'
   - created_at, updated_at TEXT with datetime('now') defaults
   - UNIQUE(date, briefing_type)
   - Indexes on date, briefing_type, status

2. Replace the existing `journal_entries` table (it was never populated, safe to DROP + recreate):
   - id TEXT PRIMARY KEY (ULID)
   - entry_type TEXT NOT NULL ('observation', 'trade_annotation', 'pattern_note', 'system_note')
   - title TEXT NOT NULL DEFAULT ''
   - content TEXT NOT NULL
   - author TEXT NOT NULL DEFAULT 'user'
   - linked_strategy_id TEXT
   - linked_trade_ids TEXT (JSON array)
   - tags TEXT (JSON array)
   - created_at, updated_at TEXT with datetime('now') defaults
   - Indexes on entry_type, author, created_at

3. `documents` table:
   - id TEXT PRIMARY KEY (ULID)
   - category TEXT NOT NULL ('research', 'strategy', 'backtest', 'ai_report')
   - title TEXT NOT NULL
   - content TEXT NOT NULL
   - author TEXT NOT NULL DEFAULT 'user'
   - tags TEXT (JSON array)
   - metadata TEXT (JSON)
   - created_at, updated_at TEXT with datetime('now') defaults
   - Indexes on category, created_at

TASK 2: Create argus/analytics/debrief_service.py

Follow TradeLogger's pattern. Class takes DatabaseManager in __init__.

Briefing methods:
- create_briefing(date, briefing_type, title=None, content=None) → dict. If content is None/empty, generate template via _generate_pre_market_template() or _generate_eod_template(). Auto-generate title from type+date if not provided. Use generate_id() for ULID.
- get_briefing(briefing_id) → dict | None
- list_briefings(briefing_type=None, status=None, date_from=None, date_to=None, limit=50, offset=0) → tuple[list[dict], int]. Returns (briefings, total_count). Add computed word_count and reading_time_min to each dict.
- update_briefing(briefing_id, **kwargs) → dict | None. Update only provided fields. Set updated_at.
- delete_briefing(briefing_id) → bool

Journal methods:
- create_journal_entry(entry_type, title, content, linked_strategy_id=None, linked_trade_ids=None, tags=None) → dict. Store linked_trade_ids and tags as JSON strings.
- get_journal_entry(entry_id) → dict | None. Parse JSON fields on return.
- list_journal_entries(entry_type=None, strategy_id=None, tag=None, search=None, date_from=None, date_to=None, limit=50, offset=0) → tuple[list[dict], int]. Search uses LIKE on title and content. Tag filter uses LIKE on JSON array string.
- update_journal_entry(entry_id, **kwargs) → dict | None
- delete_journal_entry(entry_id) → bool
- get_journal_tags() → list[str]. Query all non-null tags columns, parse JSON arrays, deduplicate, sort alphabetically.

Document methods (database documents):
- create_document(category, title, content, tags=None, metadata=None) → dict
- get_document(document_id) → dict | None
- list_documents(category=None) → list[dict]. Add computed word_count and reading_time_min.
- update_document(document_id, **kwargs) → dict | None
- delete_document(document_id) → bool

Filesystem document discovery:
- discover_filesystem_documents(base_dir=None) → list[dict]. Default base_dir is project root. Scan docs/research/*.md, docs/strategies/STRATEGY_*.md, docs/backtesting/*.md. For each file: id=f"fs_{category}_{stem}" (stable), category from dir name, title from first # heading or filename, content=full file text, word_count, reading_time_min (words/200), last_modified from stat, source='filesystem', is_editable=False, author='system'.

Search:
- search_all(query, scope='all') → dict. Search briefings (title+content), journal (title+content+tags), documents (title+content+tags) with LIKE '%{query}%'. Return {briefings: [...], journal: [...], documents: [...]}.

Template methods:
- _generate_pre_market_template() → str. Markdown with sections: ## Market Overview, ## Key Levels (SPY, QQQ), ## Watchlist, ## Catalysts, ## Game Plan. Each section has placeholder text.
- _generate_eod_template() → str. Markdown with sections: ## Session Summary, ## Trades Review, ## What Worked, ## What Didn't Work, ## Key Lessons, ## Tomorrow's Focus. Each with placeholder text.

Helper:
- _compute_word_count(text: str) → int
- _compute_reading_time(word_count: int) → int (words / 200, min 1)
- _parse_json_field(value: str | None) → list. Safe JSON parse, returns [] on None/error.

DON'T write tests in this session — Session 3 handles all testing.

DEFINITION OF DONE:
- schema.sql has all 3 tables (briefings, updated journal_entries, documents) with proper indexes
- debrief_service.py is complete with all methods listed above
- All methods are async, use aiosqlite through DatabaseManager
- JSON fields stored as text, parsed on retrieval
- Template generation returns meaningful markdown section headers
- File discovery handles missing directories gracefully (returns empty list)
- Code passes ruff lint
```

### Session 2: API Routes + AppState

```
ARGUS Sprint 21c — Session 2: API Routes + AppState Wiring

CONTEXT: Session 1 created the DebriefService and schema. This session creates the FastAPI route files and wires the service into AppState.

REFERENCE FILES (read these first):
- argus/api/routes/strategies.py (follow this pattern for route structure)
- argus/api/routes/trades.py (follow for query parameter patterns)
- argus/api/routes/__init__.py (router registration)
- argus/api/dependencies.py (AppState)
- argus/api/auth.py (require_auth dependency)
- argus/analytics/debrief_service.py (service you're calling)

TASK 1: Create argus/api/routes/briefings.py

Router with tag="debrief". All routes require auth via Depends(require_auth).

Pydantic models in-file (same pattern as other route files):
- CreateBriefingRequest: date (str), briefing_type (Literal['pre_market', 'eod']), title (str | None = None)
- UpdateBriefingRequest: title (str | None = None), content (str | None = None), status (str | None = None), metadata (dict | None = None)
- BriefingResponse: all fields from service dict + word_count + reading_time_min
- BriefingsListResponse: briefings (list[BriefingResponse]), total (int)

Routes:
- POST / → create briefing, return BriefingResponse (201)
- GET / → list with query params (briefing_type, status, date_from, date_to, limit, offset), return BriefingsListResponse
- GET /{briefing_id} → single briefing, 404 if not found
- PUT /{briefing_id} → update, 404 if not found
- DELETE /{briefing_id} → 204 no content

Access DebriefService via: state = Depends(get_app_state), then state.debrief_service. Handle debrief_service being None (503 Service Unavailable).

TASK 2: Create argus/api/routes/documents.py

Router with tag="debrief". All routes require auth.

Pydantic models:
- CreateDocumentRequest: category (str), title (str), content (str), tags (list[str] | None = None)
- UpdateDocumentRequest: title, content, category, tags — all optional
- DocumentResponse: all fields + word_count + reading_time_min + source + is_editable
- DocumentsListResponse: documents (list[DocumentResponse]), total (int)

Routes:
- GET / → list all docs. Query param: category (optional). Merge filesystem docs (discover_filesystem_documents) with database docs (list_documents). Sort by category then title. Return DocumentsListResponse.
- GET /{document_id} → if ID starts with 'fs_', resolve from filesystem docs. Otherwise query DB. 404 if not found.
- POST / → create database document, return DocumentResponse (201)
- PUT /{document_id} → update database doc. Reject fs_ IDs with 400 "Cannot edit filesystem documents".
- DELETE /{document_id} → delete database doc. Reject fs_ IDs with 400.
- GET /tags → return unique tags from all database documents.

TASK 3: Create argus/api/routes/journal.py

Router with tag="debrief". All routes require auth.

Pydantic models:
- CreateJournalEntryRequest: entry_type (Literal['observation', 'trade_annotation', 'pattern_note', 'system_note']), title (str), content (str), linked_strategy_id (str | None), linked_trade_ids (list[str] | None), tags (list[str] | None)
- UpdateJournalEntryRequest: all fields optional
- JournalEntryResponse: all fields, with linked_trade_ids and tags as lists (not JSON strings)
- JournalEntriesListResponse: entries (list[JournalEntryResponse]), total (int)
- JournalTagsResponse: tags (list[str])

Routes:
- POST / → create entry, return JournalEntryResponse (201)
- GET / → list with filters (entry_type, strategy_id, tag, search, date_from, date_to, limit, offset)
- GET /tags → return JournalTagsResponse
- GET /{entry_id} → single entry, 404 if not found
- PUT /{entry_id} → update, 404 if not found
- DELETE /{entry_id} → 204

TASK 4: Create argus/api/routes/debrief_search.py

Simple router with one GET /search endpoint. Query params: query (str, required), scope (str, default='all').
Returns merged results from debrief_service.search_all().

TASK 5: Wire everything together

1. Update argus/api/dependencies.py — add debrief_service field to AppState:
   debrief_service: DebriefService | None = None
   (Import DebriefService under TYPE_CHECKING)

2. Update argus/api/routes/__init__.py — import and register all 4 new routers under /debrief prefix.

3. DO NOT update dev_state.py yet — that's Session 3.

DEFINITION OF DONE:
- 4 new route files created with proper Pydantic models and error handling
- AppState has debrief_service field
- All routers registered in __init__.py
- All routes require JWT auth
- Filesystem document operations properly rejected for write endpoints
- Code passes ruff lint
```

### Session 3: Dev Mock Data + Pytest

```
ARGUS Sprint 21c — Session 3: Dev Mock Data + Pytest Tests

CONTEXT: Sessions 1-2 created the service layer and API routes. This session adds dev mode mock data and comprehensive pytest tests for both layers.

REFERENCE FILES (read these first):
- argus/api/dev_state.py (add mock data here — follow existing patterns)
- tests/api/conftest.py (test fixtures — you'll extend these)
- tests/api/test_strategies.py (follow this pattern for API tests)
- tests/analytics/ (follow patterns for service tests)
- argus/analytics/debrief_service.py (service under test)
- argus/api/routes/briefings.py, documents.py, journal.py (routes under test)

TASK 1: Update dev_state.py

Add mock data seeding in the create_dev_state() function. After the existing trade/position seeding, add:

5 mock briefings (insert via debrief_service):
1. Pre-market, 2 days ago, status='final', title="Pre-Market Briefing — Feb 25, 2026"
   Content: Full pre-market template with filled sections. SPY bullish above 20MA, watchlist: NVDA, TSLA, AMD, AAPL, MSFT. Catalyst: NVDA earnings aftermath.
2. EOD, 2 days ago, status='final', title="End of Day Review — Feb 25, 2026"
   Content: 8 trades, $342 net P&L, 62.5% win rate. Lesson about VWAP entries on low-volume stocks.
3. Pre-market, 1 day ago, status='final', title="Pre-Market Briefing — Feb 26, 2026"
   Content: Sparse — choppy expected, reduced position size planned.
4. EOD, 1 day ago, status='final', title="End of Day Review — Feb 26, 2026"
   Content: 5 trades, -$127 net P&L. Overtrading lesson.
5. Pre-market, today, status='draft', title="Pre-Market Briefing — Feb 27, 2026"
   Content: Partially filled template (Market Overview done, rest has placeholder text).

3 mock database documents:
1. category='research', title="VWAP Entry Timing Research", tags=['vwap', 'timing', 'entry']. Content: ~200 words about VWAP pullback entry timing analysis.
2. category='research', title="ORB Gap Size Analysis", tags=['orb', 'gaps', 'statistics']. Content: ~150 words about gap size correlation with ORB success.
3. category='ai_report', title="AI Scoring Calibration Notes", tags=['ai', 'scoring', 'calibration']. Content: ~100 words placeholder for future AI layer.

10 mock journal entries (use realistic linked_trade_ids from the seeded trades):
- 3 observations: (1) "Regime transitions happen faster than expected" tags=[regime-change, timing], (2) "VWAP gap patterns on high-gap days" tags=[gap-day, false-breakout], (3) "Afternoon momentum works best on trend days" tags=[momentum, timing]
- 2 trade_annotations: (1) "TSLA — exited too early on T1" tags=[early-exit, patience] linked_trade_ids=[use a real trade id from seeded trades], (2) "AMD — entered on low volume, paid the price" tags=[low-volume, discipline]
- 2 pattern_notes: (1) "ORB gap threshold might need to be 3% not 2%" tags=[orb, gap-day], (2) "Regime-based position sizing idea" tags=[regime-change, discipline]
- 2 system_notes: (1) "Throttle kicks in too aggressively at 3 consecutive losses" tags=[throttle], (2) "RegimeClassifier has ~30min lag on regime changes" tags=[regime-change]
- 1 observation: "Earnings catalysts produce bigger moves than momentum catalysts" tags=[earnings, catalyst, momentum]

Spread entries across the last 2 weeks with realistic timestamps.

TASK 2: Update tests/api/conftest.py

Add fixtures:
- test_debrief_service: DebriefService backed by test_db
- app_state fixture: add debrief_service field (update existing fixture)
- seeded_debrief_service: DebriefService pre-populated with 3 briefings + 5 journal entries + 2 documents

TASK 3: Create tests/analytics/test_debrief_service.py

Target: ~25 tests covering:

Briefings:
- test_create_briefing_with_template (pre_market)
- test_create_briefing_with_template_eod
- test_create_briefing_custom_content
- test_get_briefing
- test_get_briefing_not_found
- test_list_briefings_all
- test_list_briefings_filter_type
- test_list_briefings_filter_date_range
- test_list_briefings_pagination
- test_update_briefing
- test_delete_briefing
- test_briefing_unique_constraint (same date+type should raise)

Journal:
- test_create_journal_entry
- test_create_journal_entry_with_tags_and_trades
- test_list_journal_entries_filter_type
- test_list_journal_entries_filter_tag
- test_list_journal_entries_search
- test_update_journal_entry
- test_delete_journal_entry
- test_get_journal_tags

Documents:
- test_create_document
- test_list_documents_by_category
- test_update_document
- test_delete_document
- test_discover_filesystem_documents (create temp .md files, verify discovery)

Search:
- test_search_all_finds_across_types

TASK 4: Create tests/api/test_debrief_api.py

Target: ~25 tests covering all API endpoints:

Briefings API:
- test_create_briefing
- test_create_briefing_unauthenticated (401)
- test_list_briefings
- test_get_briefing
- test_get_briefing_not_found (404)
- test_update_briefing
- test_delete_briefing

Documents API:
- test_list_documents (should include filesystem docs)
- test_get_filesystem_document
- test_create_database_document
- test_update_database_document
- test_reject_edit_filesystem_document (400)
- test_reject_delete_filesystem_document (400)
- test_delete_database_document
- test_document_tags

Journal API:
- test_create_journal_entry
- test_list_journal_entries
- test_list_journal_entries_with_filters
- test_get_journal_entry
- test_update_journal_entry
- test_delete_journal_entry
- test_journal_tags

Search API:
- test_search_briefings
- test_search_journal
- test_search_all_scopes

Run all tests: pytest tests/analytics/test_debrief_service.py tests/api/test_debrief_api.py -v
Verify existing tests still pass: pytest --tb=short -q

DEFINITION OF DONE:
- Dev mode shows realistic mock briefings, documents, and journal entries
- ~50 new pytest tests all passing
- All existing tests still pass
- Zero ruff lint errors
```

### Session 4: Frontend Scaffold + Nav

```
ARGUS Sprint 21c — Session 4: Frontend Scaffold + Nav Update

CONTEXT: Backend is complete (Sessions 1-3, code reviewed). This session creates the frontend scaffold: TypeScript types, API client functions, TanStack Query hooks, Zustand store, the DebriefPage shell, and navigation updates.

REFERENCE FILES (read these first):
- argus/ui/src/api/types.ts (add new types here)
- argus/ui/src/api/client.ts (add new API functions here)
- argus/ui/src/hooks/useStrategies.ts (query hook pattern)
- argus/ui/src/hooks/useControls.ts (mutation hook pattern)
- argus/ui/src/stores/patternLibraryUI.ts (Zustand store pattern)
- argus/ui/src/pages/OrchestratorPage.tsx (page structure pattern)
- argus/ui/src/layouts/Sidebar.tsx (nav + keyboard shortcuts)
- argus/ui/src/layouts/MobileNav.tsx (mobile nav)
- argus/ui/src/App.tsx (routing)
- argus/ui/src/components/SegmentedTab.tsx (tab component for page sections)

TASK 1: Add types to argus/ui/src/api/types.ts

Add these interfaces at the end of the file:

Briefing, BriefingsListResponse, ResearchDocument (with source + is_editable fields), DocumentsListResponse, JournalEntry (with entry_type as union type, linked_trade_ids as string[], tags as string[]), JournalEntriesListResponse, JournalTagsResponse, DebriefSearchResponse.

See the implementation spec for exact field definitions.

TASK 2: Add API client functions to argus/ui/src/api/client.ts

Add functions for all debrief endpoints. All use fetchWithAuth. Prefix: /debrief/

Briefings: fetchBriefings(params?), fetchBriefing(id), createBriefing(data), updateBriefing(id, data), deleteBriefing(id)
Documents: fetchDocuments(category?), fetchDocument(id), createDocument(data), updateDocument(id, data), deleteDocument(id), fetchDocumentTags()
Journal: fetchJournalEntries(params?), fetchJournalEntry(id), createJournalEntry(data), updateJournalEntry(id, data), deleteJournalEntry(id), fetchJournalTags()
Search: fetchDebriefSearch(query, scope?)

TASK 3: Create TanStack Query hooks

Create 4 hook files in argus/ui/src/hooks/:

useBriefings.ts:
- useBriefings(filters?) — useQuery, queryKey ['briefings', filters], 30s refetchInterval
- useBriefing(id) — useQuery, queryKey ['briefing', id], enabled: !!id
- useCreateBriefing() — useMutation, onSuccess invalidates ['briefings']
- useUpdateBriefing() — useMutation, onSuccess invalidates ['briefings'] and ['briefing', variables.id]
- useDeleteBriefing() — useMutation, onSuccess invalidates ['briefings']

useDocuments.ts:
- useDocuments(category?) — useQuery, queryKey ['documents', category], 60s refetchInterval
- useDocument(id) — useQuery, queryKey ['document', id], enabled: !!id
- useCreateDocument() — useMutation, onSuccess invalidates ['documents']
- useUpdateDocument() — useMutation, onSuccess invalidates ['documents'] and ['document', variables.id]
- useDeleteDocument() — useMutation, onSuccess invalidates ['documents']
- useDocumentTags() — useQuery, queryKey ['document-tags'], staleTime: 5 * 60 * 1000

useJournal.ts:
- useJournalEntries(filters?) — useQuery, queryKey ['journal', filters], 30s refetchInterval
- useJournalEntry(id) — useQuery, queryKey ['journal-entry', id], enabled: !!id
- useCreateJournalEntry() — useMutation with optimistic update pattern, onSuccess invalidates ['journal']
- useUpdateJournalEntry() — useMutation, onSuccess invalidates ['journal'] and ['journal-entry', variables.id]
- useDeleteJournalEntry() — useMutation, onSuccess invalidates ['journal']
- useJournalTags() — useQuery, queryKey ['journal-tags'], staleTime: 5 * 60 * 1000

useDebriefSearch.ts:
- useDebriefSearch(query, scope?) — useQuery, queryKey ['debrief-search', query, scope], enabled: query.length >= 2, staleTime: 30s

Export all from argus/ui/src/hooks/index.ts.

TASK 4: Create Zustand store argus/ui/src/stores/debriefUI.ts

State:
- activeSection: 'briefings' | 'research' | 'journal' (default 'briefings')
- editingBriefingId: string | null
- readingBriefingId: string | null
- researchCategoryFilter: string | null
- editingDocumentId: string | null
- readingDocumentId: string | null
- journalDraftExpanded: boolean (default false)
- editingJournalEntryId: string | null
- journalFilters: { type: string | null, strategy_id: string | null, tag: string | null, search: string }

Actions: setActiveSection, setEditingBriefingId, setReadingBriefingId, setResearchCategoryFilter, setEditingDocumentId, setReadingDocumentId, setJournalDraftExpanded, setEditingJournalEntryId, setJournalFilter(key, value), clearJournalFilters

TASK 5: Create DebriefPage shell

Create argus/ui/src/pages/DebriefPage.tsx:
- Header: "The Debrief" title with GraduationCap icon
- SegmentedTab with 3 segments: Briefings, Research, Journal (use layoutId='debrief-tabs')
- Renders placeholder div per tab based on activeSection from Zustand store
- Wrapped in Framer Motion page transition (match other pages)

Create argus/ui/src/features/debrief/DebriefSkeleton.tsx:
- Three skeleton variants (one per tab)
- Follow existing skeleton patterns (pulsing rectangles)

Create argus/ui/src/features/debrief/index.ts:
- Barrel export (empty for now, will grow in later sessions)

TASK 6: Navigation update

Sidebar.tsx:
- Import GraduationCap from lucide-react
- Add nav item: { to: '/debrief', icon: GraduationCap, label: 'The Debrief' } — position after Orchestrator (index 5), before System (now index 6)
- Keyboard shortcuts automatically extend to 1-7 (NAV_ITEMS.length)

MobileNav.tsx:
- Add matching nav item: { to: '/debrief', icon: GraduationCap, label: 'Debrief' }
- Reduce font size to text-[8px] if 7 items overflow (test visually)

App.tsx:
- Import DebriefPage
- Add route: <Route path="/debrief" element={<DebriefPage />} />

DEFINITION OF DONE:
- Navigating to /debrief shows the page shell with 3-segment tabs
- All 7 nav items visible in sidebar and mobile nav
- Keyboard shortcuts 1-7 work
- Tab switching works (content area shows placeholder per tab)
- Skeleton loading component exists
- All hooks compile without errors
- Dev mode (npm run dev + python -m argus.api --dev) shows the page
- No TypeScript errors, no lint warnings
```

### Session 5: Briefings Tab

```
ARGUS Sprint 21c — Session 5: Briefings Tab

CONTEXT: Frontend scaffold is in place (Session 4). This session builds the complete Briefings tab: list view, card component, creation flow, full editor, and reading via DocumentModal.

REFERENCE FILES (read these first):
- argus/ui/src/features/patterns/PatternCard.tsx (card design pattern)
- argus/ui/src/features/orchestrator/DecisionTimeline.tsx (list/feed pattern)
- argus/ui/src/components/DocumentModal.tsx (reuse for reading briefings)
- argus/ui/src/components/MarkdownRenderer.tsx (reuse for preview)
- argus/ui/src/components/Badge.tsx (reuse for type/status badges)
- argus/ui/src/components/ConfirmModal.tsx (reuse for delete confirmation)
- argus/ui/src/stores/debriefUI.ts (state management)
- argus/ui/src/hooks/useBriefings.ts (data fetching)

TASK 1: Create argus/ui/src/features/debrief/briefings/BriefingCard.tsx

Props: briefing (Briefing type), onEdit () => void, onRead () => void, onDelete () => void

Layout:
- Card with subtle border, hover lift (desktop only)
- Top row: date (formatted), type badge (pre_market=blue, eod=amber), status badge (draft=gray, final=green, ai_generated=purple)
- Title (text-base font-semibold)
- Content preview (2-line clamp, text-sm text-argus-text-dim)
- Bottom row: word count, reading time, author, and action icons (read=BookOpen, edit=Pencil, delete=Trash2)
- Click card body → onRead. Explicit buttons for edit/delete.

TASK 2: Create argus/ui/src/features/debrief/briefings/BriefingEditor.tsx

Props: briefingId (string — editing existing) OR isNew (boolean) with initialType ('pre_market' | 'eod'), onClose () => void

This replaces the list view when active (not a modal). Layout:
- Header: "Edit Briefing" or "New Briefing" with back arrow button → onClose
- Title input (text-lg, full width)
- Status selector: SegmentedTab with draft/final (size='sm')
- Two-panel below on desktop (≥1024px): left=textarea, right=MarkdownRenderer preview. Stacked on mobile with toggle button.
- Textarea: monospace font, min-h-[400px], full width, dark bg-argus-surface-2
- Footer: Cancel button, Save button (primary). Show "Unsaved changes" indicator if content differs from server state.

Behavior:
- On mount, fetch briefing via useBriefing(briefingId) if editing
- Track local state for title, content, status
- Save calls useUpdateBriefing mutation
- On save success, close editor

TASK 3: Create argus/ui/src/features/debrief/briefings/BriefingList.tsx

Layout:
- Header row: "Briefings" label + "New Briefing" dropdown button
- Dropdown has two options: "Pre-Market Briefing" and "End of Day Review"
- Clicking creates briefing via useCreateBriefing (template generated server-side), then opens BriefingEditor for the new briefing
- Below: reverse-chronological list of BriefingCards
- When editingBriefingId is set in Zustand, render BriefingEditor instead of the list

Data: useBriefings() hook. Loading → DebriefSkeleton. Empty → EmptyState with "No briefings yet. Create your first one!"

Reading: When readingBriefingId is set, render DocumentModal with the briefing content. Adapt DocumentModal's StrategyDocument interface — pass {title, content, word_count, reading_time_min, last_modified: updated_at}.

Delete: ConfirmModal (variant='danger'), on confirm calls useDeleteBriefing.

TASK 4: Wire into DebriefPage

Update DebriefPage.tsx to render BriefingList when activeSection === 'briefings'.

TASK 5: Update barrel exports

Update argus/ui/src/features/debrief/index.ts to export all briefing components.

DEFINITION OF DONE:
- Briefings tab shows list of briefings from dev mode API
- "New Briefing" creates a templated briefing and opens editor
- Editor has title input, markdown textarea, preview panel, status selector, save/cancel
- Clicking a briefing card opens DocumentModal for reading
- Edit icon opens BriefingEditor
- Delete icon shows confirmation modal then removes briefing
- Responsive layout works at all breakpoints
- Dev mode shows 5 mock briefings
```

### Session 6: Research Library Tab

```
ARGUS Sprint 21c — Session 6: Research Library Tab

CONTEXT: Briefings tab is complete (Session 5). This session builds the Research Library tab with hybrid filesystem + database document support, full CRUD for database docs, categories, and tag management.

REFERENCE FILES (read these first):
- argus/ui/src/features/patterns/PatternCardGrid.tsx (grid layout pattern)
- argus/ui/src/features/debrief/briefings/BriefingEditor.tsx (editor pattern you just built)
- argus/ui/src/components/DocumentModal.tsx (reuse for reading)
- argus/ui/src/components/SegmentedTab.tsx (reuse for category filter)
- argus/ui/src/stores/debriefUI.ts (state management)
- argus/ui/src/hooks/useDocuments.ts (data fetching)

TASK 1: Create argus/ui/src/features/debrief/research/ResearchDocCard.tsx

Props: document (ResearchDocument type), onRead, onEdit?, onDelete?

Layout:
- Card with border, hover lift (desktop)
- Category badge (research=blue, strategy=green, backtest=amber, ai_report=purple)
- Source badge: filesystem=gray outline "Repo", database=blue outline "Custom" — small, top-right
- Title (text-base font-semibold)
- Tags as small rounded pills (if any)
- Bottom: word count, reading time
- Edit/delete icons only if is_editable=true
- Click card body → onRead

TASK 2: Create argus/ui/src/features/debrief/research/DocumentEditor.tsx

For creating and editing database documents. Uses SlideInPanel or replaces list view (match BriefingEditor pattern — replaces view).

Props: documentId (string | null — null for create), onClose () => void

Layout:
- Header: "New Document" or "Edit Document" + back arrow
- Title input
- Category dropdown (research, strategy, backtest, ai_report)
- Content textarea with preview toggle (same as BriefingEditor)
- Tag input section — use JournalTagInput component (build in Session 7, or build a shared TagInput here)

Actually: Build a shared TagInput component here that both Research and Journal will use.

Create argus/ui/src/components/TagInput.tsx:
- Props: tags (string[]), onChange (tags: string[]) => void, suggestions (string[]), placeholder?
- Text input. On type, filter suggestions that include the typed text (case-insensitive). Show dropdown below with matches.
- Press Enter or click suggestion → add tag to list (if not already present)
- Tags display as removable chips above/below the input
- Chip: text + X button to remove
- Style: chips in flex-wrap, input below

TASK 3: Create argus/ui/src/features/debrief/research/ResearchLibrary.tsx

Layout:
- Header: "Research Library" + "Add Document" button (opens DocumentEditor in create mode)
- Category filter: SegmentedTab with segments: All, Research, Strategy, Backtest, AI Reports. Use researchCategoryFilter from Zustand.
- Grid of ResearchDocCards (2 cols on desktop, 1 on tablet/mobile)
- Click card → read in DocumentModal. Adapt interface for ResearchDocument.
- Edit icon on editable cards → open DocumentEditor with documentId
- Delete icon on editable cards → ConfirmModal → useDeleteDocument

Data: useDocuments(category) hook. Pass category filter.

TASK 4: Wire into DebriefPage

Render ResearchLibrary when activeSection === 'research'.

TASK 5: Update exports

Update barrel exports in debrief/index.ts and components/index if TagInput is shared.

DEFINITION OF DONE:
- Research Library shows filesystem docs from repo + database docs from mock data
- Category filter works
- "Add Document" creates a new database document
- Editing database docs works (title, category, content, tags)
- Filesystem docs are read-only (no edit/delete icons)
- TagInput component works with autocomplete suggestions
- DocumentModal opens for reading
- Responsive grid layout
- Dev mode shows filesystem docs + 3 mock database docs
```

### Session 7: Journal Tab

```
ARGUS Sprint 21c — Session 7: Journal Tab (List + Create + Filter)

CONTEXT: Briefings and Research Library are complete (Sessions 5-6). This session builds the Journal tab with inline entry creation, type badges, tag management, and comprehensive filtering.

REFERENCE FILES (read these first):
- argus/ui/src/features/debrief/briefings/BriefingList.tsx (list pattern you built)
- argus/ui/src/components/TagInput.tsx (tag component from Session 6)
- argus/ui/src/components/Badge.tsx (for type badges)
- argus/ui/src/stores/debriefUI.ts (journal state)
- argus/ui/src/hooks/useJournal.ts (data fetching)
- argus/ui/src/hooks/useStrategies.ts (for strategy dropdown options)

TASK 1: Create argus/ui/src/features/debrief/journal/JournalTagInput.tsx

Thin wrapper around TagInput that provides journal-specific suggestions via useJournalTags() hook.

Props: tags (string[]), onChange (tags: string[]) => void

Internally calls useJournalTags() to get suggestions, passes to TagInput.

TASK 2: Create argus/ui/src/features/debrief/journal/JournalEntryForm.tsx

Two modes controlled by journalDraftExpanded in Zustand:

Collapsed (default):
- Single-line text input with placeholder "What did you observe today?"
- Click or focus → expands (sets journalDraftExpanded = true)

Expanded:
- Title input (text-sm, placeholder "Title (brief summary)")
- Content textarea (min-h-[120px], placeholder "Write your observation...")
- Type selector: 4 styled radio buttons in a row. observation (blue, Eye icon), trade_annotation (green, Target icon), pattern_note (amber, Lightbulb icon), system_note (gray, Settings icon). Default: observation.
- Strategy link: dropdown with strategy options from useStrategies(). Optional.
- Tags: JournalTagInput component
- [Trade linking section placeholder — Session 8 adds TradeSearchInput here]
- Buttons: Cancel (collapses form, clears state), Save (calls useCreateJournalEntry)

On save success: collapse form, clear all fields, show brief success toast or flash.

Also accepts pre-fill props for edit mode (Session 8): initialData?: JournalEntry, onSave?: (data) => void, onCancel?: () => void. When initialData is provided, form starts expanded with pre-filled values and uses useUpdateJournalEntry instead.

TASK 3: Create argus/ui/src/features/debrief/journal/JournalEntryCard.tsx

Props: entry (JournalEntry), onEdit () => void, onDelete () => void

Layout:
- Type badge: observation=blue w/ Eye icon, trade_annotation=green w/ Target, pattern_note=amber w/ Lightbulb, system_note=gray w/ Settings
- Title (text-base font-semibold) — if empty, show first 60 chars of content
- Content preview (2-line clamp, text-sm text-argus-text-dim)
- Tags as small rounded pills
- If linked_trade_ids.length > 0: badge showing "{n} linked trades" (clickable, but linking display is Session 8)
- If linked_strategy_id: show strategy badge
- Timestamp: relative time ("2 hours ago", "3 days ago") using simple formatter
- Action icons: edit (Pencil), delete (Trash2)

TASK 4: Create argus/ui/src/features/debrief/journal/JournalList.tsx

Layout:
- JournalEntryForm at top (collapsed by default)
- Filter row below form:
  - Type dropdown: All Types, Observation, Trade Annotation, Pattern Note, System Note
  - Strategy dropdown: All Strategies, + options from useStrategies()
  - Tag dropdown: All Tags, + options from useJournalTags()
  - Search input (text, debounced 300ms)
  - "Clear filters" link (visible when any filter is active)
- Entry count: "Showing {n} of {total} entries"
- Reverse-chronological list of JournalEntryCards
- Delete: ConfirmModal, calls useDeleteJournalEntry

Data: useJournalEntries(filters) where filters come from Zustand journalFilters. Loading → skeleton. Empty → EmptyState "No journal entries yet. Start capturing your observations!"

TASK 5: Wire into DebriefPage

Render JournalList when activeSection === 'journal'.

DEFINITION OF DONE:
- Journal tab shows list of entries from dev mode API
- Inline creation form expands/collapses
- All 4 entry types can be created with proper badges
- Tags work with autocomplete
- All 4 filter dimensions work (type, strategy, tag, search)
- Clear filters resets all
- Delete works with confirmation
- Responsive layout
- Dev mode shows 10 mock entries
```

### Session 8: Journal Enhancements (Inline Edit + Trade Linking)

```
ARGUS Sprint 21c — Session 8: Journal Enhancements (Inline Edit + Trade Linking)

CONTEXT: Journal tab is functional (Session 7). This session adds inline editing (click to edit) and the trade search/linking feature.

REFERENCE FILES (read these first):
- argus/ui/src/features/debrief/journal/JournalEntryForm.tsx (extend for edit mode)
- argus/ui/src/features/debrief/journal/JournalEntryCard.tsx (add edit state)
- argus/ui/src/features/trades/TradeTable.tsx (trade display patterns)
- argus/ui/src/hooks/useJournal.ts (mutations)
- argus/ui/src/api/client.ts (getTrades function)
- argus/ui/src/stores/debriefUI.ts (editingJournalEntryId state)
- argus/ui/src/stores/symbolDetailUI.ts (for opening TradeDetailPanel from linked trades)

TASK 1: Create argus/ui/src/features/debrief/journal/TradeSearchInput.tsx

Component for searching and linking trades to journal entries.

Props: linkedTradeIds (string[]), onChange (ids: string[]) => void

Layout:
- Text input with Search icon, placeholder "Search trades by symbol..."
- On type (debounced 300ms), call getTrades({ symbol: query, limit: 10 })
- Dropdown below input showing matching trades:
  - Each row: symbol (bold), date, strategy badge, P&L colored, side
  - Click row → add trade ID to linkedTradeIds (if not already present)
  - Dropdown closes after selection
- Below input: linked trades displayed as removable chips
  - Each chip: symbol + date (compact format) + X to remove
  - Click chip body (not X) → opens TradeDetailPanel via symbolDetailUI store

State: local searchQuery, local isDropdownOpen, trades from API query.

TASK 2: Update JournalEntryForm for edit mode

The form already accepts initialData prop (from Session 7). Ensure:
- When initialData is provided, pre-fill all fields including linked_trade_ids
- TradeSearchInput is rendered in the form (below tags section)
- Label: "Linked Trades" with TradeSearchInput
- On save with initialData, call useUpdateJournalEntry instead of useCreateJournalEntry
- On save success, call onCancel (which closes edit mode)

TASK 3: Update JournalEntryCard for inline edit

When editingJournalEntryId matches this entry's ID:
- Instead of rendering the card content, render JournalEntryForm with:
  - initialData={entry}
  - onSave → setEditingJournalEntryId(null)
  - onCancel → setEditingJournalEntryId(null)
- Smooth transition (Framer Motion layoutId or AnimatePresence)

The edit button (Pencil icon) onClick → setEditingJournalEntryId(entry.id)

TASK 4: Enhance JournalEntryCard linked trades display

When entry.linked_trade_ids.length > 0:
- Show "Linked Trades" section below content
- Display each linked trade ID as a small clickable chip
- For now, chips show abbreviated ID (first 8 chars) — full trade resolution requires fetching
- Click chip → open TradeDetailPanel (if trade data is available)
- Alternative simpler approach: show "{n} linked trade(s)" as a badge that's clickable. On click, you could open a small popover or just note the IDs.

Pick the simpler approach that looks good. The key deliverable is that trade IDs are stored and displayed, and the search/link workflow works.

TASK 5: Update JournalList

The list already renders JournalEntryCards. Update the edit flow:
- When editingJournalEntryId is set, the corresponding card renders in edit mode
- Only one entry can be edited at a time
- Starting to edit one entry closes any other editing entry

DEFINITION OF DONE:
- Click edit on a journal entry → card transforms into pre-filled form
- Form includes trade search input
- Search finds trades by symbol, shows dropdown with matches
- Selecting a trade links it (adds ID to linked_trade_ids)
- Linked trades shown as removable chips
- Save updates the entry with new linked trades
- Cancel exits edit mode, restoring card view
- Smooth transitions between card and edit modes
```

### Session 9: Polish + Responsive + Animations

```
ARGUS Sprint 21c — Session 9: Polish, Responsive, and Animations

CONTEXT: All features are built (Sessions 4-8). This session adds the UX polish layer: responsive refinements, skeleton loading, Framer Motion animations, empty states, and keyboard shortcuts.

REFERENCE FILES (read these first):
- argus/ui/src/utils/motion.ts (DURATION, EASE constants)
- argus/ui/src/features/patterns/ (stagger animation patterns from Sprint 21a)
- argus/ui/src/features/orchestrator/OrchestratorSkeleton.tsx (skeleton pattern)
- argus/ui/src/components/EmptyState.tsx (empty state component)
- argus/ui/src/layouts/Sidebar.tsx (keyboard shortcut pattern)

TASK 1: Skeleton Loading States

Update DebriefSkeleton.tsx with three variants:

BriefingSkeleton: 3-4 card-shaped pulsing rectangles stacked vertically
ResearchSkeleton: 2x3 grid of card-shaped rectangles
JournalSkeleton: Input bar + 4-5 card-shaped rectangles

Each page section should show its skeleton while data is loading (isLoading from hooks).

TASK 2: Framer Motion Animations

BriefingList: Stagger animation on cards (staggerChildren: 0.05, y: 10 → 0, opacity 0 → 1)
ResearchLibrary: Grid items stagger
JournalList: Entry cards stagger
BriefingEditor: Slide in from right or fade
DocumentEditor: Same as BriefingEditor
Tab transitions: AnimatePresence with mode="wait" on the tab content area in DebriefPage

Respect DURATION.fast and DURATION.normal from motion.ts. Never block interaction.

TASK 3: Empty States

Each tab gets a contextual empty state:
- Briefings: BookOpen icon, "No briefings yet", "Create your first pre-market briefing to start building your trading journal."
- Research: FolderOpen icon, "No documents found", "Your research documents will appear here. Add a document to get started."
- Research (with filter): Filter icon, "No documents in this category"
- Journal: Pencil icon, "No journal entries yet", "Start capturing your observations, trade annotations, and pattern notes."
- Journal (with filters): Filter icon, "No entries match your filters", + "Clear filters" button

TASK 4: Responsive Refinements

Test and fix all 3 breakpoints:

Phone (<640px):
- SegmentedTab full width
- BriefingEditor: single column (no side-by-side preview), preview toggle button
- ResearchLibrary: single column grid
- JournalEntryForm: stack all fields vertically
- Filter row: wrap to 2x2 grid or horizontal scroll

Tablet (640-1023px):
- BriefingEditor: single column with preview toggle
- ResearchLibrary: 2-column grid
- Filter row: single row with smaller inputs

Desktop (≥1024px):
- BriefingEditor: side-by-side textarea + preview
- ResearchLibrary: 2-3 column grid
- Everything at full width in main content area

Mobile nav: Verify 7 items fit. If text overflows, reduce to text-[8px] or abbreviate "Debrief" to "Brief".

TASK 5: Keyboard Shortcuts

In DebriefPage, add keyboard handler (same pattern as PatternLibrary arrow keys):
- 'b' key → switch to Briefings tab
- 'r' key → switch to Research tab  
- 'j' key → switch to Journal tab
- 'n' key → start new entry (Briefings: open create dropdown, Journal: expand form)
- Escape → close editor/form

All suppressed when input/textarea is focused.

TASK 6: Markdown Preview Toggle

In BriefingEditor and DocumentEditor, add a clean toggle:
- Two small buttons/icons: "Write" (code icon) and "Preview" (eye icon)
- Or a SegmentedTab (size='sm') with Write/Preview
- Write mode: show textarea
- Preview mode: show MarkdownRenderer
- Desktop: show both side by side (no toggle needed)

DEFINITION OF DONE:
- All loading states show appropriate skeletons
- Card animations are smooth and don't block interaction
- Tab transitions are smooth
- All empty states display correctly
- Responsive layout works at all 3 breakpoints
- Keyboard shortcuts work
- Preview toggle works in editors
- 7-item mobile nav displays correctly
- No visual regressions on existing pages
```

### Session 10: Tests + Final Cleanup

```
ARGUS Sprint 21c — Session 10: Vitest + Cleanup + Review Prep

CONTEXT: All features and polish are complete (Sessions 4-9). This session adds Vitest component tests, fills any pytest gaps, and prepares for code review.

REFERENCE FILES (read these first):
- argus/ui/src/features/orchestrator/SessionOverview.test.tsx (Vitest pattern)
- argus/ui/src/features/patterns/PatternCard.test.tsx (component test pattern)
- argus/ui/src/features/patterns/IncubatorPipeline.test.tsx (another test pattern)

TASK 1: Create Vitest component tests

Create tests in argus/ui/src/features/debrief/__tests__/:

BriefingCard.test.tsx (~4 tests):
- renders briefing title and content preview
- shows correct type badge (pre_market vs eod)
- shows correct status badge
- calls onRead when card body clicked

BriefingEditor.test.tsx (~4 tests):
- renders title input and content textarea
- shows preview toggle
- renders status selector
- calls save with updated content (mock mutation)

ResearchDocCard.test.tsx (~4 tests):
- renders document title and category badge
- shows tags
- shows edit/delete only for editable docs
- hides edit/delete for filesystem docs

JournalEntryCard.test.tsx (~4 tests):
- renders entry type badge correctly for each type
- shows title and content preview
- displays tags
- shows linked trade count badge

JournalEntryForm.test.tsx (~5 tests):
- starts collapsed with placeholder input
- expands on click/focus
- shows type selector when expanded
- renders tag input
- collapses on cancel

JournalTagInput.test.tsx (~3 tests):
- renders with existing tags as chips
- removes tag when X clicked
- shows input field

TradeSearchInput.test.tsx (~3 tests):
- renders search input
- shows linked trades as chips
- removes linked trade when X clicked

Total: ~27 Vitest tests

Run: cd argus/ui && npx vitest run

TASK 2: Fill pytest gaps

Run existing tests to ensure nothing broke:
pytest tests/ -x --tb=short -q

If any gaps in Session 3 tests, fill them:
- Verify search endpoint tests
- Verify edge cases (empty content, very long content, special characters in tags)
- Verify document discovery with no docs/ directory

TASK 3: Code cleanup

- Remove any TODO comments that were resolved
- Ensure all files have proper docstrings/comments
- Verify all imports are clean (no unused)
- Run: cd argus/ui && npx tsc --noEmit (zero TypeScript errors)
- Run: ruff check argus/ (zero lint errors)
- Run: cd argus/ui && npx vitest run (all pass)
- Run: pytest tests/ -x --tb=short (all pass)

TASK 4: Verify dev mode

Start dev server: python -m argus.api --dev
Start frontend: cd argus/ui && npm run dev

Verify on all 3 tabs:
- Briefings: 5 mock briefings visible, create/edit/read/delete work
- Research: filesystem + database docs visible, categories filter, CRUD on DB docs
- Journal: 10 mock entries visible, create/edit/delete work, tags, trade linking

TASK 5: Generate test count summary

Run: pytest tests/ --co -q | tail -5
Run: cd argus/ui && npx vitest run 2>&1 | tail -10

Report final counts for code review handoff.

DEFINITION OF DONE:
- ~30 new Vitest tests all passing
- All existing pytest tests still passing (no regressions)
- Zero TypeScript errors
- Zero ruff lint errors  
- Dev mode fully functional with all 3 tabs
- Ready for Code Review 2
```

---

## Part 4: Code Review Plan

### Review Cadence: 2 Reviews

| Review | After | Focus | Materials Needed |
|--------|-------|-------|-----------------|
| CR1 | Session 3 | Backend (schema, service, API, tests, mock data) | Test output, API route list |
| CR2 | Session 10 | Full sprint (all frontend, polish, tests) | Test output, screenshot set, running dev server |

### Code Review Procedure

**For each review:**

1. **Steven commits all current work to git** — `git add -A && git commit -m "sprint-21c: [checkpoint description]"`

2. **Steven opens a new Claude.ai conversation** in the ARGUS project and pastes the handoff brief (Part 5 below)

3. **Claude reviews by reading the GitHub repo** — no transcript upload needed. Claude reads the actual code via the repo.

4. **Review focuses on:**
   - Spec compliance (does the code match the implementation spec?)
   - Architectural consistency (patterns match existing codebase?)
   - Test coverage (are critical paths tested?)
   - Edge cases (error handling, empty states, null checks)
   - Responsive design (CR2 only — screenshots)
   - Integration points (does everything wire together correctly?)

5. **Review output:** List of findings categorized as:
   - 🔴 Must fix (blocks sprint completion)
   - 🟡 Should fix (quality issue, fix in polish session)
   - 🟢 Nice to have (defer or skip)
   - New DEC entries if architectural decisions were made during implementation

6. **After review:** Steven relays findings to Claude Code for a fix session if needed.

### When to Update Documents

**After CR2 (final review):**
- Decision Log: Any new DEC entries from implementation decisions
- Project Knowledge: Update sprint status, test counts, Build Track queue
- Sprint Plan: Move Sprint 21c to completed, update test totals
- CLAUDE.md: Update current state

**Steven should NOT update docs between sessions** — wait for final review to batch all updates.

---

## Part 5: Code Review Handoff Briefs

### CR1 Handoff Brief (After Session 3)

```
ARGUS Sprint 21c — Code Review 1 (Backend)

I've completed Sessions 1-3 of Sprint 21c (The Debrief page). Please review the backend implementation.

WHAT WAS BUILT:
- Database schema: 3 new tables (briefings, updated journal_entries, documents) in schema.sql
- DebriefService: Full CRUD for all 3 content types, template generation, filesystem document discovery, LIKE-based search
- API routes: 4 new route files (briefings.py, documents.py, journal.py, debrief_search.py) under /debrief prefix
- AppState updated with debrief_service field
- Dev mode mock data: 5 briefings, 3 database documents, 10 journal entries
- Pytest tests: ~50 new tests covering service layer and all API endpoints

REVIEW SCOPE:
1. Read argus/db/schema.sql — check the 3 new table definitions at the bottom
2. Read argus/analytics/debrief_service.py — full service layer
3. Read argus/api/routes/briefings.py, documents.py, journal.py, debrief_search.py — all API routes
4. Read argus/api/dependencies.py — AppState update
5. Read argus/api/routes/__init__.py — router registration
6. Read argus/api/dev_state.py — mock data additions (search for "debrief" or "briefing" or "journal")
7. Read tests/analytics/test_debrief_service.py and tests/api/test_debrief_api.py

REVIEW CHECKLIST:
- [ ] Schema matches spec (correct columns, types, constraints, indexes)
- [ ] DebriefService methods match spec (signatures, behavior, error handling)
- [ ] API routes match spec (endpoints, HTTP methods, Pydantic models, status codes)
- [ ] Filesystem document discovery works correctly (path handling, category inference)
- [ ] LIKE search implementation is correct (SQL injection safe via parameterized queries)
- [ ] JSON fields stored/parsed correctly (tags, linked_trade_ids, metadata)
- [ ] Template generation produces useful markdown structure
- [ ] Mock data is realistic and covers all content types
- [ ] Test coverage is adequate (critical paths, edge cases, error cases)
- [ ] No regressions on existing tests

Please run: pytest tests/ -x --tb=short -q (if you have access)

Flag any issues as 🔴 must-fix, 🟡 should-fix, or 🟢 nice-to-have.
```

### CR2 Handoff Brief (After Session 10)

```
ARGUS Sprint 21c — Code Review 2 (Full Sprint)

I've completed all 10 sessions of Sprint 21c (The Debrief page). Please review the complete implementation.

WHAT WAS BUILT:
Backend (reviewed in CR1):
- DebriefService, 3 DB tables, 4 API route files, ~50 pytest tests, dev mock data

Frontend (new since CR1):
- DebriefPage with 3-section SegmentedTab (Briefings / Research / Journal)
- Briefings tab: BriefingList, BriefingCard, BriefingEditor (full markdown editing with preview)
- Research Library tab: ResearchLibrary, ResearchDocCard, DocumentEditor, hybrid filesystem+database docs, category filter, tag management
- Journal tab: JournalList, JournalEntryCard, JournalEntryForm (collapsed→expanded inline creation), JournalTagInput (autocomplete), TradeSearchInput (search and link trades)
- Journal inline editing (click edit → card transforms to pre-filled form)
- Shared TagInput component
- Navigation: 7th page (GraduationCap icon), keyboard shortcuts 1-7, mobile nav updated
- Polish: skeleton loading, Framer Motion animations, responsive at all breakpoints, empty states, keyboard shortcuts (b/r/j for tab switching, n for new, Escape to close)
- ~30 new Vitest component tests

REVIEW SCOPE:
1. Frontend components in argus/ui/src/features/debrief/ (all files)
2. Shared components: argus/ui/src/components/TagInput.tsx
3. Types/hooks/stores: types.ts additions, client.ts additions, hooks/useBriefings.ts + useDocuments.ts + useJournal.ts + useDebriefSearch.ts, stores/debriefUI.ts
4. Pages: argus/ui/src/pages/DebriefPage.tsx
5. Nav: Sidebar.tsx, MobileNav.tsx changes
6. Routes: App.tsx changes
7. Tests: argus/ui/src/features/debrief/__tests__/ (all test files)

REVIEW CHECKLIST:
- [ ] All 3 tabs functional with correct data display
- [ ] Briefing create/read/edit/delete flow works
- [ ] Research Library shows both filesystem and database docs correctly
- [ ] Database doc CRUD works (create, edit, delete)
- [ ] Filesystem docs are read-only (edit/delete disabled)
- [ ] Journal entry create/edit/delete flow works
- [ ] Tag autocomplete works on journal entries and documents
- [ ] Trade search and linking works in journal entries
- [ ] Inline journal editing (card → form transformation) works
- [ ] DocumentModal reading works for both briefings and research docs
- [ ] Navigation: 7 items in sidebar and mobile nav, keyboard shortcuts 1-7
- [ ] Responsive: phone (<640px), tablet (640-1023px), desktop (≥1024px)
- [ ] Skeleton loading states on all tabs
- [ ] Animations are smooth, <500ms, don't block interaction
- [ ] Empty states display correctly
- [ ] All Vitest tests pass
- [ ] All pytest tests still pass
- [ ] Zero TypeScript errors, zero ruff lint errors
- [ ] z-index layering correct (no overlap issues)
- [ ] Badge colors follow established color scheme

Test counts (expected):
- pytest: ~1608 total (~50 new)
- Vitest: ~130 total (~30 new)

Flag any issues as 🔴 must-fix, 🟡 should-fix, or 🟢 nice-to-have.
Draft any new DEC entries for decisions made during implementation.
Draft doc updates for Project Knowledge and Sprint Plan.
```

---

## Part 6: Doc Updates to Make Now

### Decision Log Entries

```
### DEC-196 | Journal Entry Types — Updated
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Journal entry_type values updated from original schema ('observation', 'analysis', 'decision', 'insight') to ('observation', 'trade_annotation', 'pattern_note', 'system_note'). Schema DROP + recreate since table was never populated. |
| **Rationale** | New types better reflect actual usage patterns: observations for general notes, trade annotations for per-trade learning, pattern notes for strategy refinement, system notes for platform/infrastructure observations. |
| **Status** | Active |

### DEC-197 | Briefings Table Schema
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | New `briefings` table with UNIQUE(date, briefing_type) constraint. Two types: pre_market and eod. Three statuses: draft, final, ai_generated. Template-based creation generates markdown section headers server-side. |
| **Rationale** | One briefing per type per day enforces discipline. Template generation ensures consistent structure without requiring users to remember section headers. ai_generated status prepares for Sprint 22 AI Layer. |
| **Status** | Active |

### DEC-198 | Research Library — Hybrid Filesystem + Database Source
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Research Library serves documents from two sources: filesystem (auto-discovered from docs/research/, docs/strategies/, docs/backtesting/) and database (user-created via UI). Filesystem docs are read-only with stable IDs (fs_{category}_{filename}). Database docs support full CRUD with categories and tags. |
| **Rationale** | Repo documentation should be accessible without duplication. Database docs enable user-created research notes and future AI-generated reports. Hybrid approach serves both needs. |
| **Status** | Active |

### DEC-199 | Navigation — 7 Pages
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Command Center expanded to 7 pages: Dashboard, Trade Log, Performance, Pattern Library, Orchestrator, The Debrief, System. GraduationCap icon for Debrief. Keyboard shortcuts 1–7. Mobile nav: Dash/Trades/Perf/Patterns/Orch/Debrief/System. |
| **Rationale** | The Debrief is the 6th functional page (before System). Positioned after Orchestrator because it's the knowledge/review layer accessed after operational monitoring. Mobile labels abbreviated to fit 7 items. |
| **Amends** | DEC-169 (was 6 pages built, now 7 of 7), DEC-180 (shortcuts 1–5 → 1–7), DEC-189 (mobile 6-tab → 7-tab) |
| **Status** | Active |

### DEC-200 | Search — LIKE Queries Over FTS5
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Full-text search across debrief content (briefings, journal, documents) uses comprehensive LIKE queries across title+content+tags columns. FTS5 virtual tables not implemented. |
| **Rationale** | At <1,000 entries, LIKE '%term%' is instant. FTS5 adds virtual table creation, sync triggers on INSERT/UPDATE/DELETE, rebuild commands, different query syntax, and CI compatibility concerns for zero user-visible benefit at current scale. Can be swapped in as a backend optimization if search performance degrades at >10K entries. |
| **Resolves** | DEF-026 (FTS5 deferred → replaced with LIKE search, which is the shipped solution) |
| **Status** | Active |

### DEC-201 | Journal Trade Linking — Full UI in Sprint 21c
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Journal trade linking includes full search UI (TradeSearchInput component) in Sprint 21c. Search trades by symbol, select from dropdown, display linked trades as removable chips. |
| **Rationale** | Trade annotations without trade linking have limited value. The search component (~200 lines) is tractable within sprint scope and completes the journal's core value proposition. |
| **Resolves** | DEF-027 (trade linking UI deferred → now included) |
| **Status** | Active |
```

### DEF Entries to Resolve

DEF-026 (FTS5 search) → Resolved by DEC-200. LIKE search is the shipped solution.
DEF-027 (Journal trade linking UI) → Resolved by DEC-201. Full UI included in Sprint 21c.

### Sprint Plan Update (10_PHASE3_SPRINT_PLAN.md)

Add to Sprint 21c entry:

```
### Sprint 21c — The Debrief Page
**Status:** IN PROGRESS
**Sessions:** 10 implementation + 2 code reviews
**Target tests:** ~50 new pytest + ~30 new Vitest

**Scope:**
- Database schema: briefings, updated journal_entries, documents tables
- DebriefService: full CRUD, template generation, filesystem document discovery, LIKE search
- API: 4 route files under /debrief prefix (~15 endpoints)
- Frontend: DebriefPage with 3-section SegmentedTab
  - Briefings tab: list, cards, creation flow, full markdown editor with preview, DocumentModal reading
  - Research Library: hybrid filesystem + database docs, category filter, CRUD on DB docs, tag management
  - Journal: inline creation, 4 entry types, tag autocomplete, comprehensive filtering, inline editing, trade search and linking
- Navigation: 7th page (GraduationCap), keyboard shortcuts 1-7
- Polish: skeleton loading, Framer Motion animations, responsive, empty states
- Shared TagInput component
- Dev mode mock data: 5 briefings, 3 DB docs, 10 journal entries

**Decisions:** DEC-196 through DEC-201
**Resolved deferrals:** DEF-026 (FTS5 → LIKE search), DEF-027 (trade linking UI included)
```

### Project Knowledge (02) Updates

In "Current Project State > Build Track" after Sprint 21a entry, the Sprint 21b entry should already be there. After that, add Sprint 21c when complete. For now, note in queue:

```
- Sprint 21c (The Debrief page): IN PROGRESS — 7th page, 3 tabs (Briefings, Research Library, Journal), full CRUD, trade linking, ~15 API endpoints, ~50 new pytest + ~30 Vitest.
```

Update DEC-169 to note "**7 of 7 built**" once 21c completes (currently says "6 of 7 built").

---

*End of Sprint 21c Materials*
