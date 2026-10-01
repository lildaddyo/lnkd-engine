# LinkedIn Network Sales Engine: Playbook

How the engine turns about 11.4k LinkedIn connections into a working funnel, and why each rule exists. Sources marked **[E]** are peer-reviewed or large-sample studies. **[P]** marks practitioner consensus, which the engine is built to test rather than assume.

## 1. Core thesis

Your network is not a cold list. Most of the value sits in **dormant and weak ties**: people you once talked with or are loosely connected to.

- **[E] Dormant ties.** Levin, Walter & Murnighan (2011, *Organization Science* 22(4)) found that reconnecting with dormant ties gave executives more novel and useful knowledge than their current ties, with trust largely intact. → The engine weights past two-way conversations and gives the 1–5 year dormancy window the highest timing score.
- **[E] Weak ties.** Rajkumar et al. (2022, *Science* 377) ran randomized experiments on 20M LinkedIn users and found moderately weak ties are the most valuable, with diminishing returns as ties get weaker. → Warm and weak connections come before total strangers.
- **[E] Referrals.** Schmitt, Skiera & Van den Bulte (2011, *Journal of Marketing* 75) found referred customers were ~16% more valuable over their lifetime and churned less. → Non-sales contacts are not wasted: the NETWORK and WARM tracks end with a referral ask, and a referral enters the queue with a +10 relationship boost.

## 2. The funnel

```
11.4k connections ──► Scoreboard (R+I+F+T) ──► Track ──► 3-touch sequence ──► Reply
                                                                        │
      NEW → IN_SEQUENCE → REPLIED → CONVERSATION → MEETING → PROPOSAL → WON
                  │                                       (VRX CRM takes over)
                  └─► NURTURE (no reply after 3 touches; re-eligible after 90 days)
      NOT_CONNECTED · LOST · DNC (never contacted again)
```

## 3. Prospect scoreboard (0–100)

| Axis | Max | Signals (from your export) | Why |
|---|---|---|---|
| **Relationship** | 35 | two-way threads, their message volume, they started the conversation, endorsed you, invited you, shared a phone number, connected recently, CRM past buyer (+15) or dormant client (+12), warm referral (+10) | Tie strength predicts reply and trust (§1) |
| **Intent** | 25 | past talk of price, offer or contract (+8), meetings (+6), VR/XR (+4), AI (+2), positive language (+4), "keep me in mind" (+2) | Explicit buying language is the strongest signal available |
| **Fit** | 30 | seniority (C-level 10 → specialist 3) + function (HR, L&D, marketing, brand, events, innovation = 8–10) + vertical (pharma 10; banking and FMCG 9; telco 8; retail 7) | Classic fit × engagement lead scoring, using VR Express's ICP from the CRM |
| **Timing** | 10 | dormant 1–5 years = 10; 3–12 months = 8; active (<3 months) = 4; never talked = 3 | Dormant ties are the sweet spot (§1) |
| Penalties | | vendor pitched you and you never replied (−10); only group threads (−4); ignored a mass message (−3) | Removes false warmth |

**Grades:** A ≥ 50 · B ≥ 35 · C ≥ 22 · D < 22. Each prospect shows *why* it scored that way, and a **next best action** with the matching offer (see `config.json → offers`).

Baseline on the Sept 2026 export (11,438 connections plus 734 non-connected people from messages and invitations):

| Track | A | B | C | D | Total |
|---|---:|---:|---:|---:|---:|
| REACTIVATE | 20 | 28 | 5 | 3 | 56 |
| WARM | 47 | 609 | 427 | 7 | 1,090 |
| ICP | 0 | 29 | 1,460 | 840 | 2,329 |
| BUILDER | 0 | 0 | 23 | 1,103 | 1,126 |
| PARTNER | 4 | 38 | 177 | 714 | 933 |
| STUDENT / early-career | 0 | 1 | 24 | 305 | 330 |
| NETWORK | 0 | 2 | 479 | 5,029 | 5,510 |
| AUTO (profile unknown) | 0 | 0 | 8 | 777 | 785 |

## 4. Tracks: what to do with each person

| Track | Who | Motion | Offer |
|---|---|---|---|
| **REACTIVATE** | CRM past buyers and dormant clients, or past threads with price or meeting talk | "Pick up where we left off", show what's new | V-Personas, AI med-rep, XR (by vertical) |
| **WARM** | You've had a real two-way conversation | Peer reconnect → give first → soft ask | Whatever fits their role |
| **ICP** | Decision-level HR, L&D, marketing, brand, events or innovation; or C-level at pharma, banking, FMCG, telco or retail | Relevance-first cold open with a vertical proof point and an interest CTA | VR onboarding, AR/3D, AI digital humans |
| **BUILDER** | Founders, owners, startup CEOs | "What's stuck on your roadmap?" | AI-native product in weeks |
| **PARTNER** | Agencies, studios, freelancers | White-label partnership plus a referral loop | Partner pricing, invisible delivery |
| **INVESTOR** | Investors, angels, VC/fund partners and directors (segment rule, only cold-ish contacts) | No pitch: is XR / applied AI in their thesis? One-page overview, ask for an intro | Portfolio and track record |
| **AIPEER** | Founders and leads at AI, agent or automation companies | Builder to builder: swap notes, co-delivery or white-label in both directions | AI builds, XR capacity |
| **STUDENT / early-career** | Students, interns, trainees, juniors, assistants | **Not sales.** Beta testers, talent pool, campus referrals | BrainTube early access, internships |
| **NETWORK** | Everyone else (engineers, recruiters, public sector...) | Give-first reconnect → specific referral ask | Referrals to the above |
| **DNC** | Asked to stop, spam folder, family | Never contacted | — |

