You’re basically asking: “What EXACTLY should this thing do so my coding agent can just start building?”
Let’s turn it into a clean, implementation-ready spec.

⸻

0. Product vision & scope

Vision:
A multi-tenant web app that:
	1.	Crawls any given website using Deepcrawl (self-hosted).  ￼
	2.	Runs an end-to-end SEO audit (technical + on-page + content gaps).
	3.	Calls an external API (e.g. DataForSEO Keywords Data API) for keyword research & SERP data.  ￼
	4.	Uses an LLM-based agent to:
	•	interpret crawl + keyword data
	•	draft a prioritized SEO plan
	•	generate content strategies and actual content drafts.
	5.	Provides a web dashboard for multiple clients (tenants), with user accounts and access control.

Assumed stack (can be adjusted):
	•	Agent framework:
	•	Primary suggestion: LangGraph (Python) as orchestration layer for tools/agents and multi-step workflows.
	•	Crawling: self-hosted Deepcrawl; your app talks to it via HTTP API.  ￼
	•	Keyword research: DataForSEO Keywords Data APIs (Keywords for Site, Keywords for Keywords, Keyword Overview, etc).  ￼
	•	Web app:
	•	Backend: Python (FastAPI / Django) or Node (NestJS)
	•	Frontend: Next.js/React, multi-tenant aware.
	•	Database: Postgres (multi-tenant schema), plus object storage for reports.

You can feed everything below as “business requirements” into your coding agent.

⸻

1. Actors & permissions
	1.	Platform Owner (Super Admin)
	•	Manages tenants (create, suspend, delete).
	•	Manages global settings: LLM providers, DataForSEO master account, default rate limits, pricing plans.
	2.	Tenant Admin (e.g. agency owner / in-house SEO lead)
	•	Manages their own tenant’s users.
	•	Manages sites (add/remove sites, verify ownership if needed).
	•	Sets project settings (languages, markets, brand tone, content guidelines).
	•	Full access to all audits, keyword research and content.
	3.	SEO Manager (within tenant)
	•	Can start crawls, run audits, launch keyword research, create SEO plans.
	•	Can generate and edit content.
	•	Cannot change tenant billing or global settings.
	4.	Read-Only User (client stakeholder)
	•	Can view dashboards, reports and content drafts.
	•	Cannot trigger crawls or modify data.
	5.	Background Agent / Worker
	•	System component that runs scheduled or queued jobs:
	•	Calls Deepcrawl.
	•	Calls DataForSEO.
	•	Calls LLM(s) via agent framework.

⸻

2. Core user journeys (high level)
	1.	Onboard a new tenant + site
	•	Super Admin creates tenant.
	•	Tenant Admin logs in, adds a new site (domain, language, target country, CMS type).
	•	System creates a default configuration (crawl depth, user-agent, delay, etc.).
	2.	Run initial SEO audit
	•	SEO Manager selects a site → click “Run full audit”.
	•	System:
	1.	Triggers Deepcrawl to crawl site.
	2.	Stores structured crawl data (URLs, status, headings, meta, content markdown, internal links, external links, etc.).
	3.	Agent processes crawl output:
	•	Technical SEO issues.
	•	On-page issues.
	•	Content gaps (surface-level, before keyword research).
	4.	Produces a prioritized issue list and a summary report.
	3.	Run keyword research
	•	SEO Manager goes to “Keyword Research” for a site.
	•	System calls DataForSEO to:
	•	Get keywords for the domain (Keywords for Site).
	•	Expand seeds/topics (Keywords for Keywords).
	•	Get search volume, CPC, competition and intent (Keyword Overview).  ￼
	•	System clusters keywords and maps them to:
	•	Existing URLs.
	•	New “recommended pages”.
	4.	Generate SEO strategy & roadmap
	•	SEO Manager clicks “Generate SEO plan”.
	•	Agent uses:
	•	Technical audit results.
	•	Keyword clusters and SERP insight.
	•	Site goals (traffic, leads, etc.).
	•	Output:
	•	3–6 month roadmap.
	•	Prioritized tasks grouped (Technical / On-page / Content / Authority).
	•	For each task: impact, effort, and required roles (developer, content, etc.).
	5.	Generate content
	•	For each recommended page or existing URL:
	•	Agent generates:
	•	Content brief (target kw, secondary kw, search intent, H1–H3 outline, internal links, CTAs).
	•	Optional full draft (body content, title tag, meta description).
	•	SEO Manager can:
	•	Edit and approve.
	•	Export as HTML, Markdown, or copy/paste optimized for CMS.
	6.	Monitor and iterate
	•	User can rerun audits.
	•	System compares latest results with previous runs (diffs, trend charts).
	•	Agent suggests “next best actions” based on changes (e.g., fixed issues, new pages added).

⸻

3. Functional requirements (detailed)

