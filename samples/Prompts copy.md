Copy-ready format below. Each block is one 

prompt you can copy directly.



Prompt 01

Recreate SignalBoard exactly. Do only this step.

Initialize a Next.js App Router + TypeScript project (with src/).
Set package.json exactly:
name: frontend-assignment-dashboard
version: 0.1.0
private: true
scripts:
  dev: next dev
  build: next build
  start: next start
  lint: eslint . --max-warnings=0
dependencies:
  next: 16.1.6
  react: 19.2.0
  react-dom: 19.2.0
devDependencies:
  @types/node: 22.15.30
  @types/react: 19.2.2
  @types/react-dom: 19.2.2
  eslint: 9.26.0
  eslint-config-next: 16.1.6
  typescript: 5.8.3



Prompt 02

Recreate SignalBoard exactly. Do only this step.

Create exact folders:
src/app/api/{analytics,stats,users}
src/app/{challenges,reports,settings}
src/features/dashboard/{api,components,components/stats-analytics,components/users-table,data,layout,utils}
src/shared/{hooks,i18n,types,utils}
packages/design-system/src/{components/{Badge,Button,Card,DataTable,InputField},icons,styles,theme,utils}
public/images/{avatars,brand}




Prompt 03

Recreate SignalBoard exactly. Do only this step.

Write tsconfig.json with:
target ES2022, module esnext, moduleResolution bundler, strict true, noEmit true, jsx react-jsx, incremental true, baseUrl "."
paths:
  "@/*": ["./src/*"]
  "@design-system": ["packages/design-system/src/index.ts"]
  "@design-system/*": ["packages/design-system/src/*"]
types: ["node"]
plugins: [{ "name": "next" }]
include:
  next-env.d.ts
  **/*.ts
  **/*.tsx
  .next/types/**/*.ts
  .next/dev/types/**/*.ts
exclude: node_modules



Prompt 04

Recreate SignalBoard exactly. Do only this step.

Create next.config.ts:
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    staleTimes: {
      dynamic: 60,
      static: 300,
    },
  },
};

export default nextConfig;


Prompt 05

Recreate SignalBoard exactly. Do only this step.