Why a separate student track: students and juniors are a poor buyer fit today, but a cheap, high-goodwill audience for **product feedback (BrainTube)**, **hiring**, and **word of mouth**. Asking for advice or feedback is well received and raises perceived competence (**[E]** Brooks, Gino & Schweitzer 2015, *Management Science*). Today's juniors are also tomorrow's managers, since they carry the tie forward (§1).

## 5. Message rules

- **[E] Interest CTA on first touch.** Gong Labs analyzed 304k emails: interest-based CTAs ("Is this on your agenda?") booked meetings at about twice the rate of asking for time on cold outreach (30% vs 15%). Once interest is shown, a *specific time* ask more than doubles booked meetings. → Touch 1 asks about interest; reply drafts propose times.
- **[E] Follow-ups matter.** Backlinko and Pitchbox analyzed 12M outreach emails: only 8.5% got a reply, and one follow-up gave +65.8% more replies. → Three touches at day 0, +4 and +10, then stop. More than that on LinkedIn reads as spam **[P]**.
- **[P] Short, one idea, one question, no link in touch 1.** Touch 1 stays under ~60 words.
- **[P] Personal first line from the live profile** (`{hook}`, written by Cowork) plus **shared history** (`{context}`, e.g. "We last spoke in 2023 about VR training"). Generic flattery is banned.
- **[P] Never pitch price.** This follows the VR Express pricing thesis: deals are lost on follow-up and demand, not cost.
- **Language:** Bulgarian by default for Bulgarian names, companies or history (formal "Вие" for business tracks, "ти" for warm and student tracks). English otherwise. Cowork corrects it against the profile location.

## 6. Experimentation (the growth-hacking part, done properly)

- Every touch-1 template has variants `a` and `b`, and you can add `c`, `d` and so on in `templates.json`.
- The engine uses **Thompson sampling** (a Beta-Bernoulli bandit) per track and language. Each opener's reply rate is a probability distribution, and each send samples from it. Winners get more traffic automatically, and losers still get enough to be measured. This beats fixed 50/50 A/B splits when sample sizes are small.
- Success means a positive, neutral or referral reply. `python -m engine report` shows the variant table.
- **Test one thing at a time:** CTA type, then first-line style, then length. Retire a variant once it has at least 100 sends and is clearly behind.

## 7. Volume and account safety (read this)

- **LinkedIn's User Agreement §8.2 prohibits bots or other automated methods to "send or redirect messages".** Cowork driving a browser is automation. **The risk is to your account**, which can be restricted or banned, and that would also cut off your network. The engine reduces the risk but cannot remove it.
- LinkedIn publishes **no official daily cap** for messages to 1st-degree connections. The engine's defaults are conservative **[P]**:
  - **Ramp:** 40/day (send-days 1–5) → 70 → 100 → 120 → **120–150/day from send-day 21**, weekdays only, with jitter.
  - Follow-ups take at most 50% of daily volume.
  - 40–120 seconds between sends, spread over 2–3 sessions, with a **hard stop** on any warning or CAPTCHA.
  - Every message is personalized, so there are no identical blasts, which pattern detection flags.
- **Signals to slow down:** replies of "is this automated?", a rising `skipped_other` count, or any LinkedIn notice. Lower `volume.ramp`/`max_daily` in `config.json`.

**Capacity math:** 150/day × 5 days = 750 messages/week. With up to 3 touches per person, that is about **250 new people per week**, so about 11k connections take roughly 10 months. Prioritization therefore matters more than volume: A and B grades go first, and the track mix keeps each week balanced.

## 8. KPIs to watch weekly

| KPI | Where | Healthy direction |
|---|---|---|
| Reply rate by track | `report` → Outreach | REACTIVATE > WARM > ICP; set your own baseline in weeks 1–2 |
| Positive-reply rate | `report` | Primary success metric for templates |
| Meetings per 100 sequences | scoreboard KPIs | The business outcome |
| Referrals received | `sync` output | NETWORK and STUDENT value |
| Not-connected / skipped share | `sync` output | Should stay low; if it rises, re-export Connections |
| Variant winners | `report` → A/B | Promote winners and add a new challenger |

## 9. Refresh cycle

Re-export from LinkedIn monthly (**Settings → Data privacy → Get a copy of your data**), drop the zip into `data/`, and run `python -m engine import`. Re-imports update signals and new connections but **never reset** stages, touches or replies.