3.1 Multi-tenant & access control
	•	FR-1: System must support multiple tenants; data from different tenants must be logically separated (per-tenant DB schema or tenant_id on all relevant records).
	•	FR-2: Tenant Admin can:
	•	Invite users by email.
	•	Assign roles: Admin, SEO Manager, Read-only.
	•	Deactivate/reactivate users.
	•	FR-3: Authentication:
	•	Email/password and optional OAuth (Google, Microsoft) at later stage.
	•	Password reset flow.
	•	FR-4: Authorization:
	•	A user can only see data for their own tenant.
	•	Role-based access to actions (e.g., only Admin can change billing).

3.2 Site & project configuration
	•	FR-5: For each site, store:
	•	Primary domain.
	•	Additional domains/subdomains (optional).
	•	Default language(s).
	•	Target countries/markets.
	•	CMS type (for future integrations).
	•	Brand voice settings (tone, formal/informal, vocabulary constraints).
	•	FR-6: Allow enabling/disabling:
	•	Technical audit.
	•	Keyword research.
	•	Content generation.

3.3 Crawling (Deepcrawl integration)
	•	FR-7: System must be able to trigger a Deepcrawl job for a site via HTTP API, passing:
	•	Start URL / domain.
	•	Max depth.
	•	Max pages.
	•	Allowed domains.
	•	User-agent string and crawl delay.
	•	FR-8: System must poll/receive callbacks for crawl completion and status.
	•	FR-9: On completion, system must store:
	•	URL, status code, content type.
	•	Canonical URL.
	•	Meta robots, hreflang, canonical tags.
	•	Title tag, meta description.
	•	H1, H2, H3.
	•	Main content (cleaned markdown extracted by Deepcrawl).  ￼
	•	Internal and external links, including anchor text.
	•	FR-10: UI must show:
	•	Crawl date/time, pages crawled, errors.
	•	Basic filters (status code, content type, noindex/nofollow, etc).

3.4 Technical SEO audit
	•	FR-11: Agent must process crawl data and output structured issues, such as:
	•	Broken links / 4xx pages.
	•	5xx pages.
	•	Redirect chains and loops.
	•	Non-canonical pages with indexable status.
	•	Missing/duplicate title tags & meta descriptions.
	•	Too long/too short titles/descriptions.
	•	Multiple H1s or missing H1.
	•	Thin content (based on word count or LLM judgment).
	•	Orphan pages (if detectable via internal links).
	•	FR-12: Each issue must have:
	•	Unique ID.
	•	Type and category (e.g., “Technical > Status Codes”).
	•	Affected URLs.
	•	Severity (Low/Medium/High).
	•	Suggested fix (plain language).
	•	FR-13: Agent must generate a human-readable audit summary:
	•	Executive summary.
	•	Top 5 issues by impact.
	•	Quick wins vs long-term tasks.

3.5 Keyword research (DataForSEO)
	•	FR-14: For each site, system must allow:
	•	“Domain-based” keyword discovery using “Keywords for Site” endpoints.  ￼
	•	“Topic-based” expansion using “Keywords for Keywords”.
	•	Retrieval of metrics for keywords (search volume, CPC, competition, etc.) using Keyword Overview / Historical data endpoints.  ￼
	•	FR-15: User must be able to configure:
	•	Search engine (Google at minimum).
	•	Country/region.
	•	Language.
	•	FR-16: System must store keyword data, including:
	•	Keyword text.
	•	Search volume, trend, CPC, competition.
	•	Search intent (if provided by DataForSEO).
	•	FR-17: System must cluster keywords into topics:
	•	Automatic clustering (LLM or algorithmic).
	•	Each cluster has a label (e.g., “blue running shoes for men”).
	•	FR-18: Agent must map keyword clusters to:
	•	Existing URLs (based on content + URL + title).
	•	Suggested new URLs (“Recommended page: /guides/…”, “/blog/…”).

3.6 SEO plan & prioritization
	•	FR-19: For each site, user can click “Generate SEO plan”.
	•	FR-20: Agent must combine:
	•	Technical issues.
	•	Keyword opportunities.
	•	Site goals (traffic, conversions, etc.).
	•	FR-21: Output must be:
	•	Roadmap by timeframes (e.g., Month 1, Month 2–3, Month 4–6).
	•	Task list with:
	•	Title.
	•	Description.
	•	Category (Technical / Content / On-page / Authority).
	•	Estimated impact (High/Medium/Low).
	•	Estimated effort (High/Medium/Low).
	•	Suggested assignee type (Developer / Content Writer / SEO).
	•	FR-22: User must be able to:
	•	Mark tasks as “To Do / In Progress / Done”.
	•	Add comments and attachments (e.g., screenshots, Jira link).

3.7 Content generation
	•	FR-23: For each keyword cluster or recommended page:
	•	Agent can generate a content brief:
	•	Target keyword + secondary keywords.
	•	Search intent description.
	•	Recommended URL slug & page type (landing, blog, category, product).
	•	Outline (H1–H3).
	•	Recommended internal links (source/target URLs and anchors).
	•	Agent can optionally generate a full draft:
	•	Title tag and meta description.
	•	H1 and section headings.
	•	Body content.
	•	FAQ section (optional).
	•	FR-24: User must be able to:
	•	Edit AI drafts in the app (rich text editor / markdown).
	•	Save draft versions.
	•	Export as:
	•	HTML.
	•	Markdown.
	•	Plain text.
	•	FR-25: Content generation must respect:
	•	Brand tone configuration.
	•	Language (ES, EN, etc.).
	•	Word count preferences (short, medium, long-form).

