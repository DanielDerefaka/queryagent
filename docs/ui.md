# QueryAgent design system and UI/UX blueprint

**QueryAgent should be a dark-mode-first, AI-native analytics platform that combines Meridian's premium SaaS polish with Dune's community-driven query ecosystem — while eliminating the SQL barrier that limits Dune's accessibility.** The design system below synthesizes findings from two inspiration sites, four blockchain analytics competitors, and 2025/2026 best practices into a complete, buildable specification. The core principle: clarity over decoration, with every pixel serving the data.

---

## Inspiration site audit: what to steal and what to skip

### Meridian (trymeridian.com) — design DNA

Meridian is a Webflow-built dark-mode SaaS site with a **premium, data-forward aesthetic** that feels more Linear or Vercel than typical crypto. The site uses a geometric sans-serif (most likely **Inter** or DM Sans based on rendering characteristics) with a clear 5-level type hierarchy: bold H1s at ~48–64px, section H2s, card H3s, body at ~16px, and uppercase labels for category markers. Font weights span 400 (body) to 700 (headlines) with tight letter-spacing on headings.

The color palette is anchored in **deep navy-black backgrounds** (~#0A0A0F to #0D0E14), with elevated card surfaces at ~#14151D to #1A1B25. Primary text is white, secondary text is muted gray (~#8B8D97), and the accent system uses **emerald green for positive metrics** (~#22C55E), red for negative (~#EF4444), and a **blue-purple gradient** as the brand signature. Cards use 12–16px border radius with subtle borders in very dark gray (~#2A2B35). Buttons follow a primary (solid fill with → arrow affordance) and secondary (ghost/outlined) pattern with pill or rounded-rect shapes.

The layout follows a sticky nav → hero with dual CTAs → product demo cards → logo marquee → value prop → how-it-works → case studies → CTA → footer structure. Content sits within a ~1200–1280px max-width. Key animations include **infinite-scroll logo marquees** (CSS-driven with duplicated DOM nodes), scroll-triggered fade-in reveals, and a recurring **3D wireframe orb** as a brand motif. The hero section is particularly strong — showing actual product UI cards with real metrics rather than generic illustrations.

### ZeroDrift (zerodrift.ai) — design DNA

ZeroDrift takes the opposite approach: a **light-mode, enterprise-grade** site built on Webflow with **GSAP + Lottie** for sophisticated animation. It was submitted to Awwwards in February 2026 (scoring ~7.7 average across 15 reviewers) and was designed by Ayoub Kada. The likely font is a modern geometric sans-serif (Inter, Satoshi, or Neue Montreal) with the same weight range as Meridian but deployed on white/cream backgrounds.

The accent color is **warm orange**, delivered via looping MP4 gradient video backgrounds rather than CSS gradients — a technique that creates richer, more organic visual texture. Text is dark/near-black on light backgrounds, with monospaced code blocks (likely JetBrains Mono or Fira Code) for the developer API section. The navigation features **mega-menu dropdowns** with thumbnail previews for each product section — a pattern worth borrowing for QueryAgent's feature navigation.

ZeroDrift's most valuable pattern is its **social proof hierarchy**: a16z badge above the H1 → "Built by AI leaders from" logo ticker (Google, Microsoft, Bloomberg, Goldman Sachs, IBM) → detailed testimonial quote → SOC 2/trust badges. For QueryAgent, this translates to: Bittensor subnet badge → "Powered by X miners across Y chains" → community testimonials → verification proof badges.

**What to steal from each:**

- From Meridian: Dark mode palette, data-rich hero with product UI, metric card patterns (visibility/sentiment scores → query results/miner scores), → arrow CTA convention, 3D brand elements
- From ZeroDrift: Mega-menu navigation, social proof layering, video background accents, tabbed feature showcase (Compose/Guard/Command → Ask/Schedule/Explore), trust badge patterns, GSAP-level animation polish

---

## Competitive landscape: Dune's strengths and the gaps QueryAgent fills

Dune Analytics runs on **Next.js/React/TypeScript deployed on Vercel** — notably similar to QueryAgent's stack. Its default theme is a **warm light palette** with orange as the primary brand color and blue as secondary, defined via CSS custom properties (`--color1-100: var(--orange-100)`). The community has created unofficial "Dark Dune" stylesheets, signaling unmet demand for dark mode.

Dune's query editor provides syntax highlighting with configurable themes, context-aware autocomplete (DuneSQL keywords + table/column names), AI-powered SQL generation ("Edit SQL with prompt"), and GPT-4 query explanation. Results appear in **paginated tables** (25 rows, sortable columns, search filter) with visualization tabs below. Available chart types are limited: bar, area, scatter, line, pie, mixed, counter, and formatted table. The dashboard builder uses a **free-form drag-and-drop grid** with two widget types (visualization and Markdown text).

**Dune's core strengths** that QueryAgent must match: the fork/remix system (every query is public and forkable), Command+K keyboard navigation, embeddable visualizations via iframe, and the community-driven explore/discover page with star ratings. **Dune's weaknesses** that QueryAgent must exploit:

- **SQL barrier**: Dune requires SQL knowledge; QueryAgent eliminates this with plain-English queries
- **Query timeouts**: Free-tier queries frequently time out on complex joins; QueryAgent's decentralized miner network distributes compute
- **Limited visualization**: Only ~7 chart types with basic browser-native color pickers; QueryAgent should ship with 15+ chart types and a modern color system
- **Non-intuitive dashboard builder**: Users must create queries first, then add to dashboards — backwards flow; QueryAgent should support dashboard-first creation
- **No dark mode**: The warm orange theme divides users; QueryAgent launches dark-mode-first
- **No scheduling for free users**: Scheduled refreshes are premium-only; QueryAgent makes recurring queries a core feature
- **No miner transparency**: Dune is a black box; QueryAgent shows which miners answered and their verification scores

**Flipside Crypto** retired its SQL Studio in mid-2025 to go all-in on FlipsideAI — a conversational interface over 35+ chains. This validates QueryAgent's natural-language-first approach but also demonstrates the risk: power users revolted, and Dune published migration guides to capture them. QueryAgent must serve both natural language users and SQL-literate analysts.

**Nansen** excels at pre-built intelligence (500M+ labeled wallets, Token God Mode deep-dive dashboards, Smart Alerts) but charges $99–$999/month and offers no custom SQL. Its **⌘K command palette** and **"God Mode" single-entity dashboard** pattern are worth borrowing. **Footprint Analytics** is built on Metabase v0.45.0 with a drag-and-drop no-code builder — accessible but generic-looking. Its **one-click fork** and **Bronze → Silver → Gold data layer** model are good patterns.

---

## Recommended color palette for QueryAgent

The palette draws from Meridian's dark-mode foundations while adding a distinctive **electric blue-cyan** brand accent that differentiates from Dune's orange and Nansen's blue.

### Core backgrounds
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#09090B` | Page background (zinc-950) |
| `--bg-surface` | `#18181B` | Cards, panels (zinc-900) |
| `--bg-elevated` | `#27272A` | Hover states, active items (zinc-800) |
| `--bg-overlay` | `#3F3F46` | Dropdowns, tooltips (zinc-700) |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#FAFAFA` | Headlines, primary content (zinc-50) |
| `--text-secondary` | `#A1A1AA` | Descriptions, labels (zinc-400) |
| `--text-muted` | `#71717A` | Placeholders, disabled (zinc-500) |

### Brand accent (electric cyan-blue)
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-primary` | `#06B6D4` | Primary CTA, active states (cyan-500) |
| `--accent-hover` | `#22D3EE` | Hover state (cyan-400) |
| `--accent-muted` | `#164E63` | Accent backgrounds (cyan-900) |
| `--accent-subtle` | `#083344` | Accent surface tint (cyan-950) |

### Semantic colors
| Token | Value | Usage |
|-------|-------|-------|
| `--success` | `#22C55E` | Positive metrics, verified (green-500) |
| `--warning` | `#F59E0B` | Pending, caution (amber-500) |
| `--error` | `#EF4444` | Negative metrics, failures (red-500) |
| `--info` | `#3B82F6` | Informational badges (blue-500) |

### Data visualization palette (8-color categorical)
`#06B6D4` (cyan) → `#8B5CF6` (violet) → `#F59E0B` (amber) → `#EC4899` (pink) → `#10B981` (emerald) → `#F97316` (orange) → `#6366F1` (indigo) → `#14B8A6` (teal)

This avoids red-green adjacency for colorblind safety and maintains **3:1+ contrast** against the dark background.

---

## Typography system

**Primary font: Inter** — the consensus choice for data-heavy interfaces in 2025/2026. Its tabular numeral support (`font-variant-numeric: tabular-nums`) ensures columns of numbers align perfectly. Tall x-height and clear glyph differentiation (1/l/I, 0/O) make it ideal for blockchain addresses and hex values.

**Monospace font: JetBrains Mono** — for the SQL editor, query display, blockchain addresses, and transaction hashes. Ligature support and coding-optimized glyphs make it the best choice for code contexts.

### Type scale (using Tailwind's default + custom)

| Level | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| Display | 48px / 3rem | 700 | 1.1 | -0.02em | Landing page hero H1 |
| H1 | 36px / 2.25rem | 700 | 1.2 | -0.02em | Page titles |
| H2 | 24px / 1.5rem | 600 | 1.3 | -0.01em | Section headers |
| H3 | 20px / 1.25rem | 600 | 1.4 | 0 | Card headers, widget titles |
| H4 | 16px / 1rem | 600 | 1.5 | 0 | Sub-sections |
| Body | 15px / 0.9375rem | 400 | 1.6 | 0 | Paragraphs, descriptions |
| Body Small | 14px / 0.875rem | 400 | 1.5 | 0 | Table cells, form labels |
| Caption | 12px / 0.75rem | 500 | 1.4 | 0.02em | Badges, timestamps, metadata |
| Overline | 11px / 0.6875rem | 600 | 1.3 | 0.08em | Uppercase labels, categories |

Set `font-variant-numeric: tabular-nums` globally on any container displaying numbers. For table cells, **14px with 1.5 line-height and 12px/16px padding** provides optimal density.

### Spacing scale
Use Tailwind's 4px base unit: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96`. Card internal padding: **24px** (p-6). Section vertical spacing: **64–96px**. Component gaps: **16px** default, **8px** for compact contexts. Max content width: **1280px** (max-w-7xl) for marketing, **100% fluid** for the app dashboard.

---

## Complete page structure for QueryAgent

### Marketing/public pages

**1. Landing page** (`/`)
Structure: Sticky nav → Hero (H1 + natural language input demo + dual CTAs) → Animated query flow demonstration → Stats bar (miners active, queries answered, chains supported) → Feature grid (3 pillars: Ask, Schedule, Explore) → Community query showcase (live feed of recent queries) → How it works (3-step visual) → Comparison table vs Dune → Testimonials → Pricing tiers → Footer

The hero should feature a **live, interactive query input** — not a static image. Users type a natural language question, see it animate into SQL, and watch results appear. This is QueryAgent's core differentiator and should be the first thing visitors experience.

**2. Explore page** (`/explore`)
Mirrors Dune's discover page but with richer metadata: query cards showing the question asked (plain English), result preview (mini chart/table), miner count, verification score, star count, fork count, and time ago. Filter sidebar: chain, category (DeFi/NFT/L2/bridges), time range, sort by (trending/newest/most-starred). Search bar with autocomplete.

**3. Pricing page** (`/pricing`)
Three tiers in card format: Free (public queries, 10/day), Pro (private queries, scheduling, API access), Team (collaboration, shared dashboards, priority execution). Toggle for monthly/annual. Feature comparison table below.

**4. Docs** (`/docs`)
Left sidebar navigation (like Dune's docs), MDX-powered content, code examples with copy buttons, interactive API playground.

### App/authenticated pages

**5. Dashboard home** (`/dashboard`)
The first screen after login. Layout: persistent left sidebar (collapsible) + top header with search/⌘K + main content area. Content: welcome message with quick-start actions → recent queries (card grid) → saved/favorited queries → trending community queries → usage stats.

**6. Ask page — the core product** (`/dashboard/ask`)
This is QueryAgent's killer page. Layout splits into three zones:

- **Top zone**: Large natural language input bar (like a search engine, not a chat). Placeholder: "Ask any blockchain question..." with suggested queries below. Voice input option. Chain selector dropdown.
- **Middle zone (after query)**: Split panel. Left: Generated SQL with syntax highlighting (Monaco Editor, collapsible — most users won't care about SQL). Right: Miner execution panel showing which miners are working, their scores, and real-time progress.
- **Bottom zone**: Results area with tab switching — Table view (TanStack Table with sort/filter/pagination), Chart view (auto-suggested chart type with manual override), Raw JSON view. Below results: "Add to dashboard" button, "Schedule this query" button, "Share" button, "Fork" button.

**7. Query editor** (`/dashboard/query`)
For power users who want to write SQL directly. Full-screen Monaco Editor with QueryAgent SQL autocomplete, table explorer in left sidebar (searchable by chain/protocol/table), run button (Ctrl+Enter), results panel below. Identical to Dune's editor but with dark theme default, better visualization options, and the ability to switch between SQL and natural language mode.

**8. My dashboards** (`/dashboard/dashboards`)
Grid of dashboard cards with thumbnail previews, last-updated timestamp, query count, and public/private badge. Create new dashboard button → opens dashboard builder.

**9. Dashboard builder** (`/dashboard/dashboards/[id]/edit`)
Grid-based drag-and-drop layout using a **12-column grid** system (not free-form like Dune — structured grids produce better-looking dashboards). Widget palette in right sidebar: chart widget, table widget, KPI counter widget, text/markdown widget, query input widget. Each widget links to a saved query. Resize handles on widget edges. Dashboard-level filters (time range, chain) that propagate to all widgets. Auto-layout "Arrange" button for users who don't want to manually position.

**10. Dashboard view** (`/dashboard/dashboards/[id]`)
Read-only view with "Edit" toggle. All widgets render with real-time data (Convex reactive queries). Click any chart → drill-down to the underlying query and full results. Share button generates public URL or embed iframe. Schedule button for automated refresh.

**11. Schedules** (`/dashboard/schedules`)
List of all recurring queries with columns: query name, frequency (daily/weekly/monthly), next run time, last result preview, status (active/paused/failed). Create new schedule → pick query + frequency + delivery method (in-app, email, webhook).

**12. Profile** (`/dashboard/profile/[username]`)
Public profile showing user's published queries and dashboards, total stars received, queries forked, and miner reputation (if applicable). Activity feed.

**13. Settings** (`/dashboard/settings`)
Account, API keys, notification preferences, connected wallets, billing, team management.

---

## Navigation structure

### Marketing site nav (horizontal top bar)
```
[Logo]  Product  Explore  Pricing  Docs  [Login]  [Get Started →]
```
"Product" dropdown: Ask Questions, Dashboard Builder, Scheduling, API. Mobile: hamburger → slide-in sheet.

### App nav (persistent left sidebar — collapsible to icons)
```
[Q Logo]
──────────
🔍  Ask          ← Primary action, always prominent
📝  Query Editor ← For SQL users  
📊  Dashboards
📅  Schedules
🌐  Explore
──────────
⚙️  Settings
👤  Profile
```

Top header bar: **⌘K command palette** trigger (search queries, dashboards, navigate anywhere), chain selector dropdown, notification bell, user avatar. The command palette is critical — Nansen and Dune both use it, and power users expect it. Implement with shadcn/ui's Command component (built on cmdk).

---

## Key UI components needed

### Component library stack
```
shadcn/ui          → Base primitives (Button, Card, Dialog, Sheet, Tabs, Command, Skeleton, etc.)
Tremor              → Dashboard components (AreaChart, BarChart, DonutChart, KPI Card, SparkChart, Tracker)
TanStack Table v8   → Data tables (sorting, filtering, pagination, row selection, column resize)
Monaco Editor       → SQL editor (lazy-loaded, ~5MB — load only on /query route)
Recharts            → Primary charting (via Tremor/shadcn wrappers, SVG-based, good for <10K points)
Apache ECharts      → Heavy visualizations (network graphs, heatmaps, >10K data points, WebGL mode)
Framer Motion v12   → All animations (chart entrances, page transitions, micro-interactions)
cmdk                → Command palette (⌘K) — already bundled in shadcn/ui Command
react-day-picker    → Date range selector — already bundled in shadcn/ui Calendar
```

### Custom components to build

**QueryInput**: The flagship component. Large input bar with: auto-growing textarea, chain selector chip, suggested queries dropdown, submit button with loading state, keyboard shortcut hint (⌘Enter). On submit: transitions to show generated SQL + execution progress + results.

**MinerPanel**: Shows active miners processing a query. Each miner row: miner ID (truncated address), reputation score (0–100 with color coding), response time, verification status (checkmark/pending/failed). Animated progress indicators while query executes. This is unique to QueryAgent and a major trust differentiator.

**VerificationBadge**: Displays the "data snapshot proof" — a small badge/popover showing proof hash, block number, timestamp, and miner consensus score. Click to expand full verification details.

**QueryCard**: Used in explore page and dashboard home. Shows: question text (plain English), mini result preview (sparkline or value), chain badge, star count, fork count, miner score, author avatar + username, time ago. Hover: subtle elevation + border glow.

**ResultsPanel**: Tabbed container (Table | Chart | SQL | JSON) with: TanStack Table for tabular data, Recharts/Tremor chart with type switcher (line/bar/area/pie/scatter), Monaco read-only for SQL, formatted JSON with copy button.

**DashboardWidget**: Wrapper for dashboard grid items with: drag handle, resize handles, settings gear (change chart type, edit query link, remove), loading skeleton state, error state with retry.

**ScheduleBuilder**: Form component with: query selector, frequency picker (cron-based with human-friendly presets), delivery method selector (in-app/email/webhook), preview of next 5 run times.

---

## Animation and interaction recommendations

### Loading and state transitions

**Query execution flow** — this is QueryAgent's signature moment and should feel magical:
1. User submits question → input bar pulses with cyan glow, text "Translating to SQL..." appears
2. SQL generation → Monaco editor slides in from right with typewriter-effect SQL rendering (50ms per token)
3. Miner dispatch → MinerPanel fades in showing 3–5 miners with pulsing status dots
4. Results arrive → Chart/table fades up with staggered animation (opacity 0→1, y: 20→0, 400ms ease-out)
5. Verification → Green checkmark badge animates in with scale spring (1.2→1.0)

Use **Framer Motion's `AnimatePresence`** for mount/unmount transitions and **`layout` prop** for smooth repositioning when panels resize.

### Skeleton screens
Every data-dependent component should have a skeleton state matching its loaded shape. Use shadcn/ui's Skeleton component with Tailwind's `animate-pulse`. Charts show a gray rectangle with subtle wave lines. Tables show 5 rows of alternating-width gray bars. KPI cards show a large number placeholder + sparkline placeholder.

### Micro-interactions
- Buttons: `whileTap={{ scale: 0.97 }}` + 150ms background-color transition
- Cards: `whileHover={{ y: -2 }}` with `transition={{ type: "spring", stiffness: 400 }}`
- Star/favorite: Scale pop (1.0 → 1.3 → 1.0) with color fill animation
- Copy button: Check icon replaces copy icon for 2 seconds
- Number changes: `useSpring` to animate KPI counter values smoothly
- Chart data updates: 300ms crossfade between old and new data

### Page transitions
Use Next.js App Router's `template.tsx` with Framer Motion:
```tsx
<motion.main
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25, ease: "easeOut" }}
>
  {children}
</motion.main>
```

### Scroll animations (marketing pages only)
Staggered reveal for feature grids: each card fades in with 75ms delay. Use `whileInView` with `viewport={{ once: true, margin: "-100px" }}` to trigger slightly before elements enter viewport. Parallax effects on hero background elements (subtle, 0.5x scroll speed). **Avoid scroll animations inside the app** — they slow down data-focused workflows.

### Convex optimistic UI patterns
Convex's reactive `useQuery` hook automatically updates components when underlying data changes — no polling or WebSocket setup needed. For mutations (starring a query, creating a dashboard), use Convex's `useMutation` with **optimistic updates**: update UI immediately, then let Convex confirm or roll back. This makes the app feel instant. Show a subtle toast if a mutation fails and rolls back.

---

## What will make QueryAgent win

The competitive analysis reveals a clear positioning gap. Dune owns SQL-first analytics but alienates non-technical users. Flipside abandoned SQL entirely for AI, losing power users. Nansen provides pre-built intelligence but charges $99–$999/month with no custom queries. Footprint offers no-code but looks generic.

QueryAgent's winning formula is **plain-English queries with transparent SQL and decentralized verification** — it's the only platform that serves both natural language users AND SQL power users while providing cryptographic proof of results. The design system should reinforce this by making the natural language input the hero of every page, showing the generated SQL as an educational "under the hood" detail (collapsible, not hidden), and making miner scores and verification proofs visible but non-intrusive.

Three design decisions will differentiate QueryAgent visually: the **dark-mode-first palette** (while Dune stays light), the **MinerPanel** showing decentralized execution in real-time (no competitor has this), and the **query-to-chart animation flow** that makes asking blockchain questions feel like a premium AI experience rather than a database tool. Build the interaction design around that signature moment — the 3–5 seconds between question and answer — and make it the most satisfying data experience in crypto.