Create ARCHITECTURE.md with strict layer rules:
- app: src/app/*
- feature: src/features/*
- shared: src/shared/*
- design-system: packages/design-system/*
Allowed:
  app -> feature/shared/design-system
  feature -> shared/design-system
Disallowed:
  shared -> feature/app
  feature -> app
  design-system -> src/*

Create eslint.config.mjs using:
- eslint-config-next/core-web-vitals
- eslint-config-next/typescript
Add no-restricted-imports rules enforcing those boundaries.

Keep .eslintrc.json extending:
["next/core-web-vitals", "next/typescript"]


Prompt 06

Recreate SignalBoard exactly. Do only this step.

Create packages/design-system/package.json:
{
  "name": "@signalboard/design-system",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "sideEffects": ["./src/styles/index.css"],
  "exports": {
    ".": "./src/index.ts",
    "./styles.css": "./src/styles/index.css"
  }
}

Create packages/design-system/src/index.ts as barrel placeholder (will fill later).


Prompt 07

Recreate SignalBoard exactly. Do only this step.

Create packages/design-system/src/styles/tokens.css with exact token names:
- breakpoints: --breakpoint-sm/md/lg/xl (40rem, 48rem, 64rem, 80rem)
- font sizes: --font-size-xs/sm/md/lg/xl/2xl using clamp
- line-height-tight/normal/relaxed
- font-weight-regular/medium/semibold/bold
- font-family-heading/body/mono using --font-heading, --font-body, --font-mono
- spacing: --space-2xs through --space-3xl using clamp
- radii, border widths, durations, easings
- shadows sm/md/lg/xl


Prompt 08

Recreate SignalBoard exactly. Do only this step.

In tokens.css add all light theme colors exactly:
primary:
  --color-primary-light: #5fa8ff
  --color-primary-base: #1f7ae0
  --color-primary-dark: #155cb0
secondary:
  --color-secondary-light: #7bdcc4
  --color-secondary-base: #22a38a
  --color-secondary-dark: #16715f
neutral scale:
  50 #f6f8fb, 100 #ebeff5, 200 #dce3ed, 300 #c7d1df, 400 #9cabc0,
  500 #7588a0, 600 #586b83, 700 #3f5167, 800 #29384b, 900 #152030
semantic:
  success #2b9a59, warning #cf8b18, error #c84545, info #2f76cf
surface/text/border/overlay tokens exactly as SignalBoard.


Prompt 09

Recreate SignalBoard exactly. Do only this step.

In tokens.css add [data-theme='dark'] overrides exactly:
primary base: #4c94eb
secondary base: #45ac98
neutral scale:
  50 #050505, 100 #0a0a0a, 200 #121212, 300 #1a1a1a, 400 #282828,
  500 #3b3b3b, 600 #5a5a5a, 700 #888888, 800 #b5b5b5, 900 #e6e6e6
surface:
  background #000000, card #0a0a0a, elevated #121212
text:
  primary #f2f2f2, secondary #b0b0b0, disabled #6f6f6f, inverse #090909
border:
  subtle #242424, strong #3a3a3a
semantic:
  success #49b878, warning #dba542, error #e96a6a, info #67a3e8
dark shadows and overlay exactly as current app.


Prompt 10

Recreate SignalBoard exactly. Do only this step.

Create:
packages/design-system/src/styles/foundations.css
packages/design-system/src/styles/index.css
src/app/globals.css

index.css must import only:
@import './tokens.css';
@import './foundations.css';

foundations.css must include:
box-sizing reset, html/body reset, body typography defaults, heading defaults, form font inheritance, :focus-visible ring.

globals.css must:
- import ../../packages/design-system/src/styles/index.css
- add body radial gradient background (light)
- add [data-theme='dark'] body gradient variant
- add .skip-link focus-reveal styles


Prompt 11

Recreate SignalBoard exactly. Do only this step.

Create utility files:
packages/design-system/src/utils/classNames.ts
src/shared/utils/class-names.ts

Both export:
classNames(...values: Array<string | false | null | undefined>): string

Create src/shared/types/styles.d.ts with:
declare module '*.css';
declare module '*.scss';
declare module '*.sass';


Prompt 12

Recreate SignalBoard exactly. Do only this step.

Create packages/design-system/src/icons/index.tsx.
Export IconProps and these icons:
ArrowDownIcon, ArrowUpIcon, ChartBarIcon, ChevronLeftIcon, ChevronRightIcon, ConversionIcon, ExternalLinkIcon, FlaskIcon, FolderChartIcon, MenuIcon, RevenueIcon, SearchIcon, SessionsIcon, SettingsIcon, SortIcon, ThemeIcon, UsersIcon.
Use currentColor SVG strokes and optional size/className props.


Prompt 13

Recreate SignalBoard exactly. Do only this step.

Create theme system:
packages/design-system/src/theme/ThemeProvider.tsx

Requirements:
Theme type: 'light' | 'dark'
Storage key: 'dashboard-theme'
resolve initial theme from:
1) html data-theme
2) localStorage
3) prefers-color-scheme
on theme change update html data-theme and localStorage
export ThemeProvider and useTheme with provider guard error.


Prompt 14

Recreate SignalBoard exactly. Do only this step.

Create:
packages/design-system/src/theme/ThemeToggle.tsx
packages/design-system/src/theme/ThemeToggle.module.css

Props:
label default 'Theme'
ariaLabel default 'Toggle theme'
Button shows ThemeIcon + label and toggles theme via useTheme.
Use pill border, subtle hover lift, tokenized transitions.


Prompt 15

Recreate SignalBoard exactly. Do only this step.

Create Button component:
packages/design-system/src/components/Button/Button.tsx
packages/design-system/src/components/Button/Button.module.css

API:
variant: primary | secondary | ghost
size: small | medium | large
loading, leadingIcon, trailingIcon, children

Behavior:
- loading disables button
- aria-busy set during loading
- spinner + sr-only children in loading mode
- active press translate
- exact tokenized color states for each variant


Prompt 16

Recreate SignalBoard exactly. Do only this step.

Create InputField component:
packages/design-system/src/components/InputField/InputField.tsx
packages/design-system/src/components/InputField/InputField.module.css

Support:
label, error, helperText, counter, prefix/suffix, hideMeta, floatingLabel
controlled and uncontrolled mode
generated id from label + useId (remove ":" chars)
aria-describedby assembly from helper/error/counter
focus/error/disabled/readOnly visuals
floating label transform when focused or has value


Prompt 17

Recreate SignalBoard exactly. Do only this step.

Create Card and Badge:

Card:
packages/design-system/src/components/Card/Card.tsx + Card.module.css
variant default|elevated, hoverable, stretch, optional header/footer

Badge:
packages/design-system/src/components/Badge/Badge.tsx + Badge.module.css
tone neutral|success|warning|error|info
pill styles with tokenized color-mix


Prompt 18

Recreate SignalBoard exactly. Do only this step.

Create DataTable:
packages/design-system/src/components/DataTable/DataTable.tsx
packages/design-system/src/components/DataTable/DataTable.module.css

Must support:
- typed generic columns with sortable and non-sortable variants
- sticky header
- optional sticky first column
- sort icon states (SortIcon, ArrowUpIcon, ArrowDownIcon)
- loading skeleton rows when empty
- loading mask on existing rows
- empty message
- error message
- title/actions row
- maxBodyHeight
CSS must include:
min-width 58rem table
striped rows
hover highlight
sticky z-index layering
container-query sticky shadow behavior


Prompt 19

Recreate SignalBoard exactly. Do only this step.

Create Pagination:
packages/design-system/src/components/DataTable/Pagination.tsx
packages/design-system/src/components/DataTable/Pagination.module.css

Logic:
visible page markers = {1, totalPages, current, current-1, current+1} clamped/sorted.
Render text:
Page {current} of {total}
optionally append: · {totalItems} items
Use Button secondary small for Previous/Next.
Disable controls while loading.


Prompt 20

Recreate SignalBoard exactly. Do only this step.

Finalize packages/design-system/src/index.ts exports exactly:
Button + ButtonProps
Badge + BadgeProps
InputField
Card
DataTable + DataTableColumn + DataTableProps + DataTableSortOrder
Pagination + PaginationProps
ThemeProvider + useTheme
ThemeToggle
IconProps and all icon exports


Prompt 21

Recreate SignalBoard exactly. Do only this step.

Create shared API contracts and utils:
src/shared/types/api.ts
- ApiMeta {page,totalPages,totalItems}
- ApiResponse<T> {data,meta?,error?}
- SortOrder = 'asc'|'desc'
- RangeKey = '7d'|'30d'|'90d'

src/shared/utils/api-response.ts
- createApiResponse
- parseApiResponse
- readApiResponseData

src/shared/utils/number.ts
- parseNumberOrFallback
- parsePositiveNumberOrFallback


Prompt 22

Recreate SignalBoard exactly. Do only this step.

Create shared hooks:
src/shared/hooks/useAsyncQuery.ts
- options: queryKey, queryFn({signal}), initialData?, skipInitialRequest?, preserveDataOnError?
- abort in-flight requests on cleanup
- isLoading derived from resolvedQueryKey !== queryKey
- error scoped to current queryKey

src/shared/hooks/useDebouncedValue.ts
- returns debounced value using setTimeout + cleanup


Prompt 23

Recreate SignalBoard exactly. Do only this step.

Create i18n:
src/shared/i18n/messages.ts
src/shared/i18n/I18nProvider.tsx
src/shared/i18n/index.ts

Use exact EN keys and values:
a11y.skipToMainContent='Skip to main content'
layout.appName='SignalBoard'
layout.breadcrumb='Dashboard > Analytics'
layout.searchDashboard='Search dashboard'
layout.openNavigationMenu='Open navigation menu'
layout.closeNavigationMenu='Close navigation menu'
layout.goToHome='Go to analytics dashboard'
layout.navigation='Navigation'
layout.primaryNavigation='Primary navigation'
layout.expandSidebar='Expand sidebar'
layout.collapseSidebar='Collapse sidebar'
layout.userMenu='User menu'
layout.userSettings='Settings'
layout.userLogout='Logout'
layout.nav.analytics='Analytics'
layout.nav.challenges='Challenges'
layout.nav.reports='Reports'
layout.nav.settings='Settings'
theme.toggle='Toggle theme'
theme.label='Theme'
Add Spanish catalog too.
DEFAULT_LOCALE='en'


Prompt 24

Recreate SignalBoard exactly. Do only this step.

Create dashboard domain types/constants:
src/features/dashboard/types.ts
src/features/dashboard/constants.ts

Use exact constants:
USERS_PAGE_LIMIT=8
USERS_TABLE_SKELETON_ROW_COUNT_MIN=12
USERS_PAGE_LIMIT_MIN=4
USERS_PAGE_LIMIT_MAX=20
USERS_SEARCH_DEBOUNCE_MS=300
DEFAULT_USER_SORT_FIELD='name'
DEFAULT_USER_SORT_ORDER='asc'
USER_SORT_FIELDS=['name','email','role','status','country','lastActive','spend']
SORT_ORDER_OPTIONS=['asc','desc']
DEFAULT_ANALYTICS_RANGE='30d'
DASHBOARD_RANGE_OPTIONS=['7d','30d','90d']
ANALYTICS_POINTS_BY_RANGE={'7d':7,'30d':10,'90d':12}
API_DELAY_MIN_MS=200
API_DELAY_MAX_MS=800
API_CACHE_MAX_AGE_SECONDS=60
API_CACHE_STALE_WHILE_REVALIDATE_SECONDS=300
ANALYTICS_CLIENT_CACHE_TTL_MS=60000
USERS_CLIENT_CACHE_TTL_MS=30000
MOCK_USERS_TOTAL=64
MOCK_REFERENCE_DATE='2026-01-31'
ANALYTICS_CHART_SKELETON_BAR_HEIGHTS=[44,62,52,68,60,74,58,82,66,76,63,72]


Prompt 25

Recreate SignalBoard exactly. Do only this step.

Create query parsing modules:
src/features/dashboard/utils/users-query.ts
src/features/dashboard/api/query-parsers.ts

Requirements:
- resolveUserSortState validates sort/order against constants
- parseUsersPageParam positive fallback
- parseUsersLimitParam clamped min/max
- parseUsersSearchParams returns UsersQuery with trimmed search
- parseRangeKey validates 7d|30d|90d and falls back to 30d


Prompt 26

Recreate SignalBoard exactly. Do only this step.

Create data layer:
src/features/dashboard/data/dashboard-repository.ts
src/features/dashboard/data/dashboard-service.ts

Repository must generate deterministic mock users with exact arrays:
firstNames: Aarav,Sophia,Liam,Olivia,Ethan,Emma,Noah,Ava,Mason,Mia,Lucas,Isabella,Elijah,Amelia,James,Charlotte
lastNames: Sharma,Brown,Wilson,Thomas,Lee,Walker,King,Harris,Young,Scott,Turner,Parker,Evans,Collins,Morgan,Reed
roles: Admin,Manager,Analyst,Support
statuses: Active,Inactive,Pending
countries: United States,India,Canada,Germany,Japan,United Kingdom,Australia,Singapore
email format: firstname.lastname.{index}@example.com
spend formula: 450 + (index % 9) * 137 + index * 17
stats cards and analytics series exactly as SignalBoard.
Include filtering/sorting/pagination with safe page and ApiMeta.
Service must wrap outputs in ApiResponse.


Prompt 27

Recreate SignalBoard exactly. Do only this step.

Create API client + effects + route handlers:

src/features/dashboard/api/dashboard-client.ts
- getStats
- getAnalytics(range)
- getUsersPage(query)
with AbortSignal and ApiResponse parsing

src/features/dashboard/api/http-effects.ts
- randomDelay(min,max)
- shouldBypassDelay(request) (bypass unless dev and no x-internal-no-delay header)

src/app/api/stats/route.ts
src/app/api/analytics/route.ts
src/app/api/users/route.ts

Use delay logic and service calls.
Set cache-control:
stats/analytics -> public, max-age=60, stale-while-revalidate=300
users -> public, max-age=30 (half of 60 with min safeguard), stale-while-revalidate=60


Prompt 28

Recreate SignalBoard exactly. Do only this step.

Create dashboard layout shell:
src/features/dashboard/layout/constants.ts
src/features/dashboard/layout/navigation-items.ts
src/features/dashboard/layout/DashboardChrome.tsx
src/features/dashboard/layout/ChromeHeader.tsx
src/features/dashboard/layout/ChromeSidebar.tsx
src/features/dashboard/layout/UserMenuDropdown.tsx
src/features/dashboard/layout/DashboardShell.module.css
src/features/dashboard/layout/ChromeHeader.module.css
src/features/dashboard/layout/ChromeSidebar.module.css
src/features/dashboard/layout/UserMenuDropdown.module.css
src/features/dashboard/layout/index.ts

Use exact copy:
appName SignalBoard
breadcrumb Dashboard > Analytics
userName Kavin Bellam
userEmail kavin@example.com

Features:
sticky top header, center search InputField, theme toggle, avatar dropdown
sidebar collapse 16.25rem -> 4rem desktop
mobile slide-in drawer + backdrop
prefetch non-active nav routes


Prompt 29

Recreate SignalBoard exactly. Do only this step.

Create stats + analytics feature modules:
src/features/dashboard/components/StatsCard.tsx + .module.css
src/features/dashboard/components/StatsGrid.tsx + .module.css
src/features/dashboard/components/AnalyticsPanel.tsx + .module.css
src/features/dashboard/components/StatsAnalyticsClient.tsx
src/features/dashboard/components/StatsAnalyticsSection.tsx
src/features/dashboard/components/StatsAnalyticsSection.module.css
src/features/dashboard/components/stats-analytics/constants.ts
src/features/dashboard/components/stats-analytics/types.ts
src/features/dashboard/components/stats-analytics/api.ts
src/features/dashboard/components/stats-analytics/useStatsAnalyticsQuery.ts

Behavior:
server-load stats + default analytics in parallel
range buttons 7d/30d/90d
client analytics cache TTL 60s
skeleton overlay while switching range
error text on failure
StatsCard container query stacks at max-width 18.75rem


Prompt 30

Recreate SignalBoard exactly. Do only this step.

Create users table feature + app routes + final shell wiring:

Users table files:
src/features/dashboard/components/users-table/constants.ts
src/features/dashboard/components/users-table/types.ts
src/features/dashboard/components/users-table/utils.ts
src/features/dashboard/components/users-table/api.ts
src/features/dashboard/components/users-table/useUsersTableQuery.ts
src/features/dashboard/components/users-table/columns.tsx
src/features/dashboard/components/UsersTable.tsx
src/features/dashboard/components/UsersTableSection.tsx

Users table behavior:
URL-driven state page/sort/order/search
replaceState updates URL
debounced search 300ms resets page=1
sort toggles asc/desc
popstate sync
sticky Name column
status badge tones
pagination controls

Create app routes/layout:
src/app/layout.tsx
src/app/page.tsx + page.module.css
src/app/challenges/page.tsx + page.module.css
src/app/reports/page.tsx + page.module.css
src/app/settings/page.tsx + page.module.css
src/app/loading.tsx + loading.module.css
src/app/error.tsx
src/features/dashboard/components/DashboardStreamingFallbacks.tsx + .module.css
src/app/globals.css should already be used

layout.tsx must include:
- Space_Grotesk, Manrope, JetBrains_Mono font vars
- metadata title: SignalBoard Analytics Dashboard
- metadata description: Design-system driven analytics dashboard assignment
- theme-init inline script with localStorage key dashboard-theme
- skip-link
- I18nProvider + ThemeProvider + DashboardChrome

page.tsx must use two Suspense boundaries:
StatsAnalyticsSection fallback
UsersTableSection fallback keyed by serialized search params

Update README.md and ARCHITECTURE.md to match implementation details and verify lint/build pass.
If you want, I can also paste these as a single plain .txt block with === 

PROMPT 01 === separators so you can save once and copy linearly.