3.8 Reporting & exports
	•	FR-26: Provide an overview dashboard per site:
	•	Latest audit score (e.g., 0–100).
	•	Number of open issues by severity.
	•	Number of keyword opportunities identified.
	•	Number of content briefs/drafts generated.
	•	FR-27: Allow export of:
	•	Audit issues to CSV / Excel.
	•	SEO plan to PDF/Markdown.
	•	Keyword lists and clusters to CSV.
	•	FR-28: Provide change history:
	•	Store results of past audits.
	•	Show trends (e.g., 404 count over time, indexable pages count).

3.9 Automation & scheduling
	•	FR-29: User can schedule:
	•	Recurring crawls (e.g., weekly, monthly).
	•	Recurring keyword refresh.
	•	FR-30: For scheduled jobs:
	•	System must queue them and execute via workers.
	•	On completion, notify users via email or in-app notifications.
	•	FR-31: Agent must be able to:
	•	Detect significant changes (e.g., big spike in errors or drop in indexable pages).
	•	Raise “alerts” with explanation.

⸻

4. Agent framework behaviour (LangGraph or similar)

4.1 Tools (functions) the agent will use

The agent framework must expose these tools:
	1.	Crawl tool
	•	start_crawl(site_id, config) → job_id
	•	get_crawl_result(job_id) → structured crawl data.
	2.	Keyword research tool
	•	discover_keywords_for_site(site_id, country, language)
	•	expand_keywords(seed_keywords, country, language)
	•	get_keyword_metrics(keywords, country, language)
	3.	Data access tools
	•	get_site_config(site_id)
	•	get_last_crawl(site_id)
	•	get_keywords(site_id)
	•	save_audit_issues(site_id, issues)
	•	save_seo_plan(site_id, plan)
	•	save_content_brief(site_id, page_id, brief)
	•	save_content_draft(site_id, page_id, content)
	4.	Notification tool
	•	send_notification(user_id, message, severity)

4.2 Agent workflows (graphs)

Define at least these workflows in the agent framework:
	1.	Full SEO Audit Workflow
	•	Nodes:
	1.	Fetch site config.
	2.	Start crawl.
	3.	Wait until crawl finished (or error).
	4.	Analyze technical issues.
	5.	Save issues + generate summary.
	6.	Notify user.
	2.	Keyword Research Workflow
	•	Nodes:
	1.	Get existing crawl/site data.
	2.	Call DataForSEO “Keywords for Site”.
	3.	Optionally call “Keywords for Keywords” with seeds from content.
	4.	Call Keyword Overview/Historical metrics.
	5.	Cluster and map keywords to URLs.
	6.	Save keyword clusters.
	3.	SEO Plan Workflow
	•	Nodes:
	1.	Fetch latest issues + keyword clusters.
	2.	Ask LLM to prioritize and group tasks.
	3.	Save structured plan.
	4.	Notify user.
	4.	Content Generation Workflow
	•	Nodes:
	1.	Select keyword cluster or recommended page.
	2.	Generate brief (LLM).
	3.	Optionally generate full draft (LLM).
	4.	Save results.

Each workflow must be re-runnable and idempotent where possible.

⸻

5. Non-functional requirements
	•	NFR-1: Multi-tenancy & security
	•	Strong tenant isolation in data layer.
	•	No cross-tenant data leaks in API or UI.
	•	NFR-2: Performance
	•	Dashboard pages should load in < 2 seconds for typical tenants.
	•	Long-running tasks (crawls, keyword research) run asynchronously and never block the UI.
	•	NFR-3: Reliability
	•	Retry logic for Deepcrawl and DataForSEO API calls (with exponential backoff).
	•	Clear error messages if external APIs fail.
	•	NFR-4: Cost control
	•	Per-tenant limits on:
	•	Max pages per crawl.
	•	Max keyword queries per month.
	•	Track and log API usage for DataForSEO.
	•	NFR-5: Observability
	•	Log all agent workflows, including:
	•	Start/end time.
	•	Tools called.
	•	Failures and reasons.
	•	NFR-6: Extensibility
	•	Architect the integrations so that:
	•	Deepcrawl could be swapped for another crawler.
	•	DataForSEO could be swapped for another keyword API.
	•	LLM provider is abstracted behind a simple interface.

⸻

6. Out of scope (for now, but nice to have)
	•	Direct integration with Google Search Console / Analytics.
	•	Live rank tracking for keywords.
	•	Backlink analysis (DataForSEO also has this, but treat it as v2).
	•	Direct publishing to CMS (WordPress, Webflow, Shopify).

    