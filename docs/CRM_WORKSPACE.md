# LinkedIn Engine workspace in VRX CRM

The engine (this repo) is the **brain**. It scores all ~11.4k connections, plans the daily queue, and learns which openers work. The CRM workspace is the **cockpit**: only people who are actually in play live there, with a lean UI built for this one job.

## Why a separate workspace

- The pipeline covers more than VR Express: AI builds, BrainTube, agency partnerships, talent and referrals.
- The VR Express workspace has about 110 views, gated by tier. The LinkedIn workspace shows about 12.
- Data is isolated per workspace by RLS (`is_org_member(organization_id, auth.uid())`). The MCP is scoped per token, so Cowork's connector can only ever touch this workspace.

## Build phases (VR Express CRM Suite, Lovable project 8884772e…)

| Phase | What | Status |
|---|---|---|
| 1a | `find_or_create_account` is workspace-aware; the contact trigger passes the contact's org; the 5 leaked BrainTube→VR Express links are repaired | done (commit e6feb9c) |
| 1b | WorkspaceProvider plus a switcher in the sidebar; every insert carries `organization_id`; the sidebar no longer breaks when a user has 2+ memberships | done (0d251fd, bda8f32) |
| 1c | `crm-mcp`: `MCP_SERVER_TOKEN_LI` + `MCP_ORG_ID_LI`, label `LI` (mirrors BrainTube) | done (bda8f32); needs secrets |
| 1d | Create the org "LinkedIn Engine" (`linkedin-engine`, id 22630c16-3de9-4e00-ad16-2975bac06d1f), owner membership, and entitlements for tiers 0–5 | done |
| 2 | Per-workspace nav profile: `organizations.settings.nav_profile = 'linkedin'` → curated menu | done (d74f6e8) |
| 3 | LinkedIn views: Funnel dashboard, Scoreboard, Replies; MCP `upsert_linkedin_prospects` (LI-only, keeps CRM DNC, returns `dnc`) | done (d4b8609, faa71d4, a70f9e1, 4bef6a5) |

## Who goes into the workspace (the "active funnel only" rule)

A person is pushed from the engine when **either** of these is true:
- they enter a sequence (touch 1 sent), or
- they are grade A or B, even before contact, so they're visible for manual prioritizing.

Expected size: about 1–3k over the first months, not 11.4k.

## Field mapping (engine → CRM contact)

| CRM | Value |
|---|---|
| `name`, `company`, `role`, `email` | from Connections.csv / Cowork profile capture |
| `source` | `linkedin` |
| `lead_score` | engine score 0–100 |
| `tags` | `track:<track>`, `grade:<A-D>`, `li-stage:<stage>`, `lang:<bg\|en>` |
| `custom_fields.linkedin_url` | profile URL (unique key) |
| `custom_fields.li` | `{score, rel, intent, fit, timing, track, grade, stage, touch, variant, next_due, next_action, reasons, offer}` |

Stages: `IN_SEQUENCE → REPLIED → CONVERSATION → MEETING → PROPOSAL → WON / LOST`, plus `NURTURE` and `DNC`.
A **deal** is created when a contact reaches CONVERSATION. From then on the CRM pipeline owns the stage, and the engine reads it back so it never re-sequences someone in a live deal.

## LinkedIn nav profile (phase 2)

| Section | Views |
|---|---|
| Today | **LinkedIn Funnel** (new home), **Replies** (new), Tasks, Calendar |
| People | Contacts, Pipeline, **Scoreboard** (new) |
| Conversations | LinkedIn |
| Assist | Agent Hub |
| Setup | Import CSV, Settings, Users |

Everything else is hidden in this workspace, including ⌘K. VR Express is unchanged.

## New views (phase 3)

- **LinkedIn Funnel:** KPI row (in sequence · replied · conversations · meetings · proposals · won); stage funnel; reply rate by track; sends in the last 14 days; opener A/B table.
- **Scoreboard:** sortable table with grade, score and the Relationship/Intent/Fit/Timing bars, track chips, "why", next best action, and a link to the LinkedIn profile. Filters by track, grade and stage.
- **Replies:** contacts with a logged reply that isn't handled yet, showing sentiment, summary and the drafted response. Actions: Approve & mark sent, Edit, Create deal, Mark DNC.

## Cowork connectors

- **VRX CRM (VR Express):** existing token, unchanged.
- **VRX CRM – LinkedIn:** same MCP URL with `MCP_SERVER_TOKEN_LI`. Cowork's LinkedIn task uses only this one.